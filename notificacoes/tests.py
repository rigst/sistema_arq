from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.factories import criar_empresa_e_usuario
from crm.models import Cliente
from obras.models import EtapaObra, Obra
from projetos.models import Projeto
from regulatorio.models import ObrigacaoTecnica
from tarefas.models import Tarefa

from .models import Notificacao
from .services import varrer_empresa


class VarreduraTests(TestCase):
    def setUp(self):
        self.user, self.grupo = criar_empresa_e_usuario()
        self.cliente = Cliente.objects.create(empresa=self.grupo, nome="Cliente")
        self.projeto = Projeto.objects.create(
            empresa=self.grupo, nome="Casa", cliente=self.cliente, status="ativo"
        )

    def test_tarefa_atrasada_gera_notificacao_critica(self):
        Tarefa.objects.create(
            empresa=self.grupo,
            titulo="Enviar planta",
            prazo=timezone.localdate() - timedelta(days=2),
            status="aberta",
        )
        varrer_empresa(self.grupo)
        n = Notificacao.objects.get(empresa=self.grupo)
        self.assertEqual(n.nivel, "critico")

    def test_projeto_parado_gera_alerta(self):
        Projeto.objects.filter(pk=self.projeto.pk).update(
            ultima_atualizacao=timezone.now() - timedelta(days=30)
        )
        varrer_empresa(self.grupo)
        self.assertTrue(
            Notificacao.objects.filter(chave=f"projeto-parado-{self.projeto.pk}").exists()
        )

    def test_obra_em_desvio_gera_alerta(self):
        obra = Obra.objects.create(empresa=self.grupo, projeto=self.projeto)
        EtapaObra.objects.create(
            empresa=self.grupo,
            obra=obra,
            nome="Estrutura",
            percentual_previsto=80,
            percentual_real=40,
            valor=Decimal("1000"),
        )
        varrer_empresa(self.grupo)
        self.assertTrue(Notificacao.objects.filter(chave=f"obra-desvio-{obra.pk}").exists())

    def test_obrigacao_vencida_gera_critico(self):
        o = ObrigacaoTecnica.objects.create(
            empresa=self.grupo,
            tipo="art",
            status="registrada",
            vencimento=timezone.localdate() - timedelta(days=1),
        )
        varrer_empresa(self.grupo)
        n = Notificacao.objects.get(chave=f"obrigacao-{o.pk}-vencida")
        self.assertEqual(n.nivel, "critico")

    def test_varredura_e_idempotente(self):
        Tarefa.objects.create(
            empresa=self.grupo,
            titulo="X",
            prazo=timezone.localdate() - timedelta(days=1),
            status="aberta",
        )
        varrer_empresa(self.grupo)
        varrer_empresa(self.grupo)
        self.assertEqual(Notificacao.objects.filter(empresa=self.grupo).count(), 1)
