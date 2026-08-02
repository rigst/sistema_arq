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

    def liberar_ate(self, chave):
        """Aprova tudo que vem antes — a ordem agora é obrigatória de verdade."""
        alvo = self.fase(chave)
        self.projeto.fases.filter(ordem__lt=alvo.ordem).update(status=Fase.APROVADA)
        alvo.refresh_from_db()
        alvo.status = Fase.NAO_INICIADA
        alvo.save(update_fields=["status"])
        return alvo


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
        proposta = self.liberar_ate("proposta")
        proposta.abrir(self.user)
        Arquivo.objects.create(
            empresa=self.grupo, projeto=self.projeto, fase=proposta,
            titulo="Proposta", arquivo=_png("p.png"),
        )
        proposta.enviar_ao_cliente(self.user)
        proposta.registrar_resposta(True, "Pode seguir", self.user)
        self.assertTrue(self.fase("estudo_preliminar").liberada)

    def test_ajustes_nao_liberam_a_seguinte(self):
        proposta = self.liberar_ate("proposta")
        proposta.abrir(self.user)
        proposta.enviar_ao_cliente(self.user)
        proposta.registrar_resposta(False, "Rever o prazo", self.user)
        self.assertEqual(proposta.status, Fase.AJUSTES)
        self.assertFalse(self.fase("estudo_preliminar").liberada)

    def test_briefing_fecha_sem_aprovacao_do_cliente(self):
        """Briefing é insumo interno; não se manda o cliente aprovar o próprio
        depoimento."""
        briefing = self.fase("briefing")
        self.assertFalse(briefing.exige_aprovacao)
        briefing.abrir(self.user)
        self.assertTrue(briefing.concluir_sem_aprovacao(self.user))
        self.assertEqual(briefing.status, Fase.APROVADA)

    def test_fase_que_exige_aprovacao_nao_fecha_por_atalho(self):
        anteprojeto = self.liberar_ate("anteprojeto")
        anteprojeto.abrir(self.user)
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

    def test_fase_bloqueada_nao_abre_nem_por_url(self):
        """A trava é real e não conselho: adiantar trabalho sobre decisão não
        confirmada é o retrabalho que o fluxo existe para cortar."""
        anteprojeto = self.fase("anteprojeto")
        self.assertTrue(anteprojeto.bloqueada)
        self.assertFalse(anteprojeto.abrir(self.user))
        self.assertRedirects(
            self.client.get(f"/fases/{anteprojeto.pk}/"),
            f"/projetos/{self.projeto.pk}/#fases",
        )

    def test_primeira_fase_nasce_aberta(self):
        """Projeto novo com tudo "não iniciada" parece projeto travado."""
        self.assertEqual(self.fase("briefing").status, Fase.EM_ELABORACAO)

    def test_aprovar_acende_a_proxima_sem_ninguem_clicar(self):
        proposta = self.liberar_ate("proposta")
        proposta.abrir(self.user)
        Arquivo.objects.create(
            empresa=self.grupo, projeto=self.projeto, fase=proposta,
            titulo="Proposta", arquivo=_png("p2.png"),
        )
        proposta.enviar_ao_cliente(self.user)
        proposta.registrar_resposta(True, "", self.user)
        self.assertEqual(self.fase("estudo_preliminar").status, Fase.EM_ELABORACAO)
        proposta.arquivos.first().arquivo.delete(save=False)

    def test_briefing_abre_direto_no_briefing(self):
        """A fase de briefing não tem material solto: ela É a conversa."""
        fase = self.fase("briefing")
        self.assertRedirects(
            self.client.get(f"/fases/{fase.pk}/"),
            f"/briefing/projeto/{self.projeto.pk}/responder/",
            target_status_code=302,
        )


