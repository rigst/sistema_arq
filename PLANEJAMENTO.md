# Planejamento — Sistema de Gestão para Escritórios de Arquitetura

> Baseado na análise integral de site (home, guias de
> gestão, comparativos, FAQ, páginas de precificação, obras, briefing e diagnóstico).
> **Escopo desta entrega: apenas o planejamento.** Nenhum código foi implementado.

## Decisões já tomadas (revisão)
- **Frontend:** Django Templates + **HTMX** + **CSS/HTML/JS puro** (sem Tailwind, sem
  Node/build). Reaproveita o design system `stolben-ui` (`stolben-ui.css`/`.js`) e as fontes
  do `sistema_orcamentos`. SSR responsivo, sem SPA.
- **Banco:** **PostgreSQL** (dev e produção).
- **Assíncrono:** **Celery + Redis** (geração de PDF, importação de extrato, recálculo de
  margem, alertas, limpeza de visitantes).
- **Sem billing.** App **gratuito**, com **login e senha** e **acesso visitante que se
  autoexclui** (mesmo padrão dos seus outros apps — ver §3.3). Todas as features são
  liberadas para todos; a tabela de planos vira só referência de escopo.
- **Convenções herdadas do `sistema_orcamentos`:** Django 6.x / Python 3.14, multiempresa
  via `Empresa`↔`auth.Group`, `Usuario(AbstractUser)` com campo `perfil`, middleware de
  empresa ativa, CSP/security headers com nonce, auditoria.

---

## 1. Visão geral do produto

Sistema de gestão multiempresa que centraliza **as sete áreas do escritório de arquitetura
e design de interiores** em um único banco, com dados conectados: o que se cadastra em um
módulo aparece nos outros, sem redigitação.

**Proposta de valor central:** a hora lançada em uma tarefa alimenta o custo do projeto → o
custo alimenta a margem → a margem aparece no financeiro. É essa cadeia (hora técnica real →
precificação → margem por projeto) que diferencia o produto de planilha/Notion/Trello.

**Jornada única do dado (fio condutor da modelagem):**

```
Briefing → Orçamento → Proposta → Contrato → Projeto → Obra → Financeiro
```

Cada etapa alimenta a seguinte automaticamente e cada registro carrega um "selo de origem"
(rastreabilidade: de onde veio, quando, gerado por qual etapa).

**Público-alvo / momentos:** profissional solo, escritório com equipe, escritório em
crescimento. A mesma estrutura escala preservando dados e histórico.

---

## 2. Mapa de features divulgadas (fonte → o que faz)

Consolidação de tudo que o site promete, para servir de checklist de cobertura.

### 2.1 Clientes e CRM
- Cadastro de contatos com histórico completo: origem do lead, o que pediu, o que foi
  conversado, fase da negociação (funil).
- Registro de interações/conversas por cliente (timeline).
- Dossiê do cliente exibindo a linha do tempo completa (todos os registros vinculados).

### 2.2 Propostas e precificação
- **Motor de hora técnica:** valor/hora a partir dos custos fixos cadastrados.
  Fórmula: `custos mensais fixos ÷ horas realmente trabalhadas no mês`
  (ex.: R$ 5.940 ÷ 440 h = R$ 13,50/h). Recalculado só quando os custos mudam.
- **Estimativa de horas por etapa** (estudo preliminar, anteprojeto, projeto legal,
  executivo) com margem de segurança de 10%.
- **Precificação final:** `(hora técnica × horas estimadas) + reserva do escritório (20%,
  para impostos/reinvestimento/imprevistos) + despesas diretas` (impressão, deslocamento,
  embalagem, taxas de transação).
- **Gerador de proposta** com identidade visual do escritório, incorporando custos,
  impostos e ambientes definidos. Sai em < 1 h, sem refazer do zero.
- Honorários / precificação por ambiente.

### 2.3 Projetos e etapas
- Templates de etapas pré-configurados (padrão NBR 13532), configuráveis por tipo
  (residencial, comercial, corporativo, interiores) e com etiquetas/tags.
