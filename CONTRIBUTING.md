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
pip install ruff mypy bandit pip-audit pytest pytest-django pytest-cov
APPS="agenda arquivos briefing config contratos core crm fases financeiro"

ruff check .                              # bloqueia
ruff format --check .                     # bloqueia
pytest --cov --cov-fail-under=80          # bloqueia
bandit -r $APPS --severity-level high     # bloqueia a partir de "high"
pip-audit                                 # bloqueia
python manage.py makemigrations --check --dry-run   # bloqueia
python manage.py check --deploy --fail-level ERROR
mypy $APPS                                # bloqueia
```

**Nada está em `soft-fail`: toda etapa bloqueia.** O `mypy` foi o último a sair
da lista, depois que os 64 erros restantes foram zerados.

O Quality Gate do SonarQube Cloud também bloqueia: o CI passa
`-Dsonar.qualitygate.wait=true`, então o job espera o veredito em vez de
terminar verde só por ter enviado a análise. Sem isso o build ficava verde com
o gate vermelho — que foi exatamente o que aconteceu enquanto a cobertura de
código novo e a nota de segurança estavam abaixo do exigido.

### Dependências e o lock

`requirements.txt` é a lista que se edita à mão, com as diretas fixadas em
`==`. `requirements.lock` é gerado a partir dela e fixa também as transitivas,
com o sha256 de cada artefato — é dele que o Dockerfile instala, com
`--require-hashes`, para dois builds do mesmo commit produzirem a mesma imagem.

Ao mexer em `requirements.txt`, regenere:

```bash
python scripts/gerar_lock.py
```

O CI tem dois jobs para isso. O `lock com hashes` vem do pipeline
compartilhado (`run-lock`) e faz duas checagens: que os dois arquivos não
divergiram — existe porque o Dependabot atualiza o `requirements.txt` e **não**
reconhece o `requirements.lock`, então sem ela o CI testaria uma versão e a
imagem instalaria outra — e que o lock instala de verdade sob
`--require-hashes`, o que pega transitiva faltando e hash errado. Ele roda no
Python informado em `lock-python-version` (3.14, o da imagem), e não no do
resto do pipeline: conferir na versão errada acusaria divergência inexistente.

O `imagem docker` constrói a imagem de fato, que é a prova final.

O verificador em si vive em
[`rigst/ci`](https://github.com/rigst/ci/blob/v1/scripts/conferir_lock.py), com
testes próprios. A cópia que existia aqui em `scripts/conferir_lock.py` foi
removida: duas implementações da mesma regra divergem, e a divergência
apareceria como build verde com lock errado. O `scripts/gerar_lock.py`
continua sendo local, porque carrega os parâmetros de resolução deste projeto
(Python 3.14 e o `ofxparse`, que só publica sdist).

O `check --deploy` roda com `--fail-level ERROR`, e não `WARNING`, porque os
avisos de HSTS (`security.W005` e `security.W021`) são escolha deliberada
documentada em `.env.production.example`. Forjar variáveis só para calar o aviso
produziria um verde falso.

O `bandit` imprime o relatório inteiro, mas só reprova a partir de severidade
**alta**.

Os testes rodam com `pytest` (configuração em `pytest.ini`), **em PostgreSQL no
CI**, igual à produção. A convenção de nomes aqui é `tests.py` e `tests_*.py`,
não `test_*.py`.

```bash
pytest                    # suíte completa (269 testes)
pytest contratos          # só um app
pytest --cov              # com cobertura
```

Cobertura acompanhada no [Codecov](https://codecov.io/gh/rigst/sistema_arq) e no
[SonarQube Cloud](https://sonarcloud.io/summary/new_code?id=rigst_sistema_arq).
O CI reprova abaixo de **80%** (`coverage-fail-under`); hoje a suíte fica em
~83%. O piso existe para impedir queda — suba-o junto com a cobertura real, não
o contrário.

### Uma armadilha ao escrever testes

Não chame `response.close()` dentro de uma `TestCase`. Isso dispara o signal
`request_finished`, que fecha a conexão do banco dentro do `atomic` do teste —
e todo teste seguinte da mesma classe morre com `the connection is closed`. Em
SQLite o sintoma não aparece, então passa despercebido até rodar no PostgreSQL.
Para consumir um `FileResponse`, itere `response.streaming_content`. Isso já
custou 8 falhas nesta suíte.

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