class ViewsTests(BaseFase):
    def test_nao_envia_fase_vazia_ao_cliente(self):
        """Enviar sem material é pedir aprovação de nada."""
        fase = self.liberar_ate("proposta")
        fase.abrir(self.user)
        self.client.post(f"/fases/{fase.pk}/enviar/")
        fase.refresh_from_db()
        self.assertEqual(fase.status, Fase.EM_ELABORACAO)

    def test_anexar_arquivo_registra_no_historico(self):
        fase = self.liberar_ate("estudo_preliminar")
        self.client.post(
            f"/fases/{fase.pk}/anexar/",
            {"titulo": "Planta baixa", "arquivo": _png(), "categoria": "projeto", "fluxo": "interno"},
        )
        self.assertEqual(fase.arquivos.count(), 1)
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

    def test_resposta_do_cliente_pela_tela(self):
        fase = self.liberar_ate("proposta")
        fase.abrir(self.user)
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


class NavegacaoPorProjetoTests(BaseFase):
    """O que é de um projeto abre já recortado nele, sem filtrar à mão."""

    def test_listas_aceitam_o_projeto_pela_url(self):
        from django.contrib.auth.models import Group

        outro = Group.objects.create(name="Vizinho 3")
        alheio = Projeto.objects.create(
            empresa=outro, cliente=self.cliente, nome="Alheio 3", tipo="comercial"
        )
        for rota in ["/arquivos/", "/orcamentos/", "/propostas/", "/contratos/", "/regulatorio/"]:
            with self.subTest(rota=rota):
                resp = self.client.get(f"{rota}?projeto={self.projeto.pk}")
                self.assertEqual(resp.status_code, 200)
                self.assertContains(resp, "Dentro do projeto")
                # Projeto de outra empresa não vira contexto nem vaza nome.
                resp2 = self.client.get(f"{rota}?projeto={alheio.pk}")
                self.assertNotContains(resp2, "Alheio 3")

    def test_ficha_do_projeto_leva_para_os_registros_filtrados(self):
        resp = self.client.get(f"/projetos/{self.projeto.pk}/")
        for rota in ["/arquivos/", "/propostas/", "/contratos/", "/regulatorio/"]:
            self.assertContains(resp, f"{rota}?projeto={self.projeto.pk}")

    def test_orcamento_e_assunto_da_execucao_e_nao_do_projeto(self):
        """Orçamento é o custo de executar: quem precisa dele é quem toca a
        obra, não quem está desenhando."""
        from obras.models import Obra

        self.assertNotContains(
            self.client.get(f"/projetos/{self.projeto.pk}/"),
            f"/orcamentos/?projeto={self.projeto.pk}",
        )
        obra = Obra.objects.create(
            empresa=self.grupo, projeto=self.projeto, endereco="Rua A, 100"
        )
        self.assertContains(
            self.client.get(f"/obras/{obra.pk}/"), f"/orcamentos/?projeto={self.projeto.pk}"
        )

    def test_menu_nao_repete_o_que_e_de_projeto(self):
        """Menu é para o que atravessa projetos. Ter os dois caminhos fazia
        parecer que eram coisas diferentes."""
        nav = self.client.get("/").content.decode()
        nav = nav[nav.index('<nav class="app-nav"'):nav.index("</nav>")]
        for rota in ['href="/arquivos/"', 'href="/orcamentos/"', 'href="/propostas/"',
                     'href="/contratos/"', 'href="/regulatorio/"']:
            self.assertNotIn(rota, nav)
        for rota in ['href="/"', 'href="/projetos/"', 'href="/modelos/"', 'href="/financeiro/"']:
            self.assertIn(rota, nav)


class LembreteTests(BaseFase):
    """O combinado fica no topo, em post-it; o rastro desce para o histórico."""

    def test_lembrete_do_projeto_guarda_quando_e_quem(self):
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/lembrete/",
            {"texto": "Cliente quer a churrasqueira fechada."},
        )
        lembrete = self.projeto.lembretes.get()
        self.assertEqual(lembrete.autor, self.user)
        self.assertIsNotNone(lembrete.criado_em)