- Cada projeto exibe: **etapa atual, próxima etapa prevista, data prevista, data da última
  atualização** (detecta projeto parado antes do cliente cobrar).
- **Painel de projetos** respondendo 4 perguntas lado a lado: etapa atual, pendências
  abertas (com dono e prazo), última atualização, margem financeira.
- **Painel Visual de Projetos** — board tipo kanban.
- Aprovações do cliente vinculadas a projeto+etapa (marco que impede voltar etapa fechada).

### 2.4 Tarefas e equipe
- Tarefa com **um único responsável**, prazo, critério de "pronto" e projeto vinculado.
- Identificação de tarefas sem dono.
- Alertas automáticos de prazo/pendência.
- Visão de acompanhamento para reuniões curtas periódicas.

### 2.5 Financeiro
- Contas a pagar, a receber e saldos bancários em tempo real.
- Caixa do escritório separado do pessoal (múltiplas contas).
- **Margem por projeto** calculada automaticamente ao encerrar (receita − custo de horas
  reais − despesas diretas).
- Faturamento mensal: soma de entradas × custo operacional do período.
- Identificação de tipos de projeto que repetem margem baixa.
- Lançamentos vinculados a projeto e período; categorização.
- **Exportar DRE e Resumo Financeiro.**
- **Importar extrato bancário** (OFX/CSV) com conciliação.
- Parcelas do contrato entram sozinhas no contas a receber.

### 2.6 Agenda
- Reuniões, visitas a obra e compromissos vinculados a clientes e projetos.
- Separada da agenda pessoal.

### 2.7 Contratos e documentos
- Contratos, aprovações e registros de alteração de escopo documentados por projeto.
- Briefings e contratos editáveis.
- Aditivo de escopo vira registro (não discussão).

### 2.8 Briefing (guia dedicado)
- Formulário estruturado em 5 blocos: perfil/rotina do usuário; programa de necessidades
  (ambientes, medidas aproximadas, uso); orçamento e prazo; restrições do terreno/legais
  (recuos, gabarito, taxa de ocupação); referências visuais e prioridades de estilo.
- Vinculado ao projeto e acessível durante toda a obra. Alinhado à NBR 13532.

### 2.9 Obras (guia dedicado)
- Registro de **visitas técnicas** (o que foi verificado, pendências, responsável),
  vinculadas à etapa da obra.
- Etapas de obra (fundação, estrutura, alvenaria, instalações, acabamento) com data prevista.
- **Cronograma real vs. previsto** com % de avanço e alerta de desvio (ex.: previsto 65%,
  real 55% → sinaliza 10 p.p.).
- **Medições vinculadas a etapas** liberando pagamento pelo avanço verificado (integra
  financeiro).

### 2.10 Controle de horas (timer)
- **Timer com avisos e controle de horas por projeto.**
- **Comparativo de horas projetadas vs. trabalhadas** por projeto e por tarefa — retroalimenta
  as estimativas de precificação.

### 2.11 Conformidade regulatória (guia CAU/ART/RRT)
- Controle de obrigações: registro/baixa de ART/RRT, vínculo CAU, alertas de pendência por
  projeto.

### 2.12 Diagnóstico de gestão (ferramenta de topo de funil)
- Questionário de 5 perguntas, 4 dimensões (controle de projetos, prazos, financeiro,
  tarefas), pontuação 0–2 por resposta (máx. 10), 3 faixas de maturidade
  (Inicial 0–3 / Intermediário 4–7 / Avançado 8–10). Resultado imediato, sem armazenar.

### 2.13 Onboarding / implantação guiada
- Wizard em etapas sequenciais: base administrativa → motor de precificação → controle
  financeiro → estrutura de projetos → operação diária. Cada etapa entrega uma área
  funcionando antes da próxima.
- Migração de dados de planilha (clientes, projetos ativos, histórico financeiro).

### 2.14 Multiplataforma e conta
- Responsivo (computador e celular).
- Multiusuário com credenciais individuais (login/senha) + acesso visitante autoexcluível.

### 2.15 Planos — apenas referência de escopo (NÃO haverá cobrança)
Como o app será gratuito, **todas** as features abaixo são construídas para todos os usuários.
A tabela serve só para conferir que nada do produto original ficou de fora.

