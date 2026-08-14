#!/usr/bin/env python3
"""Captura as telas do sistema para comparação pixel a pixel.

    python scripts/visual/capturar.py saida/antes

Serve para provar que uma mudança de CSS não altera o que a tela mostra.
Análise estática da folha não dá essa garantia: duas classes diferentes podem
cair no mesmo elemento, e só o DOM renderizado revela isso.

Precisa de um servidor rodando com dados de demonstração:

    python manage.py migrate
    python manage.py popular_dados_demo --usuario <seu-usuario>
    python manage.py runserver 127.0.0.1:8971

E do Playwright com o Chromium instalado:

    pip install playwright && playwright install chromium

Configuração por ambiente:

    ARQ_BASE_URL   padrão http://127.0.0.1:8971
    ARQ_USUARIO    padrão admin
    ARQ_SENHA      obrigatória
    ARQ_CHROMIUM   caminho do binário, quando não for o que o Playwright acha
"""

import os
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

BASE = os.environ.get("ARQ_BASE_URL", "http://127.0.0.1:8971").rstrip("/")
USUARIO = os.environ.get("ARQ_USUARIO", "admin")
SENHA = os.environ.get("ARQ_SENHA", "")
CHROMIUM = os.environ.get("ARQ_CHROMIUM", "")

# Telas que cobrem o sistema inteiro. Ao acrescentar uma, prefira a que usa
# um componente ainda não exercitado por nenhuma outra.
PAGINAS = [
    ("login", "/login/", False),
    ("termos", "/termos/", False),
    ("privacidade", "/privacidade/", False),
    ("dashboard", "/", True),
    ("projetos", "/projetos/", True),
    ("projeto-detalhe", "/projetos/4/", True),
    ("orcamentos", "/orcamentos/", True),
    ("orcamento-detalhe", "/orcamentos/1/", True),
    ("contratos-modelos", "/contratos/modelos/", True),
    ("contrato-novo", "/contratos/novo/", True),
    ("contrato-detalhe", "/contratos/1/", True),
    ("proposta-detalhe", "/propostas/1/", True),
    ("obras", "/obras/", True),
    ("obra-detalhe", "/obras/1/", True),
    ("obra-nova", "/obras/nova/", True),
    ("financeiro", "/financeiro/", True),
    ("financeiro-dre", "/financeiro/dre/", True),
    ("notificacoes", "/notificacoes/", True),
    ("agenda", "/agenda/", True),
    ("clientes", "/clientes/", True),
    ("regulatorio", "/regulatorio/", True),
    ("fornecedores", "/fornecedores/", True),
    ("precificacao", "/precificacao/", True),
    ("identidade", "/escritorio/identidade/", True),
    ("briefing-roteiros", "/briefing/", True),
    ("modelos", "/modelos/", True),
    ("diagnostico", "/diagnostico/", True),
    ("jornada-abrir", "/projeto-novo/novo/", True),
    ("fase-detalhe", "/fases/1/", True),
]

VIEWPORTS = [("desktop", 1440, 900), ("mobile", 390, 844)]

# Congela o que varia entre execuções e poluiria o diff.
CSS_ESTATICO = (
    "*,*::before,*::after{animation:none!important;"
    "transition:none!important;caret-color:transparent!important}"
)


def destino_seguro(bruto):
    """Resolve o caminho de saída e recusa o que estiver fora de lugar.

    O caminho vem da linha de comando e vira gravação de dezenas de arquivos.
    Um valor errado — caminho relativo com "..", variável não expandida — grava
    fora do previsto. Aqui só o diretório de trabalho e o temporário do sistema
    são aceitos, que é onde as capturas fazem sentido.
    """
    alvo = pathlib.Path(bruto).expanduser().resolve()
    permitidos = [pathlib.Path.cwd().resolve(), pathlib.Path(tempfile.gettempdir()).resolve()]
    if not any(alvo == raiz or raiz in alvo.parents for raiz in permitidos):
        raise SystemExit(
            f"recusando gravar em {alvo}: use um caminho dentro de "
            f"{permitidos[0]} ou {permitidos[1]}"
        )
    return alvo


def _entrar(pagina):
    """Autentica e deixa a sessão pronta para navegar."""
    pagina.goto(f"{BASE}/login/", wait_until="domcontentloaded")
    pagina.fill("#id_username", USUARIO)
    pagina.fill("#id_password", SENHA)
    pagina.click("button[type=submit]")
    pagina.wait_for_load_state("load")


def _fotografar(pagina, alvo, destino):
    """Abre a página e grava a captura. Devolve o erro, ou None se deu certo."""
    resp = pagina.goto(alvo, wait_until="domcontentloaded", timeout=25000)
    if resp and resp.status >= 400:
        return f"HTTP {resp.status}"
    pagina.wait_for_load_state("load", timeout=15000)
    pagina.add_style_tag(content=CSS_ESTATICO)
    # Sem esperar a fonte, o screenshot sai com o fallback ainda no lugar: o
    # texto reflui e o diff acusa mudança que não existe. Foi o que tornava as
    # capturas mobile instáveis entre execuções idênticas.
    pagina.wait_for_function("() => document.fonts.status === 'loaded'", timeout=10000)
    pagina.wait_for_timeout(600)
    pagina.screenshot(path=str(destino), full_page=True, animations="disabled")
    return None


def _capturar_pagina(pagina, nome, caminho, rotulo, saida):
    """Tenta duas vezes: com htmx na página, uma navegação concorrente às
    vezes interrompe o goto."""
    for tentativa in (1, 2):
        try:
            erro = _fotografar(pagina, f"{BASE}{caminho}", saida / f"{rotulo}--{nome}.png")
            if erro:
                return f"{nome} ({rotulo}): {erro}"
            return None
        except Exception as e:
            if tentativa == 2:
                return f"{nome} ({rotulo}): {type(e).__name__} {e}"[:130]
            pagina.wait_for_timeout(800)
    return None


def capturar(saida):
    falhas = []
    with sync_playwright() as p:
        opcoes = {"executable_path": CHROMIUM} if CHROMIUM else {}
        navegador = p.chromium.launch(**opcoes)
        for rotulo, largura, altura in VIEWPORTS:
            ctx = navegador.new_context(
                viewport={"width": largura, "height": altura},
                device_scale_factor=1,
                reduced_motion="reduce",
            )
            pagina = ctx.new_page()
            _entrar(pagina)
            for nome, caminho, _exige_login in PAGINAS:
                falha = _capturar_pagina(pagina, nome, caminho, rotulo, saida)
                if falha:
                    falhas.append(falha)
            ctx.close()
        navegador.close()
    return falhas


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if not SENHA:
        print("Defina ARQ_SENHA com a senha do usuário de captura.", file=sys.stderr)
        return 2

    saida = destino_seguro(sys.argv[1])
    saida.mkdir(parents=True, exist_ok=True)
    falhas = capturar(saida)

    print(f"{len(list(saida.glob('*.png')))} capturas em {saida}")
    if falhas:
        print("falhas:")
        for f in falhas:
            print("  ", f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
