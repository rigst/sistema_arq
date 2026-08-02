"""A agenda é a única tela em que a mesma data aparece duas vezes.

Grade e lista precisam dizer o mesmo dia. Quando divergiam, o compromisso das
22h25 estava na segunda da lista e na terça do calendário — e ninguém sabe qual
das duas acreditar.
"""

from datetime import datetime, timezone as utc

from django.test import TestCase
from django.utils import timezone

from agenda import calendario
from agenda.models import Compromisso
from core.tenancy import obter_grupo_empresa_padrao
from legal.testing import aceitar_documentos
from usuarios.models import Usuario


class DiaLocalTests(TestCase):
    def setUp(self):
        self.grupo = obter_grupo_empresa_padrao()
        self.user = Usuario.objects.create_user("ana", password="senha-de-teste")
        self.user.groups.add(self.grupo)
        aceitar_documentos(self.user)
        self.client.force_login(self.user)
        # 4/8/2026 01:25 UTC é 3/8/2026 22:25 em São Paulo (UTC-3).
        self.compromisso = Compromisso.objects.create(
            empresa=self.grupo,
            criado_por=self.user,
            titulo="Reunião de briefing",
            inicio=datetime(2026, 8, 4, 1, 25, tzinfo=utc.utc),
        )

    def test_dia_local_e_o_do_fuso_do_escritorio(self):
        self.assertEqual(self.compromisso.inicio.date().day, 4)
        self.assertEqual(calendario.dia_local(self.compromisso).day, 3)

    def test_grade_pendura_no_mesmo_dia_que_a_lista(self):
        semanas = calendario.montar_mes(2026, 8, [self.compromisso], timezone.localdate())
        dias_com = [d.data for semana in semanas for d in semana if d.compromissos]
        self.assertEqual([d.day for d in dias_com], [3])

    def test_a_tela_mostra_o_compromisso_no_mes_local(self):
        resposta = self.client.get("/agenda/?ano=2026&mes=8")
        titulos = [c.titulo for c, _form in resposta.context["do_mes"]]
        self.assertEqual(titulos, ["Reunião de briefing"])
