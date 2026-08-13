FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 libgdk-pixbuf-2.0-0 libjpeg62-turbo libpango-1.0-0 \
    libpangocairo-1.0-0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
# --only-binary recusa sdist, cujo setup.py roda código arbitrário do pacote
# durante o build. ofxparse é a única exceção: a 0.21 é publicada só como
# sdist. O pip da imagem base fica como veio — `pip install --upgrade pip`
# instala uma versão não fixada, que é justamente o que o resto desta linha
# evita.
RUN pip install --only-binary :all: --no-binary ofxparse -r requirements.txt

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