class ComplementarLivreTests(BaseFase):
    """Complementar que não cabe em lista fechada: acústico, automação."""

    def test_cria_uma_fase_por_nome(self):
        from fases.models import criar_complementares_avulsos

        criar_complementares_avulsos(self.projeto, "Acústico, Automação residencial")
        nomes = [f.nome for f in self.projeto.fases.filter(chave="comp_outro")]
        self.assertEqual(sorted(nomes), ["Acústico", "Automação residencial"])

    def test_ignora_vazio_e_repetido(self):
        from fases.models import criar_complementares_avulsos

        criar_complementares_avulsos(self.projeto, "Acústico, , acústico,  ")
        self.assertEqual(self.projeto.fases.filter(chave="comp_outro").count(), 1)

    def test_depende_do_anteprojeto_como_os_outros(self):
        from fases.models import criar_complementares_avulsos

        criar_complementares_avulsos(self.projeto, "Acústico")
        fase = self.projeto.fases.get(chave="comp_outro")
        self.assertTrue(fase.complementar)
        self.assertFalse(fase.liberada)
        self.assertIn("Anteprojeto", fase.impedimento)


class TelasQueRespondemTests(BaseFase):
    """Uma varredura rasa: toda tela principal responde 200.

    Erro de template não aparece em teste de lógica — o de tarefas só apareceu
    ao abrir a página no navegador, porque `|default:` com atributo de FK nula
    estoura em vez de cair no padrão.
    """

    def test_telas_principais_abrem(self):
        from briefing.services import semear_templates_padrao

        # Sem roteiro cadastrado o briefing encaminha para os modelos; aqui o
        # que se quer medir é a tela em si.
        semear_templates_padrao(self.grupo, self.user)
        # Briefing encaminha para o briefing e proposta tem tela própria; aqui
        # vale uma fase comum, e liberada, que é onde mora a tela genérica.
        fase = self.liberar_ate("estudo_preliminar")
        fase.abrir(self.user)
        rotas = [
            "/", "/agenda/", "/notificacoes/", "/modelos/",
            "/projetos/", "/clientes/", "/fornecedores/",
            "/financeiro/", "/precificacao/", "/escritorio/identidade/",
            "/arquivos/", "/orcamentos/", "/propostas/", "/contratos/",
            "/regulatorio/", "/projeto-novo/novo/",
            f"/projetos/{self.projeto.pk}/", f"/fases/{fase.pk}/",
            f"/briefing/projeto/{self.projeto.pk}/responder/",
        ]
        for rota in rotas:
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(rota).status_code, 200)

    def test_agenda_aceita_mes_pela_url(self):
        self.assertEqual(self.client.get("/agenda/?ano=2026&mes=12").status_code, 200)
        # Mês inválido cai no corrente em vez de estourar.
        self.assertEqual(self.client.get("/agenda/?ano=abc&mes=99").status_code, 200)

    def test_briefing_abre_em_leitura_depois_de_respondido(self):
        from briefing.models import Briefing, RespostaBriefing
        from briefing.services import semear_templates_padrao

        template = semear_templates_padrao(self.grupo, self.user)[0]
        briefing = Briefing.objects.create(projeto=self.projeto, empresa=self.grupo)
        RespostaBriefing.objects.create(
            briefing=briefing, empresa=self.grupo,
            pergunta=template.perguntas.first(), texto="Casal com dois filhos",
        )
        resposta = self.client.get(f"/briefing/projeto/{self.projeto.pk}/responder/")
        self.assertFalse(resposta.context["editando"])
        self.assertContains(resposta, "Editar briefing")
        # E com ?editar=1 volta ao formulário.
        self.assertTrue(
            self.client.get(
                f"/briefing/projeto/{self.projeto.pk}/responder/?editar=1"
            ).context["editando"]
        )

    def test_rota_antiga_dos_blocos_encaminha_para_a_tela_unica(self):
        from briefing.services import semear_templates_padrao

        semear_templates_padrao(self.grupo, self.user)
        self.assertRedirects(
            self.client.get(f"/briefing/projeto/{self.projeto.pk}/"),
            f"/briefing/projeto/{self.projeto.pk}/responder/",
        )


