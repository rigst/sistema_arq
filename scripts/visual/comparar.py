#!/usr/bin/env python3
"""Compara dois diretórios de capturas, pixel a pixel.

    python scripts/visual/comparar.py saida/antes saida/depois [saida/diffs]

Sai com 0 quando tudo bate. Onde houver diferença, grava um PNG realçando a
região — o valor de cada canal é multiplicado, senão a diferença some no
escuro.

Antes de confiar no veredito, rode o controle: capture duas vezes SEM mudar
nada e compare. Se der diferença, o instrumento não está estável e qualquer
conclusão sobre a mudança é ruído. Fonte carregando tarde já causou isso aqui.
"""

import pathlib
import sys

from PIL import Image, ImageChops


def comparar(dir_a, dir_b, dir_diff):
    iguais, diferentes, ausentes = [], [], []
    for fa in sorted(dir_a.glob("*.png")):
        fb = dir_b / fa.name
        if not fb.exists():
            ausentes.append(fa.name)
            continue
        ia = Image.open(fa).convert("RGB")
        ib = Image.open(fb).convert("RGB")
        if ia.size != ib.size:
            diferentes.append((fa.name, f"tamanho {ia.size} vs {ib.size}"))
            continue
        dif = ImageChops.difference(ia, ib)
        if dif.getbbox() is None:
            iguais.append(fa.name)
            continue
        n = sum(1 for p in dif.getdata() if p != (0, 0, 0))
        pct = 100.0 * n / (ia.size[0] * ia.size[1])
        diferentes.append((fa.name, f"{n} px ({pct:.3f}%) região={dif.getbbox()}"))
        if dir_diff is not None:
            dir_diff.mkdir(parents=True, exist_ok=True)
            dif.point(lambda v: min(255, v * 12)).save(dir_diff / f"DIFF-{fa.name}")
    return iguais, diferentes, ausentes


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    dir_a = pathlib.Path(sys.argv[1])
    dir_b = pathlib.Path(sys.argv[2])
    dir_diff = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None

    iguais, diferentes, ausentes = comparar(dir_a, dir_b, dir_diff)
    print(f"idênticas : {len(iguais)}")
    print(f"diferentes: {len(diferentes)}")
    if ausentes:
        print(f"ausentes  : {len(ausentes)} -> {ausentes[:5]}")
    for nome, detalhe in diferentes:
        print(f"   {nome:40} {detalhe}")
    return 1 if (diferentes or ausentes) else 0


if __name__ == "__main__":
    sys.exit(main())
