from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import TestCase

from crm.models import Cliente
from precificacao.models import ConfiguracaoPrecificacao, FatorPrecificacao
from precificacao.services import precificar_etapa
from propostas.models import Proposta

class ItensProntosTests(TestCase):
    """A proposta trava na folha em branco, não no cálculo."""

    def setUp(self):
        from core.tenancy import obter_grupo_empresa_padrao
        from legal.testing import aceitar_documentos
        from usuarios.models import Usuario

        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(username="prop", password="senha-de-teste")
        self.user.groups.add(self.grupo)
        aceitar_documentos(self.user)
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente")
        self.proposta = Proposta.objects.create(
            empresa=self.grupo, cliente=self.cliente, titulo="Proposta",
            hora_tecnica_aplicada=Decimal("150"),
        )

    def test_adiciona_varios_de_uma_vez_ja_precificados(self):
        self.client.post(
            f"/propostas/{self.proposta.pk}/prontos/",
            {"prontos": ["Estudo preliminar", "Anteprojeto"]},
        )
        itens = list(self.proposta.itens.all())
        self.assertEqual(len(itens), 2)
        self.assertTrue(all(i.valor > 0 for i in itens))
        self.assertTrue(all(i.horas_estimadas > 0 for i in itens))
        self.assertTrue(all(i.inclusoes for i in itens))

    def test_nao_duplica_o_que_ja_esta_na_proposta(self):
        for _ in range(2):
            self.client.post(
                f"/propostas/{self.proposta.pk}/prontos/", {"prontos": ["Anteprojeto"]}
            )
        self.assertEqual(self.proposta.itens.filter(descricao="Anteprojeto").count(), 1)

    def test_sem_marcar_nada_nao_cria_item(self):
        self.client.post(f"/propostas/{self.proposta.pk}/prontos/", {})
        self.assertFalse(self.proposta.itens.exists())

    def test_proposta_de_outra_empresa_da_404(self):
        from django.contrib.auth.models import Group

        outro = Group.objects.create(name="Vizinho prop")
        alheia = Proposta.objects.create(
            empresa=outro, cliente=self.cliente, titulo="Alheia"
        )
        self.assertEqual(
            self.client.post(
                f"/propostas/{alheia.pk}/prontos/", {"prontos": ["Anteprojeto"]}
            ).status_code,
            404,
        )


