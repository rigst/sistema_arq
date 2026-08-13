# A.R.Q.

[![CI](https://github.com/rigst/sistema_arq/actions/workflows/ci.yml/badge.svg)](https://github.com/rigst/sistema_arq/actions/workflows/ci.yml)
[![Cobertura](https://codecov.io/gh/rigst/sistema_arq/branch/main/graph/badge.svg)](https://codecov.io/gh/rigst/sistema_arq)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=rigst_sistema_arq&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=rigst_sistema_arq)
[![Licença: AGPL v3](https://img.shields.io/badge/licen%C3%A7a-AGPL--3.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Django 6](https://img.shields.io/badge/django-6.0-092E20.svg)](https://www.djangoproject.com/)

Sistema web de gestão para escritórios de arquitetura e interiores. A jornada
principal conecta briefing, proposta, aprovação comercial, contrato, fases de
projeto, tarefas, arquivos, agenda e financeiro sem duplicar o projeto.

Estado atual: **release candidate da primeira implantação em produção**.

## Fluxo principal

1. Cadastro do cliente e abertura do projeto.
2. Briefing estruturado a partir de modelos reutilizáveis.
3. Proposta com itens, horas, datas de entrega, hora técnica e fatores por projeto.
4. Aprovação da proposta, que libera e abre a minuta do contrato.
5. Contrato com modelo, texto, parcelas, alterações contratuais e documentos na mesma tela.
6. Fases técnicas com tarefas, horas, prazo, arquivos e aprovação do cliente.
7. Integração das tarefas com calendário e dos recebimentos com o financeiro.

O sistema também inclui fornecedores, orçamento, obras, ART/RRT, notificações,
modelos padrão, identidade do escritório, importação OFX/CSV e PDFs.

## Tecnologia

- Python 3.12 a 3.14 e Django 6.0.
- HTML, CSS e JavaScript próprios, com HTMX vendorizado.
- PostgreSQL em produção; SQLite como fallback local.
- Redis e Celery para cache, limpeza de visitantes e alertas periódicos.
- Gunicorn e Nginx no Compose de produção.
- WeasyPrint para proposta e contrato em PDF.

## Desenvolvimento

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver

Sem .env, o app usa SQLite, cache em memória e tarefas Celery eager. Para
configurar PostgreSQL/Redis localmente, use [.env.example](.env.example).

O admin global fica em /admin/ e aceita somente superusuários. Essa restrição
é intencional: as telas do produto isolam os dados por escritório; o admin
global enxerga todos os escritórios.

## Verificação

    python manage.py check
    pytest                              # 269 testes
    python manage.py makemigrations --check
    pip-audit

Os testes cobrem isolamento entre empresas, fluxo briefing → proposta →
contrato, operações inline, financeiro, arquivos protegidos e autenticação.
No CI rodam em PostgreSQL, igual à produção.

## Produção

O primeiro deploy e o rollback estão descritos em [DEPLOY.md](DEPLOY.md).
Use [.env.production.example](.env.production.example) como inventário de
variáveis, sem reutilizar os valores de exemplo.

Antes de abrir o acesso:

- revisar domínio, TLS, DNS, SMTP, backup e monitoramento;
- criar o primeiro superusuário;
- validar check --deploy, migrações e restore de backup;
- revisar os textos legais com assessoria jurídica e preencher a lista real de
  fornecedores de infraestrutura.

## Qualidade

O CI é o pipeline compartilhado de [rigst/ci](https://github.com/rigst/ci) e
precisa passar antes do merge. Todo push roda, em paralelo:

| Etapa | Ferramenta | Estado |
|---|---|---|
| Lint e formatação | `ruff` | bloqueia |
| Testes e cobertura | `pytest` em PostgreSQL | bloqueia |
| Segurança do código | `bandit` | bloqueia a partir de severidade alta |
| Dependências | `pip-audit` | bloqueia |
| Segredos | `gitleaks` (histórico completo) | bloqueia |
| Django | `check --deploy` + `makemigrations --check` | bloqueia |
| Tipos | `mypy` | bloqueia |
| Agregação | SonarQube Cloud (Quality Gate) | bloqueia |

Cobertura no [Codecov](https://codecov.io/gh/rigst/sistema_arq); bugs, code
smells e duplicação no
[SonarQube Cloud](https://sonarcloud.io/summary/new_code?id=rigst_sistema_arq).

A proteção de branch deve exigir um único check, `CI` — ele consolida todos os
outros.

## Contribuindo

Veja [CONTRIBUTING.md](CONTRIBUTING.md).

## Segurança

Política de reporte e controles: [SECURITY.md](SECURITY.md). Não abra issue
pública para vulnerabilidade.

## Licença

[**AGPL-3.0**](LICENSE) — Copyright (C) 2026 Rodrigo Caballero Stölben.

Você pode usar, estudar, modificar e redistribuir. A cláusula que caracteriza a
AGPL: se você rodar uma versão modificada como serviço acessível pela rede, os
usuários desse serviço têm direito ao código-fonte correspondente. Para um
sistema de gestão que normalmente é oferecido como SaaS, é essa cláusula que
mantém as melhorias públicas.

Dependências e ativos de terceiros seguem suas próprias licenças, inventariadas
em [LICENCAS.md](LICENCAS.md).
