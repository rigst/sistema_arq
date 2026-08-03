from decimal import Decimal
import os
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from contratos.models import AlteracaoEscopo, Contrato, Documento, ModeloContrato, Parcela
from core.tenancy import obter_grupo_empresa_padrao
from crm.models import Cliente
from legal.testing import aceitar_documentos
from projetos.models import Projeto
from usuarios.models import Usuario


class FluxoContratoTests(TestCase):
    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(username="contrato", password="senha-de-teste")
        self.user.groups.add(self.grupo)
        aceitar_documentos(self.user)
        self.client.force_login(self.user)
        cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente")
        projeto = Projeto.objects.create(empresa=self.grupo, cliente=cliente, nome="Casa")
        self.contrato = Contrato.objects.create(
            empresa=self.grupo,
            projeto=projeto,
            titulo="Contrato Casa",
            valor_total=Decimal("12000.00"),
            corpo="Texto revisado do contrato.",
        )

    def test_envio_trava_edicao_e_retorno_libera(self):
        self.client.post(f"/contratos/{self.contrato.pk}/enviar/")
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.status, "enviado")
        self.assertFalse(self.contrato.editavel)

        resposta = self.client.get(f"/contratos/{self.contrato.pk}/")
        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, 'name="corpo"')
        self.assertEqual(
            self.client.get(f"/contratos/{self.contrato.pk}/editar/").status_code,
            404,
        )

        self.client.post(f"/contratos/{self.contrato.pk}/retornar/")
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.status, "ajustes")
        self.assertTrue(self.contrato.editavel)

    def test_modelo_novo_e_sempre_criado_ativo(self):
        resposta = self.client.post(
            "/contratos/modelos/novo/",
            {
                "nome": "Minuta própria",
                "descricao": "Modelo de teste",
                "corpo": "Contrato para {{cliente}}.",
                "padrao": "",
                "ativo": "",
            },
        )

        modelo = ModeloContrato.objects.get(nome="Minuta própria")
        self.assertTrue(modelo.ativo)
        self.assertRedirects(resposta, "/modelos/")

    def test_aprovacao_libera_parcelas(self):
        self.client.post(f"/contratos/{self.contrato.pk}/enviar/")
        self.client.post(f"/contratos/{self.contrato.pk}/aprovar/")
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.status, "aprovado")

        self.client.post(
            f"/contratos/{self.contrato.pk}/parcelas/",
            {"quantidade": 2, "primeira_data": "2026-08-10", "intervalo_dias": 30},
        )
        self.assertEqual(self.contrato.parcelas.count(), 2)

    def test_nao_envia_sem_texto(self):
        self.contrato.corpo = ""
        self.contrato.save(update_fields=["corpo"])
        self.client.post(f"/contratos/{self.contrato.pk}/enviar/")
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.status, "rascunho")

    def test_aplica_modelo_e_preenche_dados_no_editor_unificado(self):
        modelo = ModeloContrato.objects.create(
            empresa=self.grupo,
            nome="Minuta curta",
            corpo="Cliente: {{cliente}}. Projeto: {{projeto}}. Valor: {{valor}}.",
        )
        resposta = self.client.post(
            f"/contratos/{self.contrato.pk}/",
            {
                "projeto": self.contrato.projeto_id,
                "titulo": self.contrato.titulo,
                "numero": "C-001",
                "valor_total": "12000.00",
                "data_assinatura": "",
                "corpo": self.contrato.corpo,
                "observacoes": "",
                "modelo": modelo.pk,
                "acao": "aplicar_modelo",
            },
        )
        self.assertRedirects(resposta, f"/contratos/{self.contrato.pk}/#minuta")
        self.contrato.refresh_from_db()
        self.assertEqual(
            self.contrato.corpo,
            "Cliente: Cliente. Projeto: Casa. Valor: R$ 12.000,00.",
        )

        pagina = self.client.get(f"/contratos/{self.contrato.pk}/")
        self.assertContains(pagina, "Modelo da minuta")
        self.assertContains(pagina, "Minuta curta")

    def test_alteracoes_calculam_valor_atualizado_e_entram_nas_parcelas(self):
        self.contrato.status = "aprovado"
        self.contrato.save(update_fields=["status"])
        self.client.post(
            f"/contratos/{self.contrato.pk}/alteracao/",
            {
                "tipo": "aditivo",
                "descricao": "Novo ambiente incluído no escopo.",
                "valor_delta": "2500.00",
            },
        )
        self.client.post(
            f"/contratos/{self.contrato.pk}/alteracao/",
            {
                "tipo": "prazo",
                "descricao": "Entrega prorrogada por solicitação do cliente.",
                "valor_delta": "0",
            },
        )
        self.assertEqual(self.contrato.alteracoes.count(), 2)

        pagina = self.client.get(f"/contratos/{self.contrato.pk}/")
        self.assertEqual(pagina.context["impacto_alteracoes"], Decimal("2500.00"))
        self.assertEqual(pagina.context["valor_atualizado"], Decimal("14500.00"))
        self.assertContains(pagina, "Aditivo contratual")
        self.assertContains(pagina, "Sem impacto financeiro")

        self.client.post(
            f"/contratos/{self.contrato.pk}/parcelas/",
            {"quantidade": 2, "primeira_data": "2026-09-10", "intervalo_dias": 30},
        )
        self.assertEqual(
            sum((p.valor for p in self.contrato.parcelas.all()), Decimal("0")),
            Decimal("14500.00"),
        )

    def test_rascunho_aceita_planejar_alteracao_contratual(self):
        self.client.post(
            f"/contratos/{self.contrato.pk}/alteracao/",
            {"tipo": "alteracao", "descricao": "Tentativa", "valor_delta": "100"},
        )
        self.assertTrue(AlteracaoEscopo.objects.exists())

    def test_parcelamento_mantem_o_dia_do_mes(self):
        self.client.post(
            f"/contratos/{self.contrato.pk}/parcelas/",
            {"quantidade": 4, "primeira_data": "2026-01-31"},
        )
        self.assertEqual(
            [str(data) for data in self.contrato.parcelas.values_list("vencimento", flat=True)],
            ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"],
        )

    def test_documento_pode_ser_excluido_com_remocao_do_arquivo(self):
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.client.post(
                f"/contratos/{self.contrato.pk}/documento/",
                {
                    "titulo": "Aditivo assinado",
                    "arquivo": SimpleUploadedFile("aditivo.pdf", b"arquivo", "application/pdf"),
                },
            )
            documento = Documento.objects.get()
            caminho = documento.arquivo.path
            self.assertTrue(os.path.exists(caminho))

            resposta = self.client.post(f"/contratos/documento/{documento.pk}/remover/")
            self.assertRedirects(resposta, f"/contratos/{self.contrato.pk}/")
            self.assertFalse(Documento.objects.exists())
            self.assertFalse(os.path.exists(caminho))

    def test_crud_inline_de_parcelas(self):
        self.contrato.status = "aprovado"
        self.contrato.save(update_fields=["status"])
        resposta = self.client.post(
            f"/contratos/{self.contrato.pk}/parcela/",
            {"descricao": "Entrada", "valor": "3000.00", "vencimento": "2026-08-15"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'id="parcelas-bloco"')
        parcela = Parcela.objects.get()

        resposta = self.client.post(
            f"/contratos/parcela/{parcela.pk}/editar/",
            {"descricao": "Entrada revisada", "valor": "3500.00", "vencimento": "2026-08-20"},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(resposta, "Entrada revisada")
        parcela.refresh_from_db()
        self.assertEqual(parcela.valor, Decimal("3500.00"))

        resposta = self.client.post(
            f"/contratos/parcela/{parcela.pk}/remover/", HTTP_HX_REQUEST="true"
        )
        self.assertContains(resposta, 'id="parcelas-bloco"')
        self.assertFalse(Parcela.objects.exists())

    def test_crud_inline_de_alteracoes(self):
        self.contrato.status = "aprovado"
        self.contrato.save(update_fields=["status"])
        resposta = self.client.post(
            f"/contratos/{self.contrato.pk}/alteracao/",
            {"tipo": "aditivo", "descricao": "Novo ambiente", "valor_delta": "1800.00"},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(resposta, 'id="alteracoes-bloco"')
        alteracao = AlteracaoEscopo.objects.get()

        resposta = self.client.post(
            f"/contratos/alteracao/{alteracao.pk}/editar/",
            {"tipo": "prazo", "descricao": "Somente novo prazo", "valor_delta": "0"},
            HTTP_HX_REQUEST="true",
        )
        self.assertContains(resposta, "Somente novo prazo")
        self.assertContains(resposta, "Sem impacto financeiro")

        resposta = self.client.post(
            f"/contratos/alteracao/{alteracao.pk}/remover/", HTTP_HX_REQUEST="true"
        )
        self.assertContains(resposta, 'id="alteracoes-bloco"')
        self.assertFalse(AlteracaoEscopo.objects.exists())

    def test_crud_inline_de_documentos(self):
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            resposta = self.client.post(
                f"/contratos/{self.contrato.pk}/documento/",
                {"titulo": "Minuta", "arquivo": SimpleUploadedFile("minuta.pdf", b"a")},
                HTTP_HX_REQUEST="true",
            )
            self.assertContains(resposta, 'id="documentos-bloco"')
            documento = Documento.objects.get()

            resposta = self.client.post(
                f"/contratos/documento/{documento.pk}/editar/",
                {"titulo": "Minuta assinada"},
                HTTP_HX_REQUEST="true",
            )
            self.assertContains(resposta, "Minuta assinada")
            documento.refresh_from_db()
            self.assertEqual(documento.titulo, "Minuta assinada")

            resposta = self.client.post(
                f"/contratos/documento/{documento.pk}/remover/", HTTP_HX_REQUEST="true"
            )
            self.assertContains(resposta, 'id="documentos-bloco"')
            self.assertFalse(Documento.objects.exists())
