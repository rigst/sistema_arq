# A.R.Q.

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
    python manage.py test
    python manage.py makemigrations --check
    pip-audit -r requirements.txt

Os testes cobrem isolamento entre empresas, fluxo briefing → proposta →
contrato, operações inline, financeiro, arquivos protegidos e autenticação.

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

## Segurança e licença

Política de reporte e controles: [SECURITY.md](SECURITY.md).

Software proprietário, copyright Rodrigo Stölben. Consulte [LICENSE](LICENSE)
e [LICENCAS.md](LICENCAS.md) para dependências e ativos de terceiros.
