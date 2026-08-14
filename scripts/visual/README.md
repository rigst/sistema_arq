# Diff visual

Ferramenta para provar que uma mudança de CSS **não** altera o que a tela
mostra. Não roda no CI: depende de servidor, banco com dados de demonstração
e navegador. É para usar à mão, antes de abrir o PR.

## Por que existe

Ao fundir seletores duplicados no `app.css`, a tentação é decidir pela leitura
da folha: "as duas regras declaram propriedades diferentes, então mesclar é
inofensivo". **Não é.** Três casos passaram por essa análise e quebraram a
tela:

- `.app-empresa-info strong` — uma regra no meio, agrupada com outro seletor,
  aplicava `text-shadow`. Ao subir o `text-shadow: none`, ela passou a vencer.
- `.frente-cta` — usado como `class="ds-btn--acao frente-cta"`. Ao subir
  `padding` e `font-size`, o `.ds-btn--acao` passou a vencer e o botão cresceu.

O segundo é o que resolve a discussão: **duas classes diferentes caem no mesmo
elemento**, e nenhuma análise da folha isolada descobre isso — precisa do DOM.

## Como usar

```bash
pip install playwright pillow && playwright install chromium

python manage.py migrate
python manage.py popular_dados_demo --usuario admin
python manage.py runserver 127.0.0.1:8971 --noreload &

export ARQ_SENHA='a senha do usuário admin'

# 1. controle: capture duas vezes SEM mudar nada
python scripts/visual/capturar.py /tmp/ctrl-a
python scripts/visual/capturar.py /tmp/ctrl-b
python scripts/visual/comparar.py /tmp/ctrl-a /tmp/ctrl-b

# 2. só se o controle der 0 diferenças, meça a mudança
git stash                                   # volta ao CSS original
python scripts/visual/capturar.py /tmp/antes
git stash pop                               # traz a mudança de volta
python scripts/visual/capturar.py /tmp/depois
python scripts/visual/comparar.py /tmp/antes /tmp/depois /tmp/diffs
```

**O passo 1 não é opcional.** Numa primeira tentativa aqui, 29 telas mobile
apareciam diferentes entre execuções idênticas, porque o screenshot saía antes
da fonte carregar. Sem o controle, aquilo teria sido lido como regressão — ou,
pior, uma regressão real teria se escondido no meio do ruído.

## O que esperar

Uma tela (`mobile--agenda`) costuma acusar ~15 px de diferença em cantos
arredondados, mesmo comparando o original consigo mesmo. É ruído de
rasterização daquela página, não efeito de mudança.
