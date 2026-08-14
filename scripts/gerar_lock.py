#!/usr/bin/env python3
"""Regenera requirements.lock a partir de requirements.txt.

    python scripts/gerar_lock.py

O lock existe para o Dockerfile instalar com --require-hashes: sem ele, as
dependências transitivas ficam soltas e o conteúdo da imagem muda sozinho
entre dois builds do mesmo commit.

Duas decisões que não são óbvias:

1. A resolução é feita para o Python da imagem (PYTHON_ALVO), não para o
   interpretador que roda este script. Resolver no 3.12 e instalar no 3.14
   pode dar conjuntos diferentes, e com --require-hashes a diferença vira
   falha de build.

2. Os hashes cobrem todos os artefatos publicados de cada versão, não só o
   escolhido aqui. É o que mantém o lock válido em outra arquitetura.

O ofxparse é resolvido à parte: a 0.21 só é publicada como sdist, e o pip
exige --only-binary :all: junto de --python-version. As dependências dele
entram na lista de entrada para o resolvedor enxergá-las.
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "requirements.txt"
SAIDA = RAIZ / "requirements.lock"

PYTHON_ALVO = "3.14"
# Só-sdist: fica fora da resolução e entra fixado à mão, com as dependências
# dele declaradas para o resolvedor.
SDIST_ONLY = {"ofxparse": ["beautifulsoup4", "lxml", "six"]}


def resolver(requisitos, destino_relatorio):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(requisitos) + "\n")
        caminho = f.name
    with tempfile.TemporaryDirectory() as alvo:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--dry-run",
                "--quiet",
                "--ignore-installed",
                "--python-version",
                PYTHON_ALVO,
                "--only-binary",
                ":all:",
                "--target",
                alvo,
                "--report",
                str(destino_relatorio),
                "-r",
                caminho,
            ],
            check=True,
        )


def hashes_de(nome, versao):
    url = f"https://pypi.org/pypi/{nome}/{versao}/json"
    with urllib.request.urlopen(url) as r:
        info = json.load(r)
    digests = sorted({a["digests"]["sha256"] for a in info.get("urls") or []})
    if not digests:
        raise SystemExit(f"sem artefatos publicados para {nome}=={versao}")
    return digests


def main():
    declarados = [
        linha.strip()
        for linha in ENTRADA.read_text(encoding="utf-8").splitlines()
        if linha.strip() and not linha.startswith("#")
    ]

    fixados_a_mao = {}
    entrada = []
    for req in declarados:
        nome = req.split("==")[0].split("[")[0].strip().lower()
        if nome in SDIST_ONLY:
            fixados_a_mao[nome] = req.split("==", 1)[1]
            entrada.extend(SDIST_ONLY[nome])
        else:
            entrada.append(req)

    with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False) as f:
        relatorio = pathlib.Path(f.name)
    resolver(entrada, relatorio)

    pacotes = {
        item["metadata"]["name"].lower(): item["metadata"]["version"]
        for item in json.loads(relatorio.read_text())["install"]
    }
    pacotes.update(fixados_a_mao)

    linhas = [
        "# Gerado por scripts/gerar_lock.py — não edite à mão.",
        "#",
        f"# Resolvido para Python {PYTHON_ALVO} (o da imagem do Dockerfile),",
        "# incluindo as transitivas. Os hashes cobrem todos os artefatos de cada",
        "# versão, então o arquivo vale em qualquer arquitetura.",
        "#",
        "# Depois de mexer em requirements.txt:  python scripts/gerar_lock.py",
        "",
    ]
    for nome in sorted(pacotes):
        versao = pacotes[nome]
        digests = hashes_de(nome, versao)
        print(f"  {nome}=={versao} ({len(digests)} artefatos)", file=sys.stderr)
        corpo = f"{nome}=={versao}"
        for d in digests:
            corpo += f" \\\n    --hash=sha256:{d}"
        linhas.append(corpo)

    SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"\n{len(pacotes)} pacotes em {SAIDA.relative_to(RAIZ)}", file=sys.stderr)


if __name__ == "__main__":
    main()