| Recurso | No nosso app |
|---|---|
| 6 módulos, projetos/clientes ilimitados | ✅ para todos |
| Timer + controle de horas | ✅ |
| Briefings/contratos editáveis | ✅ |
| Painel Visual de Projetos | ✅ |
| Horas projetadas vs. trabalhadas | ✅ |
| Gerador de propostas personalizadas | ✅ |
| Exportar DRE / Resumo Financeiro | ✅ |
| Importar extrato bancário | ✅ |

---

## 3. Arquitetura técnica proposta

### 3.1 Stack (alinhada aos seus apps)
- **Backend:** Python 3.14, Django 6.x.
- **Banco:** **PostgreSQL** em dev e produção (JSONB para briefing/templates flexíveis).
- **Frontend:** Django Templates + **HTMX** + **CSS/HTML/JS puro** (sem Tailwind/Node).
  Reaproveita `stolben-ui.css`/`stolben-ui.js` e fontes (Inter/Manrope) do
  `sistema_orcamentos`. Interatividade leve com JS vanilla; HTMX para parciais/atualizações
  sem reload. SSR, responsivo.
- **Tarefas assíncronas:** **Celery + Redis** (Redis como broker e result backend). Usados
  para: geração de PDF, importação de extrato, recálculo de margem, alertas e limpeza de
  visitantes expirados (via **Celery Beat** agendado).
- **Arquivos:** `FileField` local em dev; S3-compatível em produção (`django-storages`)
  para contratos, PDFs de proposta e referências de briefing.
- **PDF:** WeasyPrint (propostas e contratos com identidade visual).
- **Auditoria/histórico:** reaproveitar o app `auditoria` e o padrão dos seus projetos.
- **Sem gateway de pagamento.** Nenhuma integração Hotmart/Stripe.

### 3.2 Multi-tenancy (reaproveitar o padrão `Empresa`↔`Group`)
Copiar a espinha dorsal do `sistema_orcamentos`, que já resolve isolamento por escritório:
- **`core.Empresa`** em `OneToOne` com `auth.Group`. Cada linha de negócio carrega
  `empresa` (FK para o Group). Helpers em `core.tenancy` (`obter_grupo_empresa_usuario`,
  `queryset_da_empresa`, `EMPRESA_ATIVA_SESSION_KEY`, etc.).
- **`EmpresaAtivaMiddleware`** injeta a empresa ativa na requisição.
- Toda view/queryset filtra por `empresa` do usuário → sem vazamento entre escritórios.

### 3.3 Autenticação e acesso visitante (reaproveitar padrão existente)
- **`usuarios.Usuario(AbstractUser)`** com `perfil` (`admin`, `arquiteto`/`equipe`,
  `visualizador`, `visitante`), `criado_em`.
- **Login/senha** (django auth). Cadastro simples de escritório (cria `Empresa`+Group).
- **Visitante autoexcluível**, espelhando `usuarios/visitantes.py`:
  - grupo/empresa dedicados com prefixo `__visitante__`;
  - **rate limit** por IP na criação (`DJANGO_VISITANTE_RATE_LIMIT` / `_WINDOW_SECONDS`);
  - **TTL** (`DJANGO_VISITANTE_TTL_HOURS`, default 24h);
  - `limpar_dados_visitante(user)` apaga todos os dados do tenant + usuário + Group/Empresa;
  - **signal de logout** limpa na saída; **task agendada no Celery Beat**
    `limpar_visitantes_expirados` limpa os que passaram do TTL.
  - Como o app tem muitos módulos, a limpeza do visitante precisa cobrir **todas** as
    entidades de negócio (clientes, projetos, propostas, tarefas, horas, financeiro,
    contratos, obras, agenda, etc.) — ver checklist em §5.15.

### 3.4 Padrões transversais
- **Selo de origem / rastreabilidade:** mixin `Rastreavel` (`origem_tipo`, `origem_id`,
  `criado_por`, timestamps) → suporta o "de onde veio" da jornada.
