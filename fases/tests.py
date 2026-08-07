import io
from datetime import date

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
from tarefas.models import Tarefa
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
    def test_projeto_novo_nasce_com_proposta_e_contrato_separados(self):
        self.assertEqual(
            list(self.projeto.fases.values_list("chave", flat=True)),
            ["briefing", "proposta", "contrato", "estudo_preliminar", "anteprojeto", "executivo"],
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
        self.assertIn("Contrato", self.fase("estudo_preliminar").impedimento)

    def test_aprovar_uma_fase_libera_a_seguinte(self):
        proposta = self.liberar_ate("proposta")
        proposta.abrir(self.user)
        Arquivo.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            fase=proposta,
            titulo="Proposta",
            arquivo=_png("p.png"),
        )
        proposta.enviar_ao_cliente(self.user)
        proposta.registrar_resposta(True, "Pode seguir", self.user)
        self.assertTrue(self.fase("contrato").liberada)
        self.assertFalse(self.fase("estudo_preliminar").liberada)

    def test_ajustes_nao_liberam_a_seguinte(self):
        proposta = self.liberar_ate("proposta")
        proposta.abrir(self.user)
        proposta.enviar_ao_cliente(self.user)
        proposta.registrar_resposta(False, "Rever o prazo", self.user)
        self.assertEqual(proposta.status, Fase.AJUSTES)
        self.assertFalse(self.fase("contrato").liberada)

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

    def test_todos_os_complementares_dependem_do_projeto_executivo(self):
        for passo in catalogo.COMPLEMENTARES:
            self.assertEqual(catalogo.anterior_de(passo.chave), "executivo")

    def test_complementar_so_abre_depois_do_executivo(self):
        montar_fases(self.projeto, complementares=["comp_eletrica"])
        complementar = self.fase("comp_eletrica")
        self.projeto.fases.exclude(chave__in=["executivo", "comp_eletrica"]).update(
            status=Fase.APROVADA
        )
        self.assertFalse(complementar.abrir(self.user))
        executivo = self.fase("executivo")
        executivo.status = Fase.APROVADA
        executivo.save(update_fields=["status"])
        self.assertTrue(complementar.abrir(self.user))

    def test_pagina_do_projeto_exibe_os_sete_passos_na_ordem(self):
        resposta = self.client.get(f"/projetos/{self.projeto.pk}/")
        html = resposta.content.decode()
        nomes = [
            "Briefing",
            "Proposta",
            "Contrato",
            "Estudo preliminar",
            "Anteprojeto",
            "Projeto executivo",
            "Projetos complementares",
        ]
        posicoes = [html.index(nome) for nome in nomes]
        self.assertEqual(posicoes, sorted(posicoes))

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
            empresa=self.grupo,
            projeto=self.projeto,
            fase=proposta,
            titulo="Proposta",
            arquivo=_png("p2.png"),
        )
        proposta.enviar_ao_cliente(self.user)
        proposta.registrar_resposta(True, "", self.user)
        self.assertEqual(self.fase("contrato").status, Fase.EM_ELABORACAO)
        proposta.arquivos.first().arquivo.delete(save=False)

    def test_briefing_abre_direto_no_briefing(self):
        """A fase de briefing não tem material solto: ela É a conversa."""
        fase = self.fase("briefing")
        self.assertRedirects(
            self.client.get(f"/fases/{fase.pk}/"),
            f"/briefing/projeto/{self.projeto.pk}/responder/",
        )


