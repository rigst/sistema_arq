from django.test import TestCase

from briefing.services import semear_templates_padrao
from contratos.services import garantir_modelos_padrao
from core.tenancy import obter_grupo_empresa_padrao
from crm.models import Cliente
from fornecedores.models import Fornecedor
from legal.testing import aceitar_documentos
from projetos.models import Projeto
from usuarios.models import Usuario


class AjustesDeProducaoTests(TestCase):
    def setUp(self):
        self.empresa = obter_grupo_empresa_padrao()
        self.usuario = Usuario.objects.create_user(
            username="login.ana",
            password="senha-de-teste",
            first_name="Ana",
            last_name="Altemann",
            nome_exibicao="Ana",
        )
        self.usuario.groups.add(self.empresa)
        aceitar_documentos(self.usuario)
        self.client.force_login(self.usuario)
        self.cliente = Cliente.objects.create(empresa=self.empresa, nome="Cliente")

    def test_menu_exibe_nome_real_e_painel_traz_acoes_do_projeto(self):
        projeto = Projeto.objects.create(
            empresa=self.empresa, cliente=self.cliente, nome="Parque", tipo="urbanismo"
        )
        resposta = self.client.get("/projetos/")
        self.assertContains(resposta, "Ana Altemann")
        self.assertNotContains(resposta, ">login.ana</span>")
        self.assertContains(resposta, f'/projetos/{projeto.pk}/editar/')
        self.assertContains(resposta, f'/projetos/{projeto.pk}/remover/')

    def test_ha_um_roteiro_e_uma_minuta_para_cada_tipo(self):
        roteiros = semear_templates_padrao(self.empresa, self.usuario)
        minutas = garantir_modelos_padrao(self.empresa, self.usuario)
        tipos = {valor for valor, _ in Projeto.TIPO_CHOICES}
        self.assertEqual({r.tipo_projeto for r in roteiros}, tipos)
        self.assertTrue(tipos.issubset(set(minutas.values_list("tipo_projeto", flat=True))))

    def test_novas_categorias_de_fornecedor_e_urbanismo_estao_disponiveis(self):
        categorias = dict(Fornecedor.CATEGORIA_CHOICES)
        self.assertEqual(categorias["comunicacao_visual"], "Comunicação visual")
        self.assertEqual(categorias["servicos_engenharia"], "Serviços de engenharia")
        self.assertEqual(categorias["freelancer"], "Freelancer")
        self.assertEqual(dict(Projeto.TIPO_CHOICES)["urbanismo"], "Urbanismo")

