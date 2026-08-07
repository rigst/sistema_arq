# Contribuindo

Obrigado pelo interesse. Este é um projeto mantido por uma pessoa só, então
issues e PRs podem levar alguns dias para receber resposta.

## Antes de abrir um PR

O A.R.Q. está em release candidate da primeira implantação em produção. Abra uma
issue antes de qualquer mudança em modelo de dados, no isolamento por empresa ou
no fluxo comercial (briefing → proposta → contrato → fases). Correção de bug,
texto e documentação podem ir direto para o PR.

## Ambiente

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

PostgreSQL e Redis são obrigatórios em produção; em desenvolvimento há fallback
para SQLite. O Compose de produção está em `docker-compose.production.yml`, e o
procedimento completo em [DEPLOY.md](DEPLOY.md).

## O que o CI exige

O pipeline é o compartilhado de [rigst/ci](https://github.com/rigst/ci). Para
rodar as mesmas checagens localmente antes de subir:

```bash
pip install ruff mypy bandit pip-audit
ruff check .                              # precisa passar
ruff format --check .                     # precisa passar
python manage.py makemigrations --check --dry-run
python manage.py check --deploy --fail-level WARNING
bandit -r agenda arquivos briefing config contratos core crm fases financeiro
pip-audit
```

`mypy` e `pytest` estão em `soft-fail`: rodam e reportam, mas não derrubam o
build ainda.

## Cuidados específicos deste projeto

- **Isolamento por empresa**: toda query que toca dado de negócio precisa ser
  filtrada pela empresa do usuário. PR que introduza acesso sem esse filtro não
  é aceito, mesmo que os testes passem.
- **Textos legais** (contratos, termos, ART/RRT) são revisados juridicamente;
  não altere o conteúdo sem sinalizar na issue.
- Não commite `.env`, dump de banco, documento de cliente nem credencial. O CI
  roda `gitleaks` sobre todo o histórico e reprova o PR se encontrar segredo.

## Estilo

- `ruff` decide formatação e lint — rode a ferramenta em vez de discutir estilo.
- Mensagens de commit e comentários em português.

## Licença das contribuições

Ao enviar um PR você concorda em licenciar sua contribuição sob a
[AGPL-3.0](LICENSE), a mesma do projeto.
