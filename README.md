# Sistema ARQ

Sistema de gestão para escritórios de arquitetura e design de interiores (réplica funcional
do COP). Django + HTMX + CSS/HTML/JS puro (design system `stolben-ui`), PostgreSQL e
Celery/Redis. Ver o planejamento completo em [`PLANEJAMENTO.md`](PLANEJAMENTO.md).

## Estado atual: Fase 0 (fundação)

- Projeto Django (`config`) com PostgreSQL (fallback SQLite em dev) e Celery/Redis
  (fallback eager em dev).
- App `core`: tenant `Empresa`↔`auth.Group`, `tenancy`, middleware de empresa ativa,
  CSP/security headers, mixin `Rastreavel` e registro central de limpeza de visitante.
- App `usuarios`: `Usuario` com `perfil`, login/senha e **acesso visitante autoexcluível**
  (rate limit, TTL, limpeza no logout via signal e via task do Celery Beat).
- Layout base (topbar, login, painel) responsivo.

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