class ViewsTests(BaseFase):
    def test_planejamento_atualiza_horas_e_datas_do_projeto(self):
        resposta = self.client.post(
            f"/projetos/{self.projeto.pk}/planejamento/",
            {"horas_estimadas": "96", "data_inicio": "2026-08-02", "data_prevista": "2026-10-15"},
        )
        self.assertRedirects(resposta, f"/projetos/{self.projeto.pk}/")
        self.projeto.refresh_from_db()
        self.assertEqual(str(self.projeto.horas_estimadas), "96.00")
        self.assertEqual(str(self.projeto.data_prevista), "2026-10-15")

    def test_fase_contrato_abre_o_contrato_diretamente(self):
        from contratos.models import Contrato

        fase = self.liberar_ate("contrato")
        fase.abrir(self.user)
        contrato = Contrato.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            titulo="Contrato Casa Ipê",
            valor_total=1000,
            corpo="Texto do contrato.",
        )
        self.assertRedirects(
            self.client.get(f"/fases/{fase.pk}/"),
            f"/contratos/{contrato.pk}/",
        )

    def test_documentos_comerciais_nao_usam_envio_generico_da_fase(self):
        fase = self.liberar_ate("proposta")
        fase.abrir(self.user)
        self.client.post(f"/fases/{fase.pk}/enviar/")
        fase.refresh_from_db()
        self.assertEqual(fase.status, Fase.EM_ELABORACAO)

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
            {
                "titulo": "Planta baixa",
                "arquivo": _png(),
                "categoria": "projeto",
                "fluxo": "interno",
            },
        )
        self.assertEqual(fase.arquivos.count(), 1)
        fase.arquivos.first().arquivo.delete(save=False)

    def test_arquivo_e_servido_pelo_sistema_e_nao_pela_pasta(self):
        fase = self.fase("estudo_preliminar")
        arquivo = Arquivo.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            fase=fase,
            titulo="Fachada",
            arquivo=_png("f.png"),
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
            empresa=self.grupo,
            projeto=self.projeto,
            fase=fase,
            titulo="Sem nome",
            arquivo=_png("x.png"),
        )
        self.client.post(
            f"/fases/arquivo/{arquivo.pk}/editar/",
            {"titulo": "Planta pavimento térreo", "categoria": "projeto", "observacoes": ""},
        )
        arquivo.refresh_from_db()
        self.assertEqual(arquivo.titulo, "Planta pavimento térreo")
        arquivo.arquivo.delete(save=False)

    def test_favorito_da_fase_aparece_nos_arquivos_principais(self):
        fase = self.fase("estudo_preliminar")
        arquivo = Arquivo.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            fase=fase,
            titulo="Planta aprovada",
            arquivo=_png("aprovada.png"),
            categoria="projeto",
        )

        resposta = self.client.post(
            f"/fases/arquivo/{arquivo.pk}/favorito/",
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET=f"arquivo-fase-{arquivo.pk}",
        )
        arquivo.refresh_from_db()
        self.assertTrue(arquivo.favorito)
        self.assertContains(resposta, 'aria-pressed="true"')
        self.assertContains(self.client.get(f"/projetos/{self.projeto.pk}/"), "Planta aprovada")

        resposta = self.client.post(
            f"/fases/arquivo/{arquivo.pk}/favorito/",
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="arquivos-principais",
        )
        arquivo.refresh_from_db()
        self.assertFalse(arquivo.favorito)
        self.assertContains(resposta, 'id="arquivos-principais"')
        self.assertNotContains(resposta, "Planta aprovada")
        arquivo.arquivo.delete(save=False)

    def test_arquivo_sem_fase_nao_pode_ser_marcado_como_principal(self):
        arquivo = Arquivo.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            titulo="Arquivo antigo",
            arquivo=_png("antigo.png"),
        )
        resposta = self.client.post(f"/fases/arquivo/{arquivo.pk}/favorito/")
        self.assertEqual(resposta.status_code, 404)
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

    def test_fase_proposta_nao_aceita_resposta_por_rota_generica(self):
        fase = self.liberar_ate("proposta")
        fase.abrir(self.user)
        Arquivo.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            fase=fase,
            titulo="Proposta",
            arquivo=_png("pr.png"),
        )
        self.client.post(f"/fases/{fase.pk}/enviar/")
        self.client.post(
            f"/fases/{fase.pk}/responder/", {"decisao": "aprovar", "parecer": "Fechado."}
        )
        fase.refresh_from_db()
        self.assertEqual(fase.status, Fase.EM_ELABORACAO)
        self.assertEqual(fase.parecer, "")
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