- **Soft delete** onde fizer sentido (clientes, projetos); visitantes usam hard delete.
- **Alertas:** app `notificacoes` agenda avisos (prazo de tarefa, projeto parado, desvio de
  obra, ART/RRT pendente).
- **CSP/security headers, concurrency, context processors, validators:** reaproveitar de `core`.

---

## 4. Estrutura de apps Django

> **Sobre "apps Django" (esclarecimento):** um *app* no Django **não** é um aplicativo
> separado nem um deploy à parte. É apenas uma **pasta/módulo Python dentro do mesmo
> projeto** que agrupa models, views, templates e migrations de um assunto. Tudo roda num
> **único** projeto/servidor. É exatamente o que o seu `sistema_orcamentos` já faz
> (`core`, `usuarios`, `clientes`, `catalogo`, `orcamentos`, `relatorios`, `auditoria` = 7
> apps). Na versão anterior eu havia fatiado demais (20). Abaixo está uma divisão
> **enxuta (~13)**, na mesma granularidade dos seus projetos. Apps podem ser fundidos à
> vontade — a divisão é só organização de código.

```
config/         # settings, urls, wsgi/asgi, agendamentos
core/           # Empresa↔Group, tenancy, mixins (Rastreavel), middleware, security  [reuso]
usuarios/       # Usuario(perfil), login, visitante + autoexclusão                    [reuso]
crm/            # Cliente, Interacao (timeline), funil/fase
precificacao/   # CustoFixo, HoraTecnica, EstimativaEtapa, TabelaPreco
propostas/      # Proposta, Ambiente, ItemProposta, gerador de PDF
projetos/       # Projeto, TemplateEtapa, Etapa, Tag, Pendencia, Aprovacao, Briefing
tarefas/        # Tarefa + ApontamentoHora/Timer (controle de horas junto)
financeiro/     # ContaBancaria, Lancamento, Contas a pagar/receber, Margem, DRE, ImportExtrato
contratos/      # Contrato, Parcela, Aditivo, AlteracaoEscopo, Documento
agenda/         # Compromisso, Visita
obras/          # Obra, EtapaObra, VisitaTecnica, Medicao
regulatorio/    # ART, RRT, RegistroCAU
diagnostico/    # questionário público (stateless)
relatorios/     # painéis agregados e exports (DRE, resumo financeiro)                [reuso]
auditoria/      # histórico/trilha                                                    [reuso]
notificacoes/   # alertas e avisos (prazo, projeto parado, desvio, ART/RRT)
```

Fusões possíveis para começar ainda mais enxuto: `briefing` já entra em `projetos`,
`horas` já entra em `tarefas`, `notificacoes` pode nascer dentro de `core`.

### 4.1 Modelo de dados — entidades centrais (resumo)
- **core.Empresa** — tenant (OneToOne com Group); identidade visual do escritório (logo,
  cores) para propostas/contratos.
- **usuarios.Usuario** — `AbstractUser` + `perfil` (inclui `visitante`).
- **crm.Cliente** — origem, fase do funil; `Interacao` (timeline).
- **precificacao.CustoFixo / HoraTecnica / EstimativaEtapa** — base do cálculo.
- **projetos.Projeto** — cliente, tipo, template, etapa atual, datas, `ultima_atualizacao`.
- **projetos.Etapa** — ordem, status, data prevista, tags, aprovação, rodadas de revisão.
- **projetos.Briefing** — 5 blocos (campos estruturados + JSONB), FK projeto.
- **propostas.Proposta** — cliente, ambientes, itens, hora técnica aplicada, valor, status,
  PDF; ao aprovar → gera Cliente(ativo)+Projeto+Contrato.
- **contratos.Contrato** — projeto, parcelas (geram contas a receber), aprovações, aditivos.
- **tarefas.Tarefa** — projeto, responsável único, prazo, critério pronto, status.
- **tarefas.ApontamentoHora** — usuário, projeto/tarefa, início/fim (timer), duração.
- **financeiro.Lancamento** — conta, tipo, categoria, projeto, data, status
  (previsto/realizado); base de contas a pagar/receber, DRE e margem.