class CicloDaPropostaTests(ItensProntosTests):
    """Rascunho → enviada → aprovada, e a volta quando o cliente diz não.

    A trava importa mais do que parece: mexer no valor que o cliente já viu,
    sem que ninguém tenha decidido reabrir, é o erro que só aparece na hora de
    assinar o contrato.
    """

    def _com_itens(self):
        self.client.post(
            f"/propostas/{self.proposta.pk}/prontos/", {"prontos": ["Anteprojeto"]}
        )
        return self.proposta.itens.get()

    def test_rascunho_e_editavel_e_enviada_nao_e(self):
        self.assertTrue(self.proposta.editavel)
        self._com_itens()
        self.client.post(f"/propostas/{self.proposta.pk}/finalizar/")
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.status, "enviada")
        self.assertFalse(self.proposta.editavel)

    def test_proposta_sem_item_nao_vai_ao_cliente(self):
        self.client.post(f"/propostas/{self.proposta.pk}/finalizar/")
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.status, "rascunho")

    def test_rodape_salva_os_termos_antes_de_enviar(self):
        self._com_itens()
        resposta = self.client.post(
            f"/propostas/{self.proposta.pk}/",
            {
                "titulo": "Proposta pronta para envio",
                "cliente": self.cliente.pk,
                "tipo_projeto": "residencial",
                "validade_dias_uteis": "10",
                "observacoes": "Termos finais.",
                "acao": "enviar",
            },
        )
        self.assertRedirects(resposta, f"/propostas/{self.proposta.pk}/")
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.titulo, "Proposta pronta para envio")
        self.assertEqual(self.proposta.observacoes, "Termos finais.")
        self.assertEqual(self.proposta.validade_dias_uteis, 10)
        self.assertEqual(self.proposta.status, "enviada")

    def test_validade_aceita_apenas_quantidade_positiva_de_dias_uteis(self):
        resposta = self.client.post(
            f"/propostas/{self.proposta.pk}/",
            {
                "titulo": self.proposta.titulo,
                "cliente": self.cliente.pk,
                "tipo_projeto": "residencial",
                "validade_dias_uteis": "0",
                "observacoes": "",
                "acao": "salvar",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "A proposta não foi salva")
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.validade_dias_uteis, 10)

        self.proposta.validade_dias_uteis = 1
        self.assertEqual(self.proposta.validade_texto, "1 dia útil")

    def test_acoes_do_rodape_ficam_na_ordem_correta(self):
        self._com_itens()
        pagina = self.client.get(f"/propostas/{self.proposta.pk}/")
        html = pagina.content.decode()
        self.assertContains(pagina, "fecho-acoes--proposta")
        self.assertLess(html.index('value="salvar"'), html.index('value="enviar"'))
        self.assertContains(pagina, "Salvar e enviar ao cliente")

        self.proposta.status = "enviada"
        self.proposta.save(update_fields=["status"])
        pagina = self.client.get(f"/propostas/{self.proposta.pk}/")
        html = pagina.content.decode()
        self.assertLess(html.index("Cliente não aprovou"), html.index("Cliente aprovou"))

    def test_pdf_recebe_validade_e_nome_completo_para_assinatura(self):
        self.user.first_name = "Ana"
        self.user.last_name = "Arquiteta"
        self.user.save(update_fields=["first_name", "last_name"])
        self.proposta.validade_dias_uteis = 10
        self.proposta.save(update_fields=["validade_dias_uteis"])

        with patch("core.pdf.render_pdf", return_value=HttpResponse(content_type="application/pdf")) as gerar:
            resposta = self.client.get(f"/propostas/{self.proposta.pk}/pdf/")

        self.assertEqual(resposta.status_code, 200)
        contexto = gerar.call_args.args[1]
        self.assertEqual(contexto["proposta"].validade_dias_uteis, 10)
        self.assertEqual(contexto["assinante_nome"], "Ana Arquiteta")
        html = render_to_string("pdf/proposta.html", contexto)
        self.assertIn("10 dias úteis", html)

    def test_enviada_recusa_mexer_nos_itens(self):
        item = self._com_itens()
        self.client.post(f"/propostas/{self.proposta.pk}/finalizar/")
        self.client.post(f"/propostas/item/{item.pk}/remover/")
        self.assertTrue(self.proposta.itens.filter(pk=item.pk).exists())

    def test_reabrir_devolve_a_edicao(self):
        self._com_itens()
        self.client.post(f"/propostas/{self.proposta.pk}/finalizar/")
        self.client.post(f"/propostas/{self.proposta.pk}/reabrir/")
        self.proposta.refresh_from_db()
        self.assertTrue(self.proposta.editavel)

    def test_aprovada_nao_volta_para_edicao(self):
        self._com_itens()
        self.client.post(f"/propostas/{self.proposta.pk}/finalizar/")
        self.client.post(f"/propostas/{self.proposta.pk}/aprovar/")
        self.client.post(f"/propostas/{self.proposta.pk}/reabrir/")
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.status, "aprovada")

    def test_rascunho_nao_pode_ser_aprovado_diretamente(self):
        self._com_itens()
        self.client.post(f"/propostas/{self.proposta.pk}/aprovar/")
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.status, "rascunho")

    def test_enviada_nao_recebe_novos_itens(self):
        self._com_itens()
        self.client.post(f"/propostas/{self.proposta.pk}/finalizar/")
        self.client.post(f"/propostas/{self.proposta.pk}/prontos/", {"prontos": ["Estudo preliminar"]})
        self.assertEqual(self.proposta.itens.count(), 1)

    def test_proposta_nascida_num_projeto_nao_cria_outro(self):
        """Ela já tem o seu: aprovar de novo duplicaria o mesmo trabalho."""
        from datetime import date

        from fases.models import montar_fases
        from projetos.models import Projeto

        projeto = Projeto.objects.create(
            empresa=self.grupo, cliente=self.cliente, nome="Casa", tipo="residencial"
        )
        montar_fases(projeto, complementares=["comp_eletrica"])
        estudo = projeto.fases.get(chave="estudo_preliminar")
        estudo.prazo = date(2026, 10, 15)
        estudo.save(update_fields=["prazo"])
        self.proposta.projeto_gerado = projeto
        self.proposta.save(update_fields=["projeto_gerado"])
        self._com_itens()
        self.client.post(f"/propostas/{self.proposta.pk}/finalizar/")
        resposta = self.client.post(f"/propostas/{self.proposta.pk}/aprovar/")
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.status, "aprovada")
        self.assertEqual(Projeto.objects.count(), 1)
        contrato = projeto.contratos.get()
        self.assertRedirects(resposta, f"/contratos/{contrato.pk}/")
        self.assertEqual(contrato.valor_total, self.proposta.valor_total)
        self.assertIn("Cliente", contrato.corpo)
        self.assertIn("15/10/2026", contrato.corpo)
        projeto.refresh_from_db()
        self.assertEqual(projeto.horas_estimadas, self.proposta.horas_totais)
        self.assertEqual(str(projeto.data_prevista), "2026-10-15")

        self.client.post(f"/propostas/{self.proposta.pk}/aprovar/")
        self.assertEqual(projeto.contratos.count(), 1)

    def test_edita_os_termos_sem_desvincular_o_projeto(self):
        from projetos.models import Projeto

        projeto = Projeto.objects.create(
            empresa=self.grupo, cliente=self.cliente, nome="Casa", tipo="residencial"
        )
        self.proposta.projeto_gerado = projeto
        self.proposta.save(update_fields=["projeto_gerado"])

        resposta = self.client.post(
            f"/propostas/{self.proposta.pk}/",
            {
                "titulo": "Proposta revisada",
                "cliente": self.cliente.pk,
                "tipo_projeto": "comercial",
                "validade_dias_uteis": "15",
                "observacoes": "Condições e escopo revisados.",
            },
        )

        self.assertRedirects(resposta, f"/propostas/{self.proposta.pk}/")
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.titulo, "Proposta revisada")
        self.assertEqual(self.proposta.observacoes, "Condições e escopo revisados.")
        self.assertEqual(self.proposta.validade_dias_uteis, 15)
        self.assertEqual(self.proposta.projeto_gerado, projeto)
        self.assertEqual(self.proposta.cliente, self.cliente)
        self.assertEqual(self.proposta.tipo_projeto, "residencial")

    def test_salva_dias_uteis_das_fases_e_dos_complementares_na_proposta(self):
        from fases.models import montar_fases
        from projetos.models import Projeto

        projeto = Projeto.objects.create(
            empresa=self.grupo, cliente=self.cliente, nome="Casa", tipo="residencial"
        )
        montar_fases(projeto, complementares=["comp_eletrica"])
        self.proposta.projeto_gerado = projeto
        self.proposta.save(update_fields=["projeto_gerado"])
        estudo = projeto.fases.get(chave="estudo_preliminar")
        eletrico = projeto.fases.get(chave="comp_eletrica")

        pagina = self.client.get(f"/propostas/{self.proposta.pk}/")
        self.assertContains(pagina, "Prazos por etapa")
        self.assertContains(pagina, "contagem começa na assinatura do contrato")
        self.assertContains(pagina, "Estudo preliminar")
        self.assertContains(pagina, "Projeto elétrico")

        resposta = self.client.post(
            f"/propostas/{self.proposta.pk}/",
            {
                "titulo": self.proposta.titulo,
                "cliente": self.cliente.pk,
                "tipo_projeto": "residencial",
                "validade_dias_uteis": "10",
                "observacoes": "",
                f"dias_fase_{estudo.pk}": "18",
                f"dias_fase_{eletrico.pk}": "12",
                "acao": "salvar",
            },
        )
        self.assertRedirects(resposta, f"/propostas/{self.proposta.pk}/")
        estudo.refresh_from_db()
        eletrico.refresh_from_db()
        self.assertEqual(estudo.dias_uteis_proposta, 18)
        self.assertEqual(eletrico.dias_uteis_proposta, 12)

        pdf = self.client.get(f"/propostas/{self.proposta.pk}/pdf/")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")


