from datetime import date
from decimal import Decimal

from django.test import TestCase

from contratos.models import Contrato
from core.tenancy import obter_grupo_empresa_padrao
from financeiro.models import ContaBancaria, Lancamento
from legal.testing import aceitar_documentos
from precificacao.models import ConfiguracaoPrecificacao, FatorPrecificacao
from projetos.models import Projeto
from propostas.models import Proposta
from usuarios.models import Usuario


class JornadaCompletaDaReleaseTests(TestCase):
    """Smoke E2E com dados fictícios, da abertura ao contas a receber."""

    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user(
            username="release-e2e", password="senha-de-teste-123", nome_exibicao="Arquiteta Demo"
        )
        self.user.groups.add(self.grupo)
        aceitar_documentos(self.user)
        self.client.force_login(self.user)
        ConfiguracaoPrecificacao.objects.create(
            empresa=self.grupo, hora_tecnica_manual=Decimal("100.00")
        )
        self.fator = FatorPrecificacao.objects.create(
            empresa=self.grupo, nome="Alta complexidade", percentual=Decimal("20.00")
        )
        ContaBancaria.objects.create(
            empresa=self.grupo, nome="Conta operacional", saldo_inicial=Decimal("0")
        )

    def test_briefing_proposta_contrato_e_financeiro(self):
        abertura = self.client.post(
            "/projeto-novo/novo/",
            {
                "cliente_nome": "Cliente Fictício",
                "cliente_email": "cliente@example.com",
                "nome": "Residência E2E",
                "tipo": "residencial",
                "cidade": "Curitiba",
                "uf": "PR",
                "complementares": ["comp_eletrica"],
            },
        )
        projeto = Projeto.objects.get(nome="Residência E2E")
        self.assertRedirects(abertura, f"/briefing/projeto/{projeto.pk}/responder/")

        self.client.get(abertura.url)
        briefing = self.client.post(
            abertura.url,
            {
                "perfil_usuarios": "Casal com trabalho remoto.",
                "orcamento_previsto": "300000.00",
                "prazo_desejado": "2027-02-01",
                "restricoes": "Condomínio fechado.",
                "referencias": "Referências fictícias.",
                "estilo": "Contemporâneo",
            },
        )
        proposta = Proposta.objects.get(projeto_gerado=projeto)
        self.assertRedirects(briefing, f"/propostas/{proposta.pk}/")

        self.client.post(
            f"/propostas/{proposta.pk}/hora-tecnica/", {"fatores": [self.fator.pk]}
        )
        proposta.refresh_from_db()
        self.assertEqual(proposta.hora_tecnica_aplicada, Decimal("120.00"))

        self.client.post(
            f"/propostas/{proposta.pk}/item/",
            {"descricao": "Estudo preliminar", "horas_estimadas": "40"},
        )
        self.client.post(
            f"/propostas/{proposta.pk}/",
            {
                "titulo": proposta.titulo,
                "cliente": proposta.cliente_id,
                "tipo_projeto": proposta.tipo_projeto,
                "validade_dias_uteis": "10",
                "observacoes": "Proposta fictícia para teste E2E.",
                "acao": "enviar",
            },
        )
        proposta.refresh_from_db()
        self.assertEqual(proposta.status, "enviada")

        aprovacao = self.client.post(f"/propostas/{proposta.pk}/aprovar/")
        contrato = Contrato.objects.get(projeto=projeto)
        self.assertRedirects(aprovacao, f"/contratos/{contrato.pk}/")
        self.assertGreater(contrato.valor_total, 0)
        self.assertTrue(contrato.corpo.strip())

        self.client.post(f"/contratos/{contrato.pk}/enviar/")
        self.client.post(f"/contratos/{contrato.pk}/aprovar/")
        self.client.post(
            f"/contratos/{contrato.pk}/assinatura/",
            {"data_assinatura": date(2026, 9, 5).isoformat()},
        )
        self.client.post(
            f"/contratos/{contrato.pk}/parcelas/",
            {"quantidade": "2", "primeira_data": date(2026, 9, 10).isoformat()},
        )
        self.client.post(f"/contratos/{contrato.pk}/lancar/")

        contrato.refresh_from_db()
        projeto.refresh_from_db()
        self.assertEqual(contrato.status, "ativo")
        self.assertEqual(contrato.parcelas.count(), 2)
        self.assertEqual(
            Lancamento.objects.filter(
                empresa=self.grupo, projeto=projeto, tipo="entrada", status="previsto"
            ).count(),
            2,
        )
        self.assertEqual(projeto.fases.get(chave="contrato").status, "aprovada")
