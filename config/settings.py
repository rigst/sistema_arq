import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path):
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


ENV_FILE = os.getenv("DJANGO_ENV_FILE", "").strip()

if ENV_FILE:
    load_env_file(Path(ENV_FILE))
else:
    load_env_file(BASE_DIR / ".env")

ENV = os.getenv("DJANGO_ENV", "development").lower()
IS_PRODUCTION = ENV == "production"
IS_TEST = "test" in sys.argv


def env_bool(nome, default=False):
    return os.getenv(nome, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(nome, default=""):
    return [item.strip() for item in os.getenv(nome, default).split(",") if item.strip()]


DEFAULT_SECRET_KEY = "dev-only-insecure-secret-key-change-me"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", DEFAULT_SECRET_KEY)

if IS_PRODUCTION and SECRET_KEY == DEFAULT_SECRET_KEY:
    raise RuntimeError("Defina DJANGO_SECRET_KEY em produção.")

DEBUG = env_bool("DJANGO_DEBUG", default=not IS_PRODUCTION)
DEBUG_EXPOSE_MEDIA = env_bool("DJANGO_DEBUG_EXPOSE_MEDIA", default=DEBUG)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

if IS_PRODUCTION:
    if DEBUG or DEBUG_EXPOSE_MEDIA:
        raise RuntimeError("DEBUG e DJANGO_DEBUG_EXPOSE_MEDIA devem estar desativados em produção.")
    if not os.getenv("DJANGO_ALLOWED_HOSTS", "").strip() or "*" in ALLOWED_HOSTS:
        raise RuntimeError("Defina DJANGO_ALLOWED_HOSTS explicitamente e sem curinga em produção.")
    if not CSRF_TRUSTED_ORIGINS or any(
        not origem.startswith("https://") for origem in CSRF_TRUSTED_ORIGINS
    ):
        raise RuntimeError("Defina DJANGO_CSRF_TRUSTED_ORIGINS somente com origens HTTPS.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "usuarios",
    # Módulos de negócio. A ordem também define a ordem de limpeza de visitante:
    # entidades com FK PROTECT (ex.: Cliente) devem vir depois de quem as referencia.
    "precificacao",
    "projetos",
    "tarefas",
    "contratos",
    "briefing",
    "agenda",
    "obras",
    "regulatorio",
    "notificacoes",
    "propostas",
    "financeiro",
    "crm",
    # Fase 5 — adoção (públicos/sem dados de negócio persistidos).
    "diagnostico",
    # Fase 6 — cadeia de produção completa.
    "fornecedores",
    "orcamentos",
    "arquivos",
    "jornada",
    "fases",
    "modelos",
    # Termos, privacidade e registro de aceites.
    "legal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.security_headers.ContentSecurityPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.EmpresaAtivaMiddleware",
    "legal.middleware.AceiteLegalMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.empresa_context",
                "notificacoes.context_processors.notificacoes_context",
            ],
        },
    },
]

# Todo aviso mostrado no canto também vai para o histórico em Notificações.
MESSAGE_STORAGE = "notificacoes.storage.ArmazenamentoComHistorico"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Banco de dados
# Alvo do projeto: PostgreSQL (defina DATABASE_URL). Sem ele, cai em SQLite
# para desenvolvimento local rodar sem dependência externa.
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_CONN_MAX_AGE = int(os.getenv("DJANGO_DB_CONN_MAX_AGE", "60"))
DB_SSL_REQUIRE = env_bool("DJANGO_DB_SSL_REQUIRE", default=IS_PRODUCTION)

if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=DB_CONN_MAX_AGE,
            ssl_require=DB_SSL_REQUIRE,
        )
    }
else:
    if IS_PRODUCTION:
        raise RuntimeError("Defina DATABASE_URL (PostgreSQL) em produção.")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            # str e não Path: o Django aceita os dois, mas a assinatura da
            # configuração declara str.
            "NAME": str(BASE_DIR / "db.sqlite3"),
            "OPTIONS": {"timeout": int(os.getenv("SQLITE_TIMEOUT", "20"))},
        }
    }

# ---------------------------------------------------------------------------
# Cache (Redis quando configurado; LocMem em dev)
# ---------------------------------------------------------------------------
REDIS_CACHE_URL = os.getenv("DJANGO_REDIS_CACHE_URL", "").strip()

if REDIS_CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_CACHE_URL,
        }
    }
else:
    if IS_PRODUCTION:
        raise RuntimeError("Defina DJANGO_REDIS_CACHE_URL em produção.")
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sistema-arq-cache",
        }
    }

# ---------------------------------------------------------------------------
# Celery (broker/result Redis). Em dev, sem broker configurado, roda eager.
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "").strip()
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL).strip()
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", default=not bool(CELERY_BROKER_URL))
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TIMEZONE = "America/Sao_Paulo"

if IS_PRODUCTION and not CELERY_BROKER_URL:
    raise RuntimeError("Defina CELERY_BROKER_URL (Redis) em produção.")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
DATE_FORMAT = "d/m/Y"
SHORT_DATE_FORMAT = "d/m/Y"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "usuarios.Usuario"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
HEALTHZ_TOKEN = os.getenv("DJANGO_HEALTHZ_TOKEN", "").strip()
TRUST_X_FORWARDED_FOR = env_bool("DJANGO_TRUST_X_FORWARDED_FOR", default=False)

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = Path(os.getenv("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles")))

USE_MANIFEST_STATICFILES = env_bool("DJANGO_USE_MANIFEST_STATICFILES", default=IS_PRODUCTION)
if USE_MANIFEST_STATICFILES:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
    }

MEDIA_URL = "/media/"
MEDIA_ROOT = os.getenv("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media"))
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE", 30 * 1024 * 1024))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE", 5 * 1024 * 1024))
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(os.getenv("DJANGO_DATA_UPLOAD_MAX_NUMBER_FIELDS", "2000"))

# Visitante autoexcluível (mesmos knobs do padrão herdado)
DJANGO_VISITANTE_TTL_HOURS = int(os.getenv("DJANGO_VISITANTE_TTL_HOURS", "24"))

SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", default=IS_PRODUCTION)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", default=IS_PRODUCTION)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = int(os.getenv("DJANGO_SESSION_COOKIE_AGE", "28800"))
SESSION_EXPIRE_AT_BROWSER_CLOSE = env_bool("DJANGO_SESSION_EXPIRE_AT_BROWSER_CLOSE", True)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = os.getenv("DJANGO_SECURE_REFERRER_POLICY", "same-origin")
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("DJANGO_EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = int(os.getenv("DJANGO_EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "Sistema Arq <noreply@localhost>")

if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise RuntimeError("DJANGO_EMAIL_USE_TLS e DJANGO_EMAIL_USE_SSL não podem estar ativos juntos.")

if env_bool("DJANGO_USE_X_FORWARDED_PROTO", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ENABLE_CSP = env_bool("DJANGO_ENABLE_CSP", default=IS_PRODUCTION)
CONTENT_SECURITY_POLICY = os.getenv(
    "DJANGO_CONTENT_SECURITY_POLICY",
    "default-src 'self'; img-src 'self' data: blob:; script-src 'self' 'nonce-{nonce}'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' data: https://fonts.gstatic.com; object-src 'none'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
)

if IS_PRODUCTION:
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"

if IS_TEST:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}