class EdicaoInlineDeItemTests(ItensProntosTests):
    def test_adicionar_item_manual_atualiza_so_o_bloco(self):
        resposta = self.client.post(
            f"/propostas/{self.proposta.pk}/item/",
            {"descricao": "Cozinha", "horas_estimadas": "12"},
            headers={"HX-Request": "true"},
        )
        self.assertContains(resposta, 'id="itens-bloco"')
        self.assertContains(resposta, "Cozinha")
        self.assertContains(resposta, "hora técnica")
        self.assertContains(resposta, "12 h")
        self.assertNotContains(resposta, "Termos da proposta")

    def test_adicionar_itens_prontos_atualiza_so_o_bloco(self):
        resposta = self.client.post(
            f"/propostas/{self.proposta.pk}/prontos/",
            {"prontos": ["Anteprojeto"]},
            headers={"HX-Request": "true"},
        )
        self.assertContains(resposta, 'id="itens-bloco"')
        self.assertContains(resposta, "Anteprojeto")
        self.assertNotContains(resposta, "Termos da proposta")

    def test_mudar_as_horas_reprecifica_a_linha(self):
        self.client.post(
            f"/propostas/{self.proposta.pk}/prontos/", {"prontos": ["Anteprojeto"]}
        )
        item = self.proposta.itens.get()
        antes = item.valor
        self.client.post(
            f"/propostas/item/{item.pk}/editar/",
            {"descricao": item.descricao, "horas_estimadas": "10"},
            headers={"HX-Request": "true"},
        )
        item.refresh_from_db()
        self.assertEqual(item.horas_estimadas, Decimal("10.00"))
        self.assertLess(item.valor, antes)

    def test_htmx_recebe_o_bloco_todo_para_o_total_acompanhar(self):
        self.client.post(
            f"/propostas/{self.proposta.pk}/prontos/", {"prontos": ["Anteprojeto"]}
        )
        item = self.proposta.itens.get()
        resposta = self.client.post(
            f"/propostas/item/{item.pk}/editar/",
            {"descricao": "Anteprojeto revisado", "horas_estimadas": "8"},
            headers={"HX-Request": "true"},
        )
        self.assertContains(resposta, 'id="itens-bloco"')
        self.assertContains(resposta, 'class="proposta-somatorio"')
        self.assertContains(resposta, "8 h")

    def test_move_servicos_para_cima_e_para_baixo(self):
        self.client.post(
            f"/propostas/{self.proposta.pk}/prontos/",
            {"prontos": ["Estudo preliminar", "Anteprojeto", "Projeto executivo"]},
        )
        itens = list(self.proposta.itens.order_by("ordem", "pk"))
        ultimo = itens[-1]

        resposta = self.client.post(
            f"/propostas/item/{ultimo.pk}/mover/",
            {"direcao": "cima"},
            headers={"HX-Request": "true"},
        )
        ordem = list(self.proposta.itens.order_by("ordem", "pk").values_list("pk", flat=True))
        self.assertEqual(ordem.index(ultimo.pk), 1)
        self.assertContains(resposta, "Mover para cima")
        self.assertContains(resposta, "Mover para baixo")

        self.client.post(
            f"/propostas/item/{ultimo.pk}/mover/", {"direcao": "baixo"}
        )
        ordem = list(self.proposta.itens.order_by("ordem", "pk").values_list("pk", flat=True))
        self.assertEqual(ordem.index(ultimo.pk), 2)