class LembreteDoProjetoTests(BaseFase):
    """Lembrete que não é de fase nenhuma vale para o projeto inteiro."""

    def test_cria_lembrete_no_projeto(self):
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/lembrete/",
            {"texto": "Cliente viaja em janeiro."},
        )
        lembrete = self.projeto.lembretes.get()
        self.assertIsNone(lembrete.fase_id)

    def test_editar_e_excluir(self):
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/lembrete/",
            {"texto": "Original"},
        )
        lembrete = self.projeto.lembretes.get()
        self.client.post(f"/fases/lembrete/{lembrete.pk}/editar/", {"texto": "Corrigido"})
        lembrete.refresh_from_db()
        self.assertEqual(lembrete.texto, "Corrigido")

        self.client.post(f"/fases/lembrete/{lembrete.pk}/remover/")
        self.assertFalse(self.projeto.lembretes.exists())

    def test_lembrete_de_outra_empresa_nao_pode_ser_editado(self):
        from django.contrib.auth.models import Group
        from fases.models import Lembrete

        outro = Group.objects.create(name="Vizinho 5")
        alheio = Projeto.objects.create(
            empresa=outro, cliente=self.cliente, nome="Alheio 5", tipo="comercial"
        )
        lembrete = Lembrete.objects.create(
            empresa=outro, projeto=alheio, texto="Sigiloso"
        )
        self.assertEqual(
            self.client.post(
                f"/fases/lembrete/{lembrete.pk}/editar/", {"texto": "invadido"}
            ).status_code,
            404,
        )


class ComplementaresEmLoteTests(BaseFase):
    def test_liga_e_desliga_de_uma_vez(self):
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/",
            {"complementares": ["comp_estrutural", "comp_eletrica"]},
        )
        chaves = set(self.projeto.fases.values_list("chave", flat=True))
        self.assertIn("comp_estrutural", chaves)
        self.assertIn("comp_eletrica", chaves)

        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/",
            {"complementares": ["comp_estrutural"]},
        )
        chaves = set(self.projeto.fases.values_list("chave", flat=True))
        self.assertIn("comp_estrutural", chaves)
        self.assertNotIn("comp_eletrica", chaves)

    def test_nao_desliga_complementar_com_trabalho_dentro(self):
        """Desmarcar num modal não pode apagar arquivo por engano."""
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/",
            {"complementares": ["comp_estrutural"]},
        )
        fase = self.projeto.fases.get(chave="comp_estrutural")
        Arquivo.objects.create(
            empresa=self.grupo, projeto=self.projeto, fase=fase,
            titulo="Cálculo", arquivo=_png("c.png"),
        )
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/", {"complementares": []}
        )
        self.assertTrue(self.projeto.fases.filter(chave="comp_estrutural").exists())
        fase.arquivos.first().arquivo.delete(save=False)

    def test_texto_livre_acrescenta_sem_apagar_os_marcados(self):
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/",
            {"complementares": ["comp_paisagismo"], "complementar_outro": "Acústico"},
        )
        chaves = list(self.projeto.fases.values_list("chave", flat=True))
        self.assertIn("comp_paisagismo", chaves)
        self.assertIn("comp_outro", chaves)


class AvisoDetalhadoTests(BaseFase):
    """O histórico precisa dizer o quê e onde, não só o verbo."""

    def test_aviso_guarda_lugar_e_link(self):
        from notificacoes.models import AvisoSistema

        fase = self.liberar_ate("estudo_preliminar")
        fase.abrir(self.user)
        Arquivo.objects.create(
            empresa=self.grupo, projeto=self.projeto, fase=fase,
            titulo="Planta", arquivo=_png("pl.png"),
        )
        self.client.post(f"/fases/{fase.pk}/enviar/")
        aviso = AvisoSistema.objects.filter(empresa=self.grupo).first()
        self.assertIn("Estudo preliminar", aviso.texto)
        self.assertIn(self.projeto.nome, aviso.texto)
        self.assertIn("Fase", aviso.onde)
        self.assertEqual(aviso.url, f"/fases/{fase.pk}/enviar/")
        fase.arquivos.first().arquivo.delete(save=False)

    def test_aviso_aparece_no_historico(self):
        fase = self.liberar_ate("estudo_preliminar")
        fase.abrir(self.user)
        Arquivo.objects.create(
            empresa=self.grupo, projeto=self.projeto, fase=fase,
            titulo="Planta", arquivo=_png("pl2.png"),
        )
        self.client.post(f"/fases/{fase.pk}/enviar/")
        resposta = self.client.get("/notificacoes/")
        self.assertContains(resposta, "Histórico de avisos")
        self.assertContains(resposta, "enviada ao cliente")
        fase.arquivos.first().arquivo.delete(save=False)


