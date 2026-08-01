from django.test import TestCase

from core.tenancy import obter_grupo_empresa_padrao

from crm.models import Cliente
from fornecedores.models import Fornecedor
from legal.testing import aceitar_documentos
from projetos.models import Projeto, criar_etapas_padrao
from usuarios.models import Usuario


class DisciplinaTests(TestCase):
    """Um projeto de arquitetura é vários projetos: cada disciplina tem dono."""

    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(username="disc", password="senha-de-teste")
        self.user.groups.add(self.grupo)
        aceitar_documentos(self.user)
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, cliente=self.cliente, nome="Casa", tipo="residencial"
        )

    def test_adiciona_disciplina_interna(self):
        self.client.post(
            f"/projetos/{self.projeto.pk}/disciplina/",
            {"nome": "estrutural", "interna": "on", "descricao": ""},
        )
        d = self.projeto.disciplinas.get()
        self.assertEqual(d.nome, "estrutural")
        self.assertEqual(d.responsavel_visivel, "escritório")

    def test_disciplina_externa_exige_projetista(self):
        self.client.post(
            f"/projetos/{self.projeto.pk}/disciplina/", {"nome": "estrutural", "descricao": ""}
        )
        self.assertFalse(self.projeto.disciplinas.exists())

    def test_disciplina_externa_com_fornecedor(self):
        fornecedor = Fornecedor.objects.create(
            empresa=self.grupo, nome="Calculista Silva", categoria="projeto"
        )
        self.client.post(
            f"/projetos/{self.projeto.pk}/disciplina/",
            {"nome": "estrutural", "fornecedor": fornecedor.pk, "descricao": ""},
        )
        self.assertEqual(self.projeto.disciplinas.get().responsavel_visivel, "Calculista Silva")

    def test_disciplina_avanca_por_etapas(self):
        self.client.post(
            f"/projetos/{self.projeto.pk}/disciplina/",
            {"nome": "arquitetonico", "interna": "on", "descricao": ""},
        )
        d = self.projeto.disciplinas.get()
        for esperado in ["andamento", "concluida", "concluida"]:
            self.client.post(f"/projetos/disciplina/{d.pk}/avancar/")
            d.refresh_from_db()
            self.assertEqual(d.status, esperado)

    def test_etapas_padrao_nao_criam_mais_acompanhamento_de_obra(self):
        """A obra é opcional; virar etapa de prancha para todo mundo criava uma
        linha de cronograma que a maioria nunca ia cumprir."""
        criar_etapas_padrao(self.projeto)
        nomes = list(self.projeto.etapas.values_list("nome", flat=True))
        self.assertNotIn("Acompanhamento de obra", nomes)
        self.assertIn("Projeto executivo", nomes)
