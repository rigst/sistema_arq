# Licenças de terceiros

O código original do A.R.Q. é proprietário conforme [LICENSE](LICENSE). Este
arquivo registra componentes de terceiros usados pela release atual; não
substitui os textos oficiais de cada projeto.

## Dependências diretas

| Componente | Versão | Licença declarada |
|---|---:|---|
| Django | 6.0.7 | BSD-3-Clause |
| asgiref | 3.11.1 | BSD-3-Clause |
| dj-database-url | 3.0.1 | BSD |
| psycopg / psycopg-binary | 3.2.12 | LGPL-3.0-only |
| Pillow | 12.3.0 | MIT-CMU |
| Celery | 5.4.0 | BSD-3-Clause |
| redis-py | 5.2.1 | MIT |
| Gunicorn | 23.0.0 | MIT |
| sqlparse | 0.5.5 | BSD-3-Clause |
| WeasyPrint | 69.0 | BSD-3-Clause |
| ofxparse | 0.21 | MIT |

As dependências transitivas são instaladas pelo pip a partir de
requirements.txt. A imagem de produção deve preservar os metadados e textos de
licença instalados nos pacotes. psycopg-binary é redistribuído na imagem sob
LGPL; alterações no próprio componente continuam sujeitas a essa licença.

## Front-end e fontes

| Item | Licença |
|---|---|
| HTMX 2.x (static/js/htmx.min.js) | Zero-Clause BSD |
| CSS, JavaScript, ícones e marca próprios | Proprietária |
| Archivo, IBM Plex Sans e IBM Plex Mono | SIL Open Font License 1.1 |

As fontes são solicitadas ao Google Fonts na configuração atual. Isso deve ser
considerado na política de privacidade e na escolha dos fornecedores da
implantação. Para evitar a requisição externa, hospede as fontes localmente
antes do lançamento.

## Imagens

Os JPGs em static/img/ foram incorporados durante o desenvolvimento. Antes de
uso comercial, o responsável pelo deploy deve manter no inventário privado a
origem e a prova de licença de cada imagem:

- fundo-vidro.jpg
- hero-comercial.jpg
- hero-gestao.jpg
- hero-obra.jpg
- hero-painel.jpg
- hero-producao.jpg
- login-arquitetura.jpg

Não há metadados suficientes no repositório para afirmar a licença ou autoria
dessas imagens. Essa validação é um bloqueio operacional para publicação
comercial, não um problema que possa ser resolvido apenas pelo código.

## Auditoria

Na atualização desta release, as licenças declaradas foram conferidas nos
metadados dos pacotes instalados. Refaça a conferência sempre que
requirements.txt mudar.
