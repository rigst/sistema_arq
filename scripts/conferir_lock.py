#!/usr/bin/env python3
"""Confere se requirements.lock está de acordo com requirements.txt.

    python scripts/conferir_lock.py

O Dependabot atualiza requirements.txt, mas não reconhece requirements.lock
como arquivo de dependências — ele não casa com os nomes que a ferramenta
procura. Sem esta checagem os dois divergem em silêncio: o CI testa uma
versão e a imagem instala outra, que é o tipo de diferença que só aparece em
produção.

Não resolve nada nem acessa a rede: só compara o que os dois arquivos dizem.
"""

import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
REQUISITOS = RAIZ / "requirements.txt"
LOCK = RAIZ / "requirements.lock"


def pinos_do_requirements():
    pinos = {}
    for linha in REQUISITOS.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9._-]+)(?:\[[^\]]*\])?==([^\s;]+)", linha)
        if not m:
            print(f"não entendi a linha de requirements.txt: {linha!r}", file=sys.stderr)
            return None
        pinos[m.group(1).lower().replace("_", "-")] = m.group(2)
    return pinos


def pinos_do_lock():
    pinos = {}
    for linha in LOCK.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9._-]+)==([^\s\\]+)", linha)
        if m:
            pinos[m.group(1).lower().replace("_", "-")] = m.group(2)
    return pinos


def main():
    if not LOCK.exists():
        print("requirements.lock não existe. Rode: python scripts/gerar_lock.py", file=sys.stderr)
        return 1

    declarados = pinos_do_requirements()
    if declarados is None:
        return 1
    travados = pinos_do_lock()

    faltando = sorted(n for n in declarados if n not in travados)
    divergentes = sorted(
        (n, declarados[n], travados[n])
        for n in declarados
        if n in travados and declarados[n] != travados[n]
    )

    if not faltando and not divergentes:
        print(f"lock em dia: {len(declarados)} dependências diretas conferem.")
        return 0

    for nome in faltando:
        print(f"FALTA no lock: {nome}=={declarados[nome]}", file=sys.stderr)
    for nome, esperado, achado in divergentes:
        print(f"DIVERGE: {nome} — requirements.txt {esperado}, lock {achado}", file=sys.stderr)
    print("\nRegenere com: python scripts/gerar_lock.py", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