class TarefasDaFaseTests(BaseFase):
    def abrir_fase(self, chave="estudo_preliminar"):
        fase = self.liberar_ate(chave)
        fase.abrir(self.user)
        return fase

    def test_fase_semeia_entregaveis_usuais_uma_unica_vez(self):
        fase = self.abrir_fase()
        fase.prazo = date(2026, 9, 15)
        fase.save(update_fields=["prazo"])

        resposta = self.client.get(f"/fases/{fase.pk}/")

        self.assertContains(resposta, "Tarefas desta fase")
        self.assertContains(resposta, "3 tarefas · 28 h")
        self.assertNotContains(resposta, "Do briefing")
        self.assertEqual(list(fase.tarefas.values_list("titulo", flat=True)), list(fase.entrega))
        self.assertTrue(fase.tarefas.filter(prazo=date(2026, 9, 15)).exists())
        self.assertFalse(fase.tarefas.filter(horas_previstas=0).exists())

        self.client.get(f"/fases/{fase.pk}/")
        self.assertEqual(fase.tarefas.count(), len(fase.entrega))

    def test_complementar_tambem_recebe_tarefas_usuais(self):
        montar_fases(self.projeto, complementares=["comp_eletrica"])
        fase = self.abrir_fase("comp_eletrica")

        self.client.get(f"/fases/{fase.pk}/")

        self.assertEqual(list(fase.tarefas.values_list("titulo", flat=True)), list(fase.entrega))

    def test_crud_e_check_da_tarefa_funcionam_inline(self):
        fase = self.abrir_fase()
        self.client.get(f"/fases/{fase.pk}/")
        cabecalho_htmx = {"HTTP_HX_REQUEST": "true"}

        resposta = self.client.post(
            f"/fases/{fase.pk}/tarefa/",
            {
                "titulo": "Compatibilizar implantação",
                "prazo": "2026-09-20",
                "horas_previstas": "6",
            },
            **cabecalho_htmx,
        )
        tarefa = fase.tarefas.get(titulo="Compatibilizar implantação")
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'id="tarefas-fase"')
        self.assertEqual(tarefa.projeto, self.projeto)
        self.assertEqual(tarefa.fase, fase)

        resposta = self.client.get(f"/fases/tarefa/{tarefa.pk}/editar/")
        self.assertContains(resposta, 'value="2026-09-20"')

        resposta = self.client.post(
            f"/fases/tarefa/{tarefa.pk}/editar/",
            {
                "titulo": "Compatibilizar implantação e acessos",
                "prazo": "2026-09-22",
                "horas_previstas": "8",
            },
            **cabecalho_htmx,
        )
        tarefa.refresh_from_db()
        self.assertContains(resposta, "Compatibilizar implantação e acessos")
        self.assertEqual(tarefa.horas_previstas, 8)

        self.client.post(f"/fases/tarefa/{tarefa.pk}/alternar/", **cabecalho_htmx)
        tarefa.refresh_from_db()
        self.assertEqual(tarefa.status, "concluida")

        resposta = self.client.post(f"/fases/tarefa/{tarefa.pk}/remover/", **cabecalho_htmx)
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Tarefa.objects.filter(pk=tarefa.pk).exists())

    def test_tarefa_excluida_nao_e_recriada_ao_reabrir(self):
        fase = self.abrir_fase()
        self.client.get(f"/fases/{fase.pk}/")
        removida = fase.tarefas.first()
        titulo = removida.titulo
        removida.delete()

        self.client.get(f"/fases/{fase.pk}/")

        self.assertFalse(fase.tarefas.filter(titulo=titulo).exists())

    def test_aprovacao_abre_diretamente_a_proxima_fase(self):
        fase = self.abrir_fase()
        Arquivo.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            fase=fase,
            titulo="Estudo preliminar",
            arquivo=_png("estudo.png"),
        )
        self.client.post(f"/fases/{fase.pk}/enviar/")

        proxima = self.fase("anteprojeto")
        resposta = self.client.post(
            f"/fases/{fase.pk}/responder/",
            {"decisao": "aprovar", "parecer": "Aprovado."},
        )

        self.assertRedirects(resposta, f"/fases/{proxima.pk}/")
        proxima.refresh_from_db()
        self.assertEqual(proxima.status, Fase.EM_ELABORACAO)
        fase.arquivos.first().arquivo.delete(save=False)

    def test_ficha_do_projeto_oculta_tarefas_das_fases_bloqueadas(self):
        fase = self.fase("estudo_preliminar")
        fase.prazo = date(2026, 9, 15)
        fase.save(update_fields=["prazo"])

        resposta = self.client.get(f"/projetos/{self.projeto.pk}/")

        self.assertEqual(resposta.context["tarefas_total"], 0)
        self.assertEqual(resposta.context["tarefas_concluidas"], 0)
        self.assertEqual(resposta.context["tarefas_pendentes"], 0)
        self.assertEqual(len(resposta.context["proximas_tarefas"]), 0)
        self.assertContains(resposta, "Próximas tarefas")
        self.assertNotContains(resposta, "Horas projetadas × trabalhadas")
        self.assertNotContains(resposta, "Apresentação de conceito e referências")
        estudo = next(f for f in resposta.context["fases"] if f.chave == "estudo_preliminar")
        self.assertIsNone(estudo.horas_tarefas)

    def test_check_no_projeto_atualiza_contadores_inline(self):
        fase = self.abrir_fase()
        self.client.get(f"/projetos/{self.projeto.pk}/")
        tarefa = self.projeto.tarefas.filter(fase=fase).first()

        resposta = self.client.post(
            f"/projetos/tarefa/{tarefa.pk}/alternar/", HTTP_HX_REQUEST="true"
        )

        tarefa.refresh_from_db()
        self.assertEqual(tarefa.status, "concluida")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["tarefas_concluidas"], 1)
        self.assertContains(resposta, 'id="tarefas"')
        self.assertContains(resposta, "Tarefa concluída")
        self.assertContains(resposta, tarefa.titulo)


