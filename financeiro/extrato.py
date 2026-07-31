"""Importação e conciliação de extrato bancário (OFX e CSV)."""

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation


def parse_ofx(arquivo):
    """Retorna lista de {data, descricao, valor} a partir de um OFX."""
    from ofxparse import OfxParser

    conteudo = arquivo.read()
    if isinstance(conteudo, bytes):
        conteudo = conteudo.decode("latin-1", errors="ignore")
    ofx = OfxParser.parse(io.StringIO(conteudo))
    transacoes = []
    for conta in ofx.accounts:
        for t in conta.statement.transactions:
            transacoes.append(
                {"data": t.date.date(), "descricao": (t.memo or t.payee or "").strip(), "valor": Decimal(str(t.amount))}
            )
    return transacoes


def parse_csv(arquivo):
    """CSV simples com colunas: data (dd/mm/aaaa ou aaaa-mm-dd), descricao, valor.
    Aceita cabeçalho opcional."""
    conteudo = arquivo.read()
    if isinstance(conteudo, bytes):
        conteudo = conteudo.decode("utf-8-sig", errors="ignore")
    transacoes = []
    leitor = csv.reader(io.StringIO(conteudo), delimiter=_detectar_sep(conteudo))
    for linha in leitor:
        if len(linha) < 3:
            continue
        data = _parse_data(linha[0].strip())
        if data is None:  # provavelmente cabeçalho
            continue
        try:
            valor = Decimal(linha[2].strip().replace(".", "").replace(",", ".")) if "," in linha[2] else Decimal(linha[2].strip())
        except (InvalidOperation, ValueError):
            continue
        transacoes.append({"data": data, "descricao": linha[1].strip(), "valor": valor})
    return transacoes


def _detectar_sep(conteudo):
    primeira = conteudo.splitlines()[0] if conteudo.splitlines() else ""
    return ";" if primeira.count(";") >= primeira.count(",") else ","


def _parse_data(texto):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def conciliar(grupo, conta, transacoes):
    """Para cada transação: se houver um lançamento PREVISTO de mesmo valor na conta,
    marca-o como realizado (conciliação); senão cria um lançamento realizado novo.
    Retorna (conciliados, criados)."""
    from .models import Lancamento

    conciliados = 0
    criados = 0
    for tx in transacoes:
        tipo = "entrada" if tx["valor"] >= 0 else "saida"
        valor = abs(tx["valor"])
        previsto = Lancamento.objects.filter(
            empresa=grupo, conta=conta, status="previsto", tipo=tipo, valor=valor
        ).order_by("data").first()
        if previsto is not None:
            previsto.status = "realizado"
            previsto.data = tx["data"]
            previsto.save(update_fields=["status", "data"])
            conciliados += 1
        else:
            Lancamento.objects.create(
                empresa=grupo, conta=conta, tipo=tipo,
                descricao=tx["descricao"] or "Extrato importado",
                valor=valor, data=tx["data"], status="realizado",
                origem_tipo="extrato",
            )
            criados += 1
    return conciliados, criados