- **financeiro.Margem** — por projeto: receita − (horas reais × hora técnica) − despesas.
- **obras.Obra / EtapaObra / VisitaTecnica / Medicao** — avanço físico e liberação de pagto.
- **agenda.Compromisso** — tipo, cliente/projeto, data, participantes.
- **regulatorio.ART/RRT** — número, status, vencimento, projeto.

Todas as entidades de negócio carregam `empresa` (FK Group) e o mixin `Rastreavel`.

---

## 5. Detalhamento de implementação por feature

### 5.1 Motor de hora técnica e precificação
`CustoFixo` (custos mensais) → serviço `calcular_hora_tecnica(empresa)` = `Σ custos ÷
horas_uteis_mes`, persistido em `HoraTecnica` com vigência; recalcula via signal.
`EstimativaEtapa` guarda horas por etapa + 10%. `precificar_projeto()` aplica
`(hora_tecnica × horas) + reserva(20%) + despesas_diretas`. Pós-execução,
`comparar_estimado_real()` refina estimativas.

### 5.2 Gerador de proposta
Template HTML com identidade da empresa → WeasyPrint gera PDF. `Proposta` monta itens a
partir de `Ambiente` + tabela de preço. "Aprovar" dispara transação que cria Cliente ativo,
Projeto (com etapas do template) e Contrato — materializando `Orçamento → Proposta →
Contrato → Projeto`.

### 5.3 Projetos, etapas e painéis
`TemplateEtapa` instanciado em `Etapa` ao criar projeto. `ultima_atualizacao` atualizada por
signal em qualquer evento filho. Painel = queryset anotado (etapa atual, nº pendências, dias
parado, margem). Painel Visual = board HTMX (drag-and-drop com Alpine).

### 5.4 Tarefas e alertas
`Tarefa` com `responsavel` obrigatório e `criterio_pronto`; destaque para "sem dono".
Task Celery Beat diária varre prazos → `notificacoes`.

### 5.5 Timer e apontamento de horas
Endpoint HTMX start/stop cria `ApontamentoHora`; timer no front (Alpine) com aviso.
Agregação por projeto → custo real (× hora técnica) → margem e comparativo estimado×real.

### 5.6 Financeiro, DRE e margem
`Lancamento` unificado (tipo/categoria/status) alimenta contas a pagar/receber e saldos.
`Margem` recalculada ao encerrar projeto. DRE = view agregada exportável (PDF/XLSX).
Importação de extrato: upload OFX/CSV → parser (`ofxparse`) → tela de conciliação com
lançamentos previstos.

### 5.7 Briefing
Wizard multi-bloco com campos estruturados + JSONB para itens variáveis (ambientes do
programa de necessidades). Upload de referências. Vinculado a projeto e proposta.

### 5.8 Contratos, aditivos e alterações de escopo
`Contrato` gera parcelas → contas a receber. `AlteracaoEscopo`/`Aditivo` versionados
(auditoria). Aprovação de etapa trava retrocesso (regra de status).

### 5.9 Obras
`EtapaObra` com % previsto/real; `VisitaTecnica` (checklist, pendências, responsável);
`Medicao` libera parcela no financeiro conforme avanço. Alerta de desvio via task Celery Beat.

### 5.10 Agenda
`Compromisso` (reunião/visita) com FK cliente/projeto; visitas de obra sincronizam com
`obras.VisitaTecnica`; feed iCal opcional.

### 5.11 Regulatório (CAU/ART/RRT)
`ART`/`RRT` por projeto com status e vencimento; alertas de pendência.

### 5.12 Diagnóstico
App público stateless: 5 perguntas, cálculo no servidor, resultado por faixa. Sem
persistência (opcional captura de e-mail).

### 5.13 Onboarding
Wizard em 5 etapas espelhando a implantação guiada; import de planilha (pandas); checklist
de progresso por empresa.

### 5.14 Acesso e visitante (sem billing)
Login/senha padrão. Botão "entrar como visitante" cria empresa temporária + usuário
`perfil=visitante`, com rate limit por IP. Autoexclusão no logout (signal) e por TTL
(command agendado). Sem planos, sem cobrança, sem gating de features.

