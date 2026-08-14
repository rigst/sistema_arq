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
            pagina.goto(f"{BASE}/login/", wait_until="domcontentloaded")
            pagina.fill("#id_username", USUARIO)
            pagina.fill("#id_password", SENHA)
            pagina.click("button[type=submit]")
            pagina.wait_for_load_state("load")

            for nome, caminho, _exige_login in PAGINAS:
                alvo = f"{BASE}{caminho}"
                # Duas tentativas: com htmx na página, uma navegação
                # concorrente às vezes interrompe o goto.
                for tentativa in (1, 2):
                    try:
                        resp = pagina.goto(alvo, wait_until="domcontentloaded", timeout=25000)
                        if resp and resp.status >= 400:
                            falhas.append(f"{nome} ({rotulo}): HTTP {resp.status}")
                            break
                        pagina.wait_for_load_state("load", timeout=15000)
                        pagina.add_style_tag(content=CSS_ESTATICO)
                        # Sem esperar a fonte, o screenshot sai com o fallback
                        # ainda no lugar: o texto reflui e o diff acusa mudança
                        # que não existe. Foi o que tornava o mobile instável.
                        pagina.wait_for_function(
                            "() => document.fonts.status === 'loaded'", timeout=10000
                        )
                        pagina.wait_for_timeout(600)
                        pagina.screenshot(
                            path=str(saida / f"{rotulo}--{nome}.png"),
                            full_page=True,
                            animations="disabled",
                        )
                        break
                    except Exception as e:
                        if tentativa == 2:
                            falhas.append(f"{nome} ({rotulo}): {type(e).__name__} {e}"[:130])
                        else:
                            pagina.wait_for_timeout(800)
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

    saida = pathlib.Path(sys.argv[1])
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
