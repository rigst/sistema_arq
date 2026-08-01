import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from arquivos.models import Arquivo
from core.tenancy import obter_grupo_empresa_padrao
from crm.models import Cliente
from fases import catalogo
from fases.models import Fase, montar_fases
from legal.testing import aceitar_documentos
from projetos.models import Projeto
from usuarios.models import Usuario


def _png(nome="planta.png"):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 200, 200)).save(buf, format="PNG")
    return SimpleUploadedFile(nome, buf.getvalue(), content_type="image/png")


class BaseFase(TestCase):
    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(username="arq-fase", password="senha-de-teste")
        self.user.groups.add(self.grupo)
        aceitar_documentos(self.user)
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Marina")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, cliente=self.cliente, nome="Casa Ipê", tipo="residencial"
        )
        montar_fases(self.projeto)

    def fase(self, chave):
        return self.projeto.fases.get(chave=chave)


class MontagemTests(BaseFase):
    def test_projeto_novo_nasce_com_as_cinco_principais(self):
        self.assertEqual(
            list(self.projeto.fases.values_list("chave", flat=True)),
            ["briefing", "proposta", "estudo_preliminar", "anteprojeto", "executivo"],
        )

    def test_complementares_nao_entram_sozinhos(self):
        """São opcionais: nem todo trabalho tem algum, quase nenhum tem todos."""
        self.assertFalse(self.projeto.fases.filter(chave__startswith="comp_").exists())

    def test_montar_de_novo_nao_duplica(self):
        montar_fases(self.projeto, complementares=["comp_eletrica"])
        montar_fases(self.projeto, complementares=["comp_eletrica"])
        self.assertEqual(self.projeto.fases.filter(chave="comp_eletrica").count(), 1)


class FluxoTests(BaseFase):
    def test_so_a_primeira_fase_comeca_liberada(self):
        self.assertTrue(self.fase("briefing").liberada)
        self.assertFalse(self.fase("estudo_preliminar").liberada)
        self.assertIn("Proposta e contrato", self.fase("estudo_preliminar").impedimento)

    def test_aprovar_uma_fase_libera_a_seguinte(self):
        proposta = self.fase("proposta")
        proposta.iniciar(self.user)
        Arquivo.objects.create(
            empresa=self.grupo, projeto=self.projeto, fase=proposta,
            titulo="Proposta", arquivo=_png("p.png"),
        )
        proposta.enviar_ao_cliente(self.user)
        proposta.registrar_resposta(True, "Pode seguir", self.user)
        self.assertTrue(self.fase("estudo_preliminar").liberada)

    def test_ajustes_nao_liberam_a_seguinte(self):
        proposta = self.fase("proposta")
        proposta.iniciar(self.user)
        proposta.enviar_ao_cliente(self.user)
        proposta.registrar_resposta(False, "Rever o prazo", self.user)
        self.assertEqual(proposta.status, Fase.AJUSTES)
        self.assertFalse(self.fase("estudo_preliminar").liberada)

    def test_briefing_fecha_sem_aprovacao_do_cliente(self):
        """Briefing é insumo interno; não se manda o cliente aprovar o próprio
        depoimento."""
        briefing = self.fase("briefing")
        self.assertFalse(briefing.exige_aprovacao)
        briefing.iniciar(self.user)
        self.assertTrue(briefing.concluir_sem_aprovacao(self.user))
        self.assertEqual(briefing.status, Fase.APROVADA)

    def test_fase_que_exige_aprovacao_nao_fecha_por_atalho(self):
        anteprojeto = self.fase("anteprojeto")
        anteprojeto.iniciar(self.user)
        self.assertFalse(anteprojeto.concluir_sem_aprovacao(self.user))
        self.assertEqual(anteprojeto.status, Fase.EM_ELABORACAO)

    def test_todos_os_complementares_dependem_do_anteprojeto(self):
        for passo in catalogo.COMPLEMENTARES:
            self.assertEqual(catalogo.anterior_de(passo.chave), "anteprojeto")

    def test_transicao_fora_de_ordem_nao_acontece(self):
        fase = self.fase("anteprojeto")
        self.assertFalse(fase.enviar_ao_cliente(self.user))  # nem começou
        self.assertFalse(fase.registrar_resposta(True, "", self.user))
        self.assertEqual(fase.status, Fase.NAO_INICIADA)


