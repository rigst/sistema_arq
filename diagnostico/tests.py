from django.test import Client, TestCase

from .perguntas import PONTOS_MAXIMO, avaliar


class DiagnosticoScoreTests(TestCase):
    def test_pontuacao_maxima_e_avancado(self):
        respostas = {"projetos": 2, "prazos": 2, "precificacao": 2, "financeiro": 2, "tarefas": 2}
        pontos, faixa, _ = avaliar(respostas)
        self.assertEqual(pontos, PONTOS_MAXIMO)
        self.assertEqual(faixa, "Avançado")

    def test_pontuacao_minima_e_inicial(self):
        respostas = {"projetos": 0, "prazos": 0, "precificacao": 0, "financeiro": 0, "tarefas": 0}
        pontos, faixa, _ = avaliar(respostas)
        self.assertEqual(pontos, 0)
        self.assertEqual(faixa, "Inicial")

    def test_respostas_invalidas_sao_ignoradas(self):
        pontos, _faixa, _ = avaliar({"projetos": "x", "prazos": None})
        self.assertEqual(pontos, 0)


class DiagnosticoViewTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")

    def test_get_publico_sem_login(self):
        self.assertEqual(self.client.get("/diagnostico/").status_code, 200)

    def test_post_mostra_resultado(self):
        resp = self.client.post(
            "/diagnostico/",
            {"projetos": 2, "prazos": 2, "precificacao": 1, "financeiro": 1, "tarefas": 1},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Intermediário")