class FatoresDaPropostaTests(ItensProntosTests):
    def setUp(self):
        super().setUp()
        ConfiguracaoPrecificacao.objects.update_or_create(
            empresa=self.grupo,
            defaults={"hora_tecnica_manual": Decimal("100.00")},
        )
        self.urgencia = FatorPrecificacao.objects.create(
            empresa=self.grupo, nome="Urgência", percentual=Decimal("20.00")
        )
        self.complexidade = FatorPrecificacao.objects.create(
            empresa=self.grupo, nome="Complexidade", percentual=Decimal("10.00")
        )

    def test_aplica_fatores_e_reprecifica_itens(self):
        self.client.post(
            f"/propostas/{self.proposta.pk}/item/",
            {"descricao": "Estudo", "horas_estimadas": "10"},
        )
        resposta = self.client.post(
            f"/propostas/{self.proposta.pk}/hora-tecnica/",
            {"fatores": [self.urgencia.pk, self.complexidade.pk], "valor_manual": ""},
        )
        self.assertRedirects(resposta, f"/propostas/{self.proposta.pk}/")
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.hora_tecnica_aplicada, Decimal("130.00"))
        self.assertEqual(
            set(self.proposta.fatores.values_list("pk", flat=True)),
            {self.urgencia.pk, self.complexidade.pk},
        )
        esperado = precificar_etapa(
            self.grupo, Decimal("10"), hora_tecnica=Decimal("130.00")
        )["total"]
        self.assertEqual(self.proposta.itens.get().valor, esperado)

    def test_ignora_fator_inativo_e_de_outra_empresa(self):
        from django.contrib.auth.models import Group

        inativo = FatorPrecificacao.objects.create(
            empresa=self.grupo, nome="Antigo", percentual=Decimal("90"), ativo=False
        )
        outro = Group.objects.create(name="Outra empresa dos fatores")
        alheio = FatorPrecificacao.objects.create(
            empresa=outro, nome="Alheio", percentual=Decimal("80")
        )
        self.client.post(
            f"/propostas/{self.proposta.pk}/hora-tecnica/",
            {"fatores": [self.urgencia.pk, inativo.pk, alheio.pk]},
        )
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.hora_tecnica_aplicada, Decimal("120.00"))
        self.assertEqual(list(self.proposta.fatores.all()), [self.urgencia])

    def test_valor_manual_invalido_nao_altera_fatores(self):
        self.proposta.fatores.add(self.urgencia)
        resposta = self.client.post(
            f"/propostas/{self.proposta.pk}/hora-tecnica/",
            {"fatores": [self.complexidade.pk], "valor_manual": "inválido"},
        )
        self.assertRedirects(resposta, f"/propostas/{self.proposta.pk}/")
        self.assertEqual(list(self.proposta.fatores.all()), [self.urgencia])

    def test_valor_manual_aceita_moeda_brasileira(self):
        resposta = self.client.post(
            f"/propostas/{self.proposta.pk}/hora-tecnica/",
            {"valor_manual": "1.234,56"},
        )
        self.assertRedirects(resposta, f"/propostas/{self.proposta.pk}/")
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.hora_tecnica_aplicada, Decimal("1234.56"))