### 5.15 Checklist de limpeza do visitante (crítico)
`limpar_dados_visitante` deve apagar, na ordem, tudo do tenant antes de remover
usuário+Group+Empresa: `crm`, `precificacao`, `propostas`, `projetos`(+Briefing),
`tarefas`(+ApontamentoHora), `financeiro`, `contratos`, `agenda`, `obras`, `regulatorio`,
`relatorios`, `auditoria`. **Cada app novo deve registrar-se nessa limpeza** (padrão de
registro/hook para não esquecer nenhuma tabela quando o sistema crescer).

---

## 6. Requisitos não-funcionais
- **Responsivo** (desktop + celular) desde o início.
- **Isolamento por empresa** em todas as queries; permissões por `perfil`.
- **LGPD:** dados de clientes; visitante com hard delete garantido (§5.15).
- **Auditoria/histórico** nas entidades financeiras e contratuais.
- **Segurança:** CSP/security headers (reuso de `core`), CSRF, rate limiting, 2FA opcional.
- **Testes:** pytest-django com cobertura no núcleo de cálculo (hora técnica, margem,
  precificação, avanço de obra) e na **limpeza do visitante**.
- **Observabilidade:** logs estruturados; Sentry opcional.
- **i18n:** pt-BR.

---

## 7. Roadmap sugerido (fases)

**Fase 0 — Fundação**
Scaffold Django 6 + PostgreSQL + **Celery/Redis (worker + Beat)**. `core`
(Empresa/tenancy/mixins/CSP) e `usuarios` (login + **visitante autoexcluível**) portados do
`sistema_orcamentos`. Layout base com HTMX + `stolben-ui` (CSS/JS puro reaproveitado),
CI, deploy.

**Fase 1 — Núcleo de valor (MVP)**
CRM · Precificação/hora técnica · Propostas (PDF) · Projetos/etapas + painel · Tarefas ·
Timer/horas · Financeiro básico (lançamentos, contas a pagar/receber, margem por projeto).
> Cobre a jornada até o financeiro e a cadeia hora→custo→margem.

**Fase 2 — Contratos, briefing e agenda**
Contratos + parcelas + aditivos · Briefing estruturado · Agenda · Aprovações/rastreabilidade.

**Fase 3 — Análise avançada**
Painel Visual (kanban) · Comparativo horas estimado×real · Propostas personalizadas ·
DRE/Resumo financeiro exportável · Importação de extrato bancário.

**Fase 4 — Obras e regulatório**
Módulo de obras (visitas, avanço, medições) · CAU/ART/RRT · notificações/alertas.

**Fase 5 — Adoção**
Onboarding guiado + migração de planilha · Diagnóstico público · refinamento de relatórios.

---

## 8. Riscos e decisões em aberto (poucas restantes)
- **Flexibilidade de templates/briefing:** híbrido campos estruturados + JSONB.
- **Importação de extrato:** variedade de formatos (OFX/CSV) exige parser robusto + tela de
  conciliação — deixado para a Fase 3.
- **"6 módulos" vs "7 áreas":** o site cita 7 áreas na home e "6 módulos" nos planos (CRM
  contado junto de propostas). A modelagem cobre as 7 áreas + extras.

## 9. Está pronto para começar? (o que falta)
**Sim — todas as decisões estão fechadas.** Resumo do que foi definido:

- Frontend: **HTMX + CSS/HTML/JS puro** (sem Tailwind), reaproveitando `stolben-ui`.
- Banco: **PostgreSQL**.
- Assíncrono: **Celery + Redis** (worker + Beat).
- Sem billing; **login/senha + visitante autoexcluível**.
- Reuso de `core` e `usuarios` do `sistema_orcamentos` (copiar/adaptar).

**Próximo passo — Fase 0:** criar o projeto Django, configurar PostgreSQL e Celery/Redis,
portar `core` (tenancy/CSP) e `usuarios` (login + visitante), montar o layout base com
`stolben-ui` + HTMX e deixar o login e o acesso visitante funcionando.
```
