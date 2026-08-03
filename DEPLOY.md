# Primeiro deploy

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