class NavegacaoPorProjetoTests(BaseFase):
    """O projeto reúne o que é central sem depender de listagens globais."""

    def test_listas_operacionais_aceitam_o_projeto_pela_url(self):
        from django.contrib.auth.models import Group

        outro = Group.objects.create(name="Vizinho 3")
        alheio = Projeto.objects.create(
            empresa=outro, cliente=self.cliente, nome="Alheio 3", tipo="comercial"
        )
        for rota in ["/orcamentos/", "/regulatorio/"]:
            with self.subTest(rota=rota):
                resp = self.client.get(f"{rota}?projeto={self.projeto.pk}")
                self.assertEqual(resp.status_code, 200)
                self.assertContains(resp, "Dentro do projeto")
                # Projeto de outra empresa não vira contexto nem vaza nome.
                resp2 = self.client.get(f"{rota}?projeto={alheio.pk}")
                self.assertNotContains(resp2, "Alheio 3")

    def test_ficha_reune_documentos_gerados_e_anexos_do_contrato(self):
        from briefing.models import Briefing
        from contratos.models import Contrato, Documento
        from propostas.models import Proposta

        Briefing.objects.create(empresa=self.grupo, projeto=self.projeto)
        proposta = Proposta.objects.create(
            empresa=self.grupo,
            cliente=self.cliente,
            projeto_gerado=self.projeto,
            titulo="Proposta Casa Ipê",
        )
        contrato = Contrato.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            titulo="Contrato Casa Ipê",
            corpo="Minuta principal",
        )
        documento = Documento.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            contrato=contrato,
            titulo="Contrato assinado",
            arquivo=_png("contrato-assinado.png"),
        )

        resposta = self.client.get(f"/projetos/{self.projeto.pk}/")
        self.assertContains(resposta, "Arquivos principais")
        self.assertContains(resposta, f"/briefing/projeto/{self.projeto.pk}/pdf/")
        self.assertContains(resposta, f"/propostas/{proposta.pk}/pdf/")
        self.assertContains(resposta, f"/contratos/{contrato.pk}/pdf/")
        self.assertContains(resposta, "Contrato assinado")
        self.assertNotContains(resposta, "Registros do projeto")
        documento.arquivo.delete(save=False)

    def test_paginas_antigas_nao_fazem_mais_parte_do_fluxo(self):
        rotas = [
            "/arquivos/",
            "/propostas/",
            "/propostas/nova/",
            "/contratos/",
            "/projetos/kanban/",
            "/projetos/novo/",
            f"/projeto-novo/{self.projeto.pk}/",
        ]
        for rota in rotas:
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(rota).status_code, 404)
        self.assertEqual(self.client.get("/clientes/novo/").status_code, 405)
        self.assertEqual(self.client.get("/fornecedores/novo/").status_code, 405)

    def test_orcamento_e_assunto_da_execucao_e_nao_do_projeto(self):
        """Orçamento é o custo de executar: quem precisa dele é quem toca a
        obra, não quem está desenhando."""
        from obras.models import Obra

        self.assertNotContains(
            self.client.get(f"/projetos/{self.projeto.pk}/"),
            f"/orcamentos/?projeto={self.projeto.pk}",
        )
        obra = Obra.objects.create(empresa=self.grupo, projeto=self.projeto, endereco="Rua A, 100")
        self.assertContains(
            self.client.get(f"/obras/{obra.pk}/"), f"/orcamentos/?projeto={self.projeto.pk}"
        )

    def test_menu_nao_repete_o_que_e_de_projeto(self):
        """Menu é para o que atravessa projetos. Ter os dois caminhos fazia
        parecer que eram coisas diferentes."""
        nav = self.client.get("/").content.decode()
        nav = nav[nav.index('<nav class="app-nav"') : nav.index("</nav>")]
        for rota in [
            'href="/arquivos/"',
            'href="/orcamentos/"',
            'href="/propostas/"',
            'href="/contratos/"',
            'href="/regulatorio/"',
        ]:
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

    def test_depende_do_projeto_executivo_como_os_outros(self):
        from fases.models import criar_complementares_avulsos

        criar_complementares_avulsos(self.projeto, "Acústico")
        fase = self.projeto.fases.get(chave="comp_outro")
        self.assertTrue(fase.complementar)
        self.assertFalse(fase.liberada)
        self.assertIn("Projeto executivo", fase.impedimento)


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
            "/",
            "/agenda/",
            "/notificacoes/",
            "/modelos/",
            "/projetos/",
            "/clientes/",
            "/fornecedores/",
            "/financeiro/",
            "/precificacao/",
            "/escritorio/identidade/",
            "/orcamentos/",
            "/regulatorio/",
            "/projeto-novo/novo/",
            f"/projetos/{self.projeto.pk}/",
            f"/fases/{fase.pk}/",
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
            briefing=briefing,
            empresa=self.grupo,
            pergunta=template.perguntas.first(),
            texto="Casal com dois filhos",
        )
        resposta = self.client.get(f"/briefing/projeto/{self.projeto.pk}/responder/")
        self.assertFalse(resposta.context["editando"])
        self.assertContains(resposta, "Editar briefing")
        # E com ?editar=1 volta ao formulário.
        self.assertTrue(
            self.client.get(f"/briefing/projeto/{self.projeto.pk}/responder/?editar=1").context[
                "editando"
            ]
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
        lembrete = Lembrete.objects.create(empresa=outro, projeto=alheio, texto="Sigiloso")
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

    def test_desliga_complementar_com_trabalho_dentro(self):
        """A interface confirma antes de remover; o backend remove fase e arquivos."""
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/",
            {"complementares": ["comp_estrutural"]},
        )
        fase = self.projeto.fases.get(chave="comp_estrutural")
        Arquivo.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            fase=fase,
            titulo="Cálculo",
            arquivo=_png("c.png"),
        )
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/", {"complementares": []}
        )
        self.assertFalse(self.projeto.fases.filter(chave="comp_estrutural").exists())

    def test_texto_livre_acrescenta_sem_apagar_os_marcados(self):
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/",
            {"complementares": ["comp_paisagismo"], "complementar_outro": "Acústico"},
        )
        chaves = list(self.projeto.fases.values_list("chave", flat=True))
        self.assertIn("comp_paisagismo", chaves)
        self.assertIn("comp_outro", chaves)

    def test_complementar_livre_e_mantido_ou_removido_pelo_mesmo_formulario(self):
        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/",
            {"complementar_outro": "Acústico"},
        )
        livre = self.projeto.fases.get(chave="comp_outro")

        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/",
            {"complementares_livres": [str(livre.pk)]},
        )
        self.assertTrue(self.projeto.fases.filter(pk=livre.pk).exists())

        self.client.post(
            f"/fases/projeto/{self.projeto.pk}/complementares/",
            {},
        )
        self.assertFalse(self.projeto.fases.filter(pk=livre.pk).exists())


