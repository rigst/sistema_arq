# Primeiro deploy

> **Dois caminhos.** Este guia cobre a implantação de referência em Docker
> Compose, indicada para quem for adotar o projeto. A instância mantida pelo
> autor **não usa Docker**: roda systemd + Gunicorn com virtualenv em
> `/var/www/sistema_arq/current`. O deploy de rotina dessa instalação está na
> seção [Atualização em instalação systemd](#atualização-em-instalação-systemd)
> e, em forma genérica, no
> [runbook do CI compartilhado](https://github.com/rigst/ci/blob/main/RUNBOOK.md).

Este guia descreve a implantação de host único incluída em
docker-compose.production.yml. O proxy/TLS público pode ser fornecido pela
plataforma ou por um proxy externo apontando para a porta 8080.
O bind mount do Nginx usa relabel privado (`Z`) para funcionar também em hosts
com SELinux habilitado.

## Pré-requisitos

- Docker Engine com o plugin Compose v2;
- domínio e certificado TLS válidos;
- volume persistente e backup para PostgreSQL e arquivos;
- SMTP transacional, caso haja envio de e-mail, e monitoramento definidos pela infraestrutura;
- inventário dos operadores/suboperadores de dados.

## Configuração

    cp .env.production.example .env.production
    python -c "import secrets; print(secrets.token_urlsafe(64))"

Preencha uma chave secreta nova, domínio, origem CSRF e senhas. No Compose
local, DJANGO_DB_SSL_REQUIRE=false é adequado porque o banco fica na rede
privada. Para PostgreSQL gerenciado, use TLS e a URL fornecida pelo provedor.
Os parâmetros SMTP já são aceitos pelo app. Nesta versão, os comandos "Enviar
ao cliente" apenas registram o andamento interno; o envio externo ainda deve
ser feito pelo escritório.

## Subida

    docker compose --env-file .env.production -f docker-compose.production.yml build --pull
    docker compose --env-file .env.production -f docker-compose.production.yml run --rm web python manage.py check --deploy
    docker compose --env-file .env.production -f docker-compose.production.yml up -d
    docker compose --env-file .env.production -f docker-compose.production.yml exec web python manage.py createsuperuser
    curl -fsS https://arq.exemplo.com/healthz/

O web aplica migrações e coleta estáticos antes de iniciar o Gunicorn. worker
executa tarefas assíncronas e beat agenda limpeza de visitantes e alertas. O
Nginx não publica /media/; os documentos passam por autorização no Django.

## Checklist de abertura

- login, logout, aceite legal e /admin/ verificados;
- jornada completa criada com dados de teste e removida depois;
- proposta e contrato em PDF revisados;
- upload e download testados entre dois escritórios distintos;
- SMTP testado, quando utilizado, e redefinição operacional de conta via admin verificada;
- logs, uptime e alertas de erro ativos;
- backup automático e restauração ensaiada;
- imagens estáticas com licença comprovada;
- Termos v1.2 e Política v1.2 revisados por profissional jurídico.

## Backup

Banco e arquivos formam uma unidade. Capture os dois no mesmo ciclo:

    docker compose --env-file .env.production -f docker-compose.production.yml exec -T db pg_dump -Fc -U sistema_arq sistema_arq > backup.dump
    docker run --rm -v sistema_arq_media_data:/data -v "$PWD":/backup alpine tar -czf /backup/media.tar.gz -C /data .

Guarde cópias criptografadas fora do host e teste periodicamente a restauração.

## Atualização e rollback

Antes de atualizar, gere backup. Depois:

    git pull --ff-only
    docker compose --env-file .env.production -f docker-compose.production.yml build --pull
    docker compose --env-file .env.production -f docker-compose.production.yml up -d

Para rollback, volte à imagem/tag anterior. Não reverta migrações sem confirmar
que são reversíveis; quando houver mudança destrutiva, restaure banco e mídia do
mesmo ponto. O rollback deve ser testado em staging antes da primeira release.

## Atualização em instalação systemd

Caminho usado pela instância do autor. Layout: código em
`/var/www/sistema_arq/current`, virtualenv em `/var/www/sistema_arq/venv`,
ambiente em `/var/www/sistema_arq/shared/.env`.

**Desde que o CD (`.github/workflows/deploy.yml`) foi ligado, os passos
abaixo acontecem sozinhos a cada PR mesclado em `main` que passar no CI** — via
`deploy/cd-deploy.sh`, disparado por SSH pelo workflow reutilizável
`deploy-django.yml` do `rigst/ci` (RUNBOOK.md seção 7). A branch `main` tem
proteção ativa (checks obrigatórios, sem push direto nem pra admin); mudanças
sempre entram por PR, sem exigir aprovação de terceiros. O procedimento manual
continua valendo para rollback e para depurar um deploy que falhou.

Antes de puxar, verifique o que vem no lote e anote o ponto de rollback:

    D=/var/www/sistema_arq/current
    git -C $D fetch origin
    git -C $D rev-parse --short HEAD                                    # rollback
    git -C $D diff --name-only HEAD..origin/main -- '*/migrations/*'    # vazio = sem migração
    git -C $D diff --name-only HEAD..origin/main -- requirements.txt    # vazio = sem pip install

Havendo migração, gere backup do banco antes (seção anterior). Depois:

    git -C $D pull --ff-only origin main
    cd $D
    set -a && . /var/www/sistema_arq/shared/.env && set +a
    /var/www/sistema_arq/venv/bin/python manage.py check --deploy --fail-level ERROR
    /var/www/sistema_arq/venv/bin/python manage.py migrate --check

O `--fail-level ERROR` é intencional: `security.W005` e `security.W021` (HSTS)
são escolha documentada em `.env.production.example`, e forjar variável só para
calar o aviso produziria um verde falso. O `migrate --check` sai diferente de
zero se houver migração não aplicada.

Se `static/` mudou, rode `collectstatic --noinput`. Por fim:

    sudo systemctl restart sistema_arq.service sistema_arq_celery.service sistema_arq_celerybeat.service
    systemctl is-active sistema_arq.service
    curl -s -o /dev/null -w "%{http_code}\n" https://arq.stolben.com

Rollback sem migração no meio é voltar o código e reiniciar:

    git -C $D reset --hard SHA_ANOTADO
    sudo systemctl restart sistema_arq.service sistema_arq_celery.service sistema_arq_celerybeat.service
