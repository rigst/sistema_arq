FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 libgdk-pixbuf-2.0-0 libjpeg62-turbo libpango-1.0-0 \
    libpangocairo-1.0-0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# O lock, e não o requirements.txt: ele fixa também as transitivas e traz o
# sha256 de cada artefato. Sem isso, dois builds do mesmo commit podiam
# instalar conteúdos diferentes. Regenerar com scripts/gerar_lock.py.
COPY requirements.lock ./
# --require-hashes recusa qualquer pacote fora da lista. --only-binary recusa
# sdist, cujo setup.py roda código arbitrário durante o build; ofxparse é a
# única exceção, porque a 0.21 só é publicada como sdist.
#
# O próprio pip agora está no lock, com pin e hash, então esta linha o atualiza
# junto com o resto. Isso NÃO é o mesmo que `pip install --upgrade pip`, que a
# versão anterior deste comentário evitava com razão: aquilo instalaria versão
# não fixada. Aqui a versão é fixa e o hash é conferido, igual a todo o resto —
# é a mesma preocupação, atendida em vez de contornada.
RUN pip install --require-hashes --only-binary :all: --no-binary ofxparse \
    -r requirements.lock

# Cópia explícita em vez de `COPY . .`: o conteúdo da imagem vira uma lista
# revisável. Na cópia recursiva, qualquer arquivo novo na raiz do repositório
# — dump de banco, .env de rascunho, chave privada — embarca junto sem ninguém
# notar, porque o .dockerignore só barra o que alguém lembrou de listar.
# App novo no INSTALLED_APPS pede uma linha nova aqui; a falta dela aparece no
# start, como ModuleNotFoundError.
COPY manage.py ./
COPY config/ config/
COPY deploy/ deploy/
COPY static/ static/
COPY templates/ templates/
COPY agenda/ agenda/
COPY arquivos/ arquivos/
COPY briefing/ briefing/
COPY contratos/ contratos/
COPY core/ core/
COPY crm/ crm/
COPY diagnostico/ diagnostico/
COPY fases/ fases/
COPY financeiro/ financeiro/
COPY fornecedores/ fornecedores/
COPY jornada/ jornada/
COPY legal/ legal/
COPY modelos/ modelos/
COPY notificacoes/ notificacoes/
COPY obras/ obras/
COPY orcamentos/ orcamentos/
COPY precificacao/ precificacao/
COPY projetos/ projetos/
COPY propostas/ propostas/
COPY regulatorio/ regulatorio/
COPY tarefas/ tarefas/
COPY usuarios/ usuarios/

RUN addgroup --system arq && adduser --system --ingroup arq arq \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R arq:arq /app

USER arq
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--config", "deploy/gunicorn.conf.py"]