class AvisoDetalhadoTests(BaseFase):
    """O histórico precisa dizer o quê e onde, não só o verbo."""

    def test_aviso_guarda_lugar_e_link(self):
        from notificacoes.models import AvisoSistema

        fase = self.liberar_ate("estudo_preliminar")
        fase.abrir(self.user)
        Arquivo.objects.create(
            empresa=self.grupo,
            projeto=self.projeto,
            fase=fase,
            titulo="Planta",
            arquivo=_png("pl.png"),
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
            empresa=self.grupo,
            projeto=self.projeto,
            fase=fase,
            titulo="Planta",
            arquivo=_png("pl2.png"),
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
                "referencias": "",
                "estilo": "",
                "orcamento_previsto": "",
                "prazo_desejado": "",
            },
        )
        proposta = self.projeto.proposta_origem
        self.assertRedirects(resposta, f"/propostas/{proposta.pk}/")

        self.projeto.briefing.refresh_from_db()
        self.assertEqual(self.projeto.briefing.perfil_usuarios, "Trabalham em casa duas tardes.")
        self.assertTrue(self.projeto.briefing.respostas.exists())

    def test_salvar_conclui_o_briefing_e_abre_a_proposta(self):
        pergunta = self.template.perguntas.first()
        self.client.post(
            f"/briefing/projeto/{self.projeto.pk}/responder/",
            {
                f"t{pergunta.pk}": "Resposta",
                "perfil_usuarios": "",
                "restricoes": "",
                "referencias": "",
                "estilo": "",
                "orcamento_previsto": "",
                "prazo_desejado": "",
            },
        )
        self.assertEqual(self.fase("briefing").status, Fase.APROVADA)
        self.assertEqual(self.fase("proposta").status, Fase.EM_ELABORACAO)

    def test_abre_em_edicao_enquanto_nao_respondido(self):
        resposta = self.client.get(f"/briefing/projeto/{self.projeto.pk}/responder/")
        self.assertTrue(resposta.context["editando"])
        self.assertContains(resposta, "Salvar briefing")

    def test_a_pagina_toda_envia_por_um_formulario_so(self):
        """O texto do botão sobrevive mesmo sem a tag <form>; ele não basta.

        Roteiro, blocos NBR e botão de salvar são um POST só, e o que
        costura os três é o atributo form="briefing" nos campos que ficam
        fora da tag. Sem isso a página parece certa e não salva nada.
        """
        resposta = self.client.get(f"/briefing/projeto/{self.projeto.pk}/responder/")
        html = resposta.content.decode()
        self.assertIn('id="briefing"', html)
        self.assertIn('form="briefing"', html)
        # O programa fica no meio, com formulário próprio de adicionar.
        self.assertIn('id="programa-bloco"', html)
        self.assertIn("programa-add", html)

    def test_fase_de_proposta_abre_rascunho_completo_diretamente(self):
        fase = self.liberar_ate("proposta")
        fase.abrir(self.user)
        resposta = self.client.get(f"/fases/{fase.pk}/")
        proposta = self.projeto.proposta_origem
        self.assertRedirects(resposta, f"/propostas/{proposta.pk}/")
        detalhe = self.client.get(f"/propostas/{proposta.pk}/")
        self.assertContains(detalhe, "Termos da proposta")
        self.assertContains(detalhe, "Ambientes / etapas")

    def test_briefing_respondido_pode_ser_gerado_em_pdf(self):
        pergunta = self.template.perguntas.first()
        self.client.post(
            f"/briefing/projeto/{self.projeto.pk}/responder/",
            {f"t{pergunta.pk}": "Resposta para o PDF"},
        )
        resposta = self.client.get(f"/briefing/projeto/{self.projeto.pk}/pdf/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Content-Type"], "application/pdf")
        self.assertIn(
            f'filename="briefing-{self.projeto.pk}.pdf"',
            resposta["Content-Disposition"],
        )

    def test_area_do_programa_soma_os_ambientes(self):
        from briefing.models import AmbientePrograma, Briefing

        briefing = Briefing.objects.create(projeto=self.projeto, empresa=self.grupo)
        for nome, area in [("Sala", 24), ("Cozinha", 12), ("Suíte", 18)]:
            AmbientePrograma.objects.create(
                briefing=briefing, empresa=self.grupo, nome=nome, area_aprox=area
            )
        resposta = self.client.get(f"/briefing/projeto/{self.projeto.pk}/responder/")
        self.assertEqual(resposta.context["area_programa"], 54)
