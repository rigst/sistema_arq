# Sistema ARQ

Sistema de gestão para escritórios de arquitetura e design de interiores.
Django + HTMX + CSS/HTML/JS puro (design system `stolben-ui`), PostgreSQL e
Celery/Redis. Ver o planejamento completo em [`PLANEJAMENTO.md`](PLANEJAMENTO.md).

## Estado atual: Fase 1 concluída (núcleo de valor)

**Fundação (Fase 0):**
- Projeto Django (`config`) com PostgreSQL (fallback SQLite em dev) e Celery/Redis
  (fallback eager em dev).
- App `core`: tenant `Empresa`↔`auth.Group`, `tenancy`, middleware de empresa ativa,
  CSP/security headers, mixins `EmpresaModel`/`Rastreavel` e registro central de limpeza
  de visitante (`core.visitante_cleanup`).
- App `usuarios`: `Usuario` com `perfil`, login/senha e **acesso visitante autoexcluível**
  (rate limit, TTL, limpeza no logout via signal e via task do Celery Beat).

**Módulos de negócio (Fase 1):**
- `crm` — clientes, funil e timeline de interações.
- `precificacao` — custos fixos → **hora técnica**; serviço de precificação de etapa.
- `propostas` — proposta com itens precificados; **aprovar gera o projeto** (com etapas).
- `projetos` — painel (etapa, pendências, tempo parado, margem), etapas e pendências.
- `tarefas` — tarefas com dono/prazo/critério + **timer** de horas por projeto.
- `financeiro` — contas, lançamentos, saldos, resumo mensal e **margem por projeto**.

A cadeia de valor está fechada: hora lançada → custo do projeto → margem no financeiro.

## Rodar em desenvolvimento

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser        # opcional
python manage.py runserver
```

Sem `.env`, roda em SQLite e Celery eager — não precisa de PostgreSQL/Redis para testar.
Para usar PostgreSQL e Redis, copie `.env.example` para `.env` e preencha `DATABASE_URL`
e `CELERY_BROKER_URL`.

## Celery (quando usar Redis)

```bash
celery -A config worker -l info
celery -A config beat -l info      # agenda a limpeza de visitantes expirados
```

## Limpeza de visitantes (sem Celery)

```bash
python manage.py limpar_visitantes_expirados
```