class AgendaNavegacaoTests(BaseFase):
    def test_link_do_mes_seguinte_nao_localiza_o_ano(self):
        """2026 formatado com separador vira "2.026" e o link quebra."""
        resposta = self.client.get("/agenda/?ano=2026&mes=12")
        self.assertContains(resposta, "ano=2027")
        self.assertNotContains(resposta, "ano=2.027")
        self.assertEqual(self.client.get("/agenda/?ano=2027&mes=1").status_code, 200)


class BriefingUnicoTests(BaseFase):
    """Briefing numa tela só, com um botão de salvar e saída para a proposta."""

    def setUp(self):
        super().setUp()
        from briefing.services import semear_templates_padrao

        self.template = semear_templates_padrao(self.grupo, self.user)[0]

    def test_um_post_salva_roteiro_e_blocos_e_leva_para_a_proposta(self):
        pergunta = self.template.perguntas.first()
        resposta = self.client.post(
            f"/briefing/projeto/{self.projeto.pk}/responder/",
            {
                f"t{pergunta.pk}": "Casal com um filho.",
                "perfil_usuarios": "Trabalham em casa duas tardes.",
                "restricoes": "Recuo lateral de 1,5 m.",
                "referencias": "", "estilo": "", "orcamento_previsto": "", "prazo_desejado": "",
            },
        )
        proposta = self.projeto.fases.get(chave="proposta")
        self.assertRedirects(resposta, f"/fases/{proposta.pk}/")

        self.projeto.briefing.refresh_from_db()
        self.assertEqual(self.projeto.briefing.perfil_usuarios, "Trabalham em casa duas tardes.")
        self.assertTrue(self.projeto.briefing.respostas.exists())

    def test_salvar_conclui_o_briefing_e_abre_a_proposta(self):
        pergunta = self.template.perguntas.first()
        self.client.post(
            f"/briefing/projeto/{self.projeto.pk}/responder/",
            {f"t{pergunta.pk}": "Resposta", "perfil_usuarios": "",
             "restricoes": "", "referencias": "", "estilo": "",
             "orcamento_previsto": "", "prazo_desejado": ""},
        )
        self.assertEqual(self.fase("briefing").status, Fase.APROVADA)
        self.assertEqual(self.fase("proposta").status, Fase.EM_ELABORACAO)

    def test_abre_em_edicao_enquanto_nao_respondido(self):
        resposta = self.client.get(f"/briefing/projeto/{self.projeto.pk}/responder/")
        self.assertTrue(resposta.context["editando"])
        self.assertContains(resposta, "Salvar briefing")

    def test_fase_de_proposta_tem_tela_propria(self):
        proposta = self.liberar_ate("proposta")
        proposta.abrir(self.user)
        resposta = self.client.get(f"/fases/{proposta.pk}/")
        self.assertContains(resposta, "Proposta de honorários")
        self.assertContains(resposta, "Contrato")
        # Sem tarefas nem prazo: a fase é só as duas peças.
        self.assertNotContains(resposta, "Tarefas desta fase")
        self.assertNotContains(resposta, "Prazo e responsável")

    def test_area_do_programa_soma_os_ambientes(self):
        from briefing.models import AmbientePrograma, Briefing

        briefing = Briefing.objects.create(projeto=self.projeto, empresa=self.grupo)
        for nome, area in [("Sala", 24), ("Cozinha", 12), ("Suíte", 18)]:
            AmbientePrograma.objects.create(
                briefing=briefing, empresa=self.grupo, nome=nome, area_aprox=area
            )
        resposta = self.client.get(f"/briefing/projeto/{self.projeto.pk}/responder/")
        self.assertEqual(resposta.context["area_programa"], 54)
