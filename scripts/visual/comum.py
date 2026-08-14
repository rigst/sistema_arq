"""O que capturar.py e comparar.py compartilham."""

import pathlib
import tempfile


def destino_seguro(bruto):
    """Resolve um caminho vindo da linha de comando e recusa o que estiver
    fora de lugar.

    Esses caminhos viram leitura e gravação de dezenas de arquivos. Um valor
    errado — relativo com "..", variável de ambiente não expandida — atinge
    diretório que ninguém pretendia. Aqui só o diretório de trabalho e o
    temporário do sistema são aceitos, que é onde capturas fazem sentido.
    """
    alvo = pathlib.Path(bruto).expanduser().resolve()
    permitidos = [pathlib.Path.cwd().resolve(), pathlib.Path(tempfile.gettempdir()).resolve()]
    if not any(alvo == raiz or raiz in alvo.parents for raiz in permitidos):
        raise SystemExit(
            f"recusando usar {alvo}: escolha um caminho dentro de "
            f"{permitidos[0]} ou {permitidos[1]}"
        )
    return alvo
