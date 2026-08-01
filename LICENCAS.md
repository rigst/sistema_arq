# Licenças — A.R.Q.

Resumo das licenças das dependências e recomendação de licença para o app.

## Dependências diretas (requirements.txt)

| Pacote | Licença | Tipo |
|---|---|---|
| Django | BSD-3-Clause | permissiva |
| asgiref | BSD-3-Clause | permissiva |
| dj-database-url | BSD-3-Clause | permissiva |
| **psycopg[binary]** | **LGPL-3.0-or-later** | copyleft fraco (biblioteca) |
| pillow | HPND (estilo MIT/BSD) | permissiva |
| celery | BSD-3-Clause | permissiva |
| redis (redis-py) | MIT | permissiva |
| gunicorn | MIT | permissiva |
| sqlparse | BSD-3-Clause | permissiva |
| weasyprint | BSD-3-Clause | permissiva |
| ofxparse | MIT | permissiva |

## Transitivas relevantes

| Pacote | Licença | Observação |
|---|---|---|
| **Pyphen** (via WeasyPrint) | GPL-2.0 **ou** LGPL-2.1 **ou** MPL-1.1 (tri-licença) | você escolhe uma; opte por LGPL ou MPL para evitar o GPL |
| lxml | BSD-3-Clause | permissiva |
| cffi, pycparser | MIT | permissiva |
| tinycss2, cssselect2, pydyf, fonttools, webencodings | BSD/MIT | permissivas |
| beautifulsoup4, soupsieve, tinyhtml5 | MIT | permissivas |
| brotli, zopfli | MIT | permissivas |

## Front-end (vendorizado em static/)

| Item | Licença |
|---|---|
| htmx 2.x (`static/js/htmx.min.js`) | BSD-2-Clause (0BSD/BSD) |
| `stolben-ui.css` / `stolben-ui.js` | proprietário do autor (código próprio) |
| Fontes Inter e Manrope (Google Fonts) | SIL Open Font License 1.1 |

## Análise

- **Quase tudo é permissivo** (MIT/BSD/HPND): não obriga a abrir o código do app nem
  impõe condições ao seu licenciamento.
- **Único copyleft no runtime: `psycopg` (LGPL-3.0).** A LGPL, para uso como **biblioteca**
  (o app apenas importa o pacote, instalado separadamente via pip), **não obriga** a abrir o
  código do app. A obrigação prática é permitir a substituição/atualização da própria lib
  LGPL — o que já ocorre naturalmente, já que ela é instalada como pacote independente.
- **`Pyphen` é tri-licenciado** (GPL/LGPL/MPL). Tri-licença significa que você **escolhe**
  uma das opções; escolhendo LGPL-2.1 ou MPL-1.1, não há obrigação de GPL. Além disso, o
  Pyphen só é usado para hifenização na geração de PDF (WeasyPrint).

**Conclusão:** nenhuma dependência força o app a ser open source. Você pode licenciar o
código do A.R.Q. como quiser.

## Recomendação de licença do app

Como é um app **gratuito** e sem intenção comercial, a recomendação é **MIT** — a mais
simples e permissiva, compatível com todas as dependências acima. Alternativas:

- **MIT** (recomendada): máxima simplicidade e adoção; deixa o portfólio reutilizável.
- **BSD-3-Clause**: equivalente à MIT, com cláusula de não-endosso.
- **Apache-2.0**: permissiva + concessão explícita de patentes (mais “corporativa”).
- **Proprietário/privado**: se não quiser permitir reuso; basta não publicar uma licença
  e manter o repositório privado.

> Observação: distribuir binários de `psycopg`/`Pyphen` (ex.: em uma imagem Docker) mantém
> as obrigações LGPL — na prática, disponibilizar as versões dessas libs e permitir sua
> troca. Rodando via `pip install`, isso já é atendido.

## Imagens e tipografia

**Fotos** (`static/img/*.jpg`): Unsplash — a
[Unsplash License](https://unsplash.com/license) permite uso comercial e não
comercial, sem pedir permissão nem atribuição. As imagens foram baixadas,
recortadas e recomprimidas para dentro do repositório, então o app não depende
de CDN externo em produção.

| Arquivo | Origem |
| --- | --- |
| `login-arquitetura.jpg` | `unsplash.com/photos/1625390711106-3728815ebcd9` |
| `hero-painel.jpg` | `unsplash.com/photos/1546414701-81cc6963c67f` |
| `hero-obra.jpg` | `unsplash.com/photos/1522743791393-522312deeebf` |

**Fontes**: Archivo, IBM Plex Sans e IBM Plex Mono, todas sob
[SIL Open Font License 1.1](https://openfontlicense.org/), servidas pelo Google
Fonts. A OFL permite uso, modificação e redistribuição, inclusive comercial;
a única restrição prática é não vender as fontes isoladamente.

## Termos de uso e política de privacidade

O texto em `legal/textos.py` é um rascunho redigido para este projeto, com base
na LGPD (Lei 13.709/2018). **Não é parecer jurídico.** Antes de usar em
produção com clientes reais, revise com um advogado — em especial os trechos de
retenção de dados, papel de controlador/operador e foro.

A seção "Licença do software" dos termos descreve a licença **proprietária** do
`LICENSE` deste repositório. Se a licença do projeto mudar, publique uma versão
nova do documento (`legal/textos.py` + migração de dados) — mudar o texto de uma
versão já aceita descaracterizaria o registro de aceite.
