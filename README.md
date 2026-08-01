# A.R.Q.

Sistema de gestão para escritórios de arquitetura e design de interiores.
Django + HTMX + CSS/HTML/JS puro (design system `stolben-ui`), PostgreSQL e
Celery/Redis. Ver o planejamento completo em [`PLANEJAMENTO.md`](PLANEJAMENTO.md).

Software proprietário — ver [`LICENSE`](LICENSE). As dependências mantêm suas
próprias licenças (ver [`LICENCAS.md`](LICENCAS.md)).

**Identidade visual — "Prancheta técnica":** o app veste o design system Stölben com
o vocabulário da prancheta de arquitetura — papel frio + tinta grafite, acento em
verde de tinta técnica, títulos em Space Grotesk e **números em monoespaçada**
(cada percentual, valor e registro lido como numa folha de especificação), com
linhas de cota sob os títulos de cartão.

## Estado atual: Fase 5 concluída (adoção)

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

**Precificação — hora técnica escolhível:** o custo da hora (custos÷horas úteis) é o piso
usado na margem; a hora-base cobrada pode ser manual; e cada proposta ajusta sua hora técnica
por **fatores de projeto** (urgência, complexidade, etc.) ou por valor livre.

**Módulos de negócio (Fase 2):**
- `contratos` — contrato por projeto, **parcelas que viram contas a receber** no financeiro
  (marcar paga → lançamento realizado), aditivos/alterações de escopo (registro) e documentos.
- `briefing` — formulário de 5 blocos + programa de necessidades, vinculado ao projeto.
- `agenda` — reuniões, visitas e prazos ligados a cliente/projeto.

A cadeia de valor está fechada: hora lançada → custo do projeto → margem no financeiro;
e proposta → contrato → parcelas → financeiro.

**Análise avançada (Fase 3):**
- **Painel visual (kanban)** de projetos com arrastar-e-soltar (HTMX/JS, muda o status).
- **Horas projetadas × trabalhadas** por projeto (estimativa vinda da proposta).
- **PDF** de proposta e contrato (WeasyPrint).
- **DRE** do mês por categoria + **exportação CSV**.
- **Importar extrato** bancário (OFX/CSV) com conciliação automática por valor.

**Obras e conformidade (Fase 4):**
- `obras` — abertura da obra com etapas construtivas padrão; **cronograma real × previsto**
  com alerta de desvio (ponderado pelo valor das etapas); **visitas técnicas** (verificado,
  pendências, próxima ação) ligadas à etapa; **medições que, ao aprovar, viram lançamento
  (entrada) no financeiro** do projeto.
- `regulatorio` — **ART/RRT e vínculo CAU** por projeto, com status, vencimento e alerta de
  pendência/vencimento.
- `notificacoes` — motor de alertas (task Celery Beat + comando `varrer_alertas`): prazo de
  tarefa, projeto parado, desvio de obra e obrigação vencida/pendente, com **sino e contador**
  na barra superior e deduplicação por chave.

**Adoção (Fase 5):**
- `diagnostico` — ferramenta pública (sem login, sem persistência): 5 perguntas × 4 dimensões,
  pontuação 0–10 e faixa de maturidade (Inicial / Intermediário / Avançado).
- `onboarding` — **implantação guiada em 5 etapas** cujo progresso é derivado dos dados reais
  do escritório (cliente → custos → conta → projeto → tarefa).

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

## Tarefas de manutenção (sem Celery)

```bash
python manage.py limpar_visitantes_expirados   # remove visitantes além do TTL
python manage.py varrer_alertas                # gera notificações de prazo/desvio/obrigação
```