class ViewsTests(BaseFase):
    def test_nao_envia_fase_vazia_ao_cliente(self):
        """Enviar sem material é pedir aprovação de nada."""
        fase = self.fase("proposta")
        fase.iniciar(self.user)
        self.client.post(f"/fases/{fase.pk}/enviar/")
        fase.refresh_from_db()
        self.assertEqual(fase.status, Fase.EM_ELABORACAO)

    def test_anexar_arquivo_registra_no_historico(self):
        fase = self.fase("estudo_preliminar")
        self.client.post(
            f"/fases/{fase.pk}/anexar/",
            {"titulo": "Planta baixa", "arquivo": _png(), "categoria": "projeto", "fluxo": "interno"},
        )
        self.assertEqual(fase.arquivos.count(), 1)
        self.assertTrue(fase.registros.filter(tipo="sistema", texto__contains="Planta baixa").exists())
        fase.arquivos.first().arquivo.delete(save=False)

    def test_arquivo_e_servido_pelo_sistema_e_nao_pela_pasta(self):
        fase = self.fase("estudo_preliminar")
        arquivo = Arquivo.objects.create(
            empresa=self.grupo, projeto=self.projeto, fase=fase,
            titulo="Fachada", arquivo=_png("f.png"),
        )
        resp = self.client.get(f"/fases/arquivo/{arquivo.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/png")
        # Imagem abre na aba; não força download.
        self.assertNotIn("attachment", resp.get("Content-Disposition", ""))
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        arquivo.arquivo.delete(save=False)

    def test_arquivo_de_outra_empresa_da_404(self):
        from django.contrib.auth.models import Group

        outro = Group.objects.create(name="Escritório vizinho")
        projeto_alheio = Projeto.objects.create(
            empresa=outro, cliente=self.cliente, nome="Alheio", tipo="comercial"
        )
        arquivo = Arquivo.objects.create(
            empresa=outro, projeto=projeto_alheio, titulo="Sigiloso", arquivo=_png("s.png")
        )
        self.assertEqual(self.client.get(f"/fases/arquivo/{arquivo.pk}/").status_code, 404)
        arquivo.arquivo.delete(save=False)

    def test_renomear_arquivo_deixa_rastro(self):
        fase = self.fase("anteprojeto")
        arquivo = Arquivo.objects.create(
            empresa=self.grupo, projeto=self.projeto, fase=fase,
            titulo="Sem nome", arquivo=_png("x.png"),
        )
        self.client.post(
            f"/fases/arquivo/{arquivo.pk}/editar/",
            {"titulo": "Planta pavimento térreo", "categoria": "projeto", "observacoes": ""},
        )
        arquivo.refresh_from_db()
        self.assertEqual(arquivo.titulo, "Planta pavimento térreo")
        self.assertTrue(fase.registros.filter(texto__contains="renomeado").exists())
        arquivo.arquivo.delete(save=False)

    def test_ligar_e_desligar_complementar(self):
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementar/", {"chave": "comp_hidraulica"}
        )
        fase = self.projeto.fases.get(chave="comp_hidraulica")
        self.assertTrue(fase.complementar)

        self.client.post(f"/fases/{fase.pk}/remover/")
        self.assertFalse(self.projeto.fases.filter(chave="comp_hidraulica").exists())

    def test_fase_principal_nao_pode_ser_removida(self):
        fase = self.fase("executivo")
        self.client.post(f"/fases/{fase.pk}/remover/")
        self.assertTrue(self.projeto.fases.filter(chave="executivo").exists())

    def test_registrar_conversa_com_o_cliente(self):
        fase = self.fase("briefing")
        self.client.post(
            f"/fases/{fase.pk}/registro/",
            {"tipo": "cliente", "texto": "Pediu para rever a cozinha."},
        )
        registro = fase.registros.get(tipo="cliente")
        self.assertEqual(registro.autor, self.user)

    def test_resposta_do_cliente_pela_tela(self):
        fase = self.fase("proposta")
        fase.iniciar(self.user)
        Arquivo.objects.create(
            empresa=self.grupo, projeto=self.projeto, fase=fase,
            titulo="Proposta", arquivo=_png("pr.png"),
        )
        self.client.post(f"/fases/{fase.pk}/enviar/")
        self.client.post(
            f"/fases/{fase.pk}/responder/", {"decisao": "aprovar", "parecer": "Fechado."}
        )
        fase.refresh_from_db()
        self.assertEqual(fase.status, Fase.APROVADA)
        self.assertEqual(fase.parecer, "Fechado.")
        self.assertTrue(fase.registros.filter(tipo="cliente", texto__contains="aprovou").exists())
        fase.arquivos.first().arquivo.delete(save=False)

    def test_fase_de_outra_empresa_da_404(self):
        from django.contrib.auth.models import Group

        outro = Group.objects.create(name="Vizinho 2")
        alheio = Projeto.objects.create(
            empresa=outro, cliente=self.cliente, nome="Alheio 2", tipo="comercial"
        )
        montar_fases(alheio)
        fase = alheio.fases.first()
        self.assertEqual(self.client.get(f"/fases/{fase.pk}/").status_code, 404)
