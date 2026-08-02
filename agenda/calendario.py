"""O mês em forma de grade, com os compromissos pendurados em cada dia.

O calendário é montado no servidor de propósito: a agenda precisa funcionar sem
JavaScript, e a navegação entre meses é um link — o que também faz cada mês ter
URL própria, para poder ser guardado nos favoritos ou enviado para alguém.
"""

import calendar
from dataclasses import dataclass, field
from datetime import date

from django.utils import timezone

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
# Segunda a domingo, como se lê agenda no Brasil.
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


@dataclass
class Dia:
    data: date
    no_mes: bool
    hoje: bool
    compromissos: list = field(default_factory=list)

    @property
    def fim_de_semana(self):
        return self.data.weekday() >= 5


def dia_local(compromisso):
    """O dia em que o compromisso acontece para quem está olhando a agenda.

    `inicio` é guardado em UTC, e `inicio.date()` devolvia o dia de lá: uma
    reunião das 22h25 de segunda caía na terça da grade, enquanto a lista
    logo abaixo — que o template converte para o fuso local — mostrava a
    segunda. Dois dias diferentes para o mesmo compromisso, na mesma tela.
    """
    if getattr(compromisso, "prazo", None):
        return compromisso.prazo
    return timezone.localtime(compromisso.inicio).date()


def nome_do_mes(ano, mes):
    return f"{MESES[mes - 1]} de {ano}"


def vizinhos(ano, mes):
    """(ano, mês) do anterior e do seguinte."""
    anterior = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    seguinte = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return anterior, seguinte


def montar_mes(ano, mes, compromissos, hoje=None):
    """Semanas do mês, cada uma com sete Dias já com os compromissos dentro.

    A grade inclui os dias vizinhos que completam a primeira e a última semana:
    sem eles a linha fica torta e a leitura por coluna de dia da semana quebra.
    """
    hoje = hoje or date.today()

    por_dia = {}
    for c in compromissos:
        por_dia.setdefault(dia_local(c), []).append(c)

    semanas = []
    for semana in calendar.Calendar(firstweekday=0).monthdatescalendar(ano, mes):
        semanas.append(
            [
                Dia(
                    data=d,
                    no_mes=d.month == mes,
                    hoje=d == hoje,
                    compromissos=por_dia.get(d, []),
                )
                for d in semana
            ]
        )
    return semanas
