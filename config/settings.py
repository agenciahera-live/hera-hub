"""Configurações do Hera Creator Hub.

Tudo que muda entre ambientes vem de variáveis de ambiente (ver .env.example).
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


SECRET_KEY = env("SECRET_KEY", "dev-insecure-change-me")
DEBUG = env("DEBUG", "1") == "1"
# Produção = DEBUG=0 nas variáveis do servidor. Os comandos de demonstração (seed_demo, demo_semana) leem esta marca
# para se recusarem a criar logins com senha conhecida. (Nos testes o Django desliga o DEBUG, por isso a marca é separada.)
IS_PRODUCTION = not DEBUG
if not DEBUG and SECRET_KEY == "dev-insecure-change-me":
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("Em produção, cadastre a variável SECRET_KEY (ver .env.example).")
ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h.strip()]
ALLOWED_HOSTS.append("healthcheck.railway.app")  # verificação de saúde do Railway
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "allauth",
    "allauth.account",
    "core",
    "crm",
    "data",
    "engage",
    "web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.RLSContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "core.middleware.ConsentMiddleware",
    "core.middleware.AuditMiddleware",
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
                "core.context.hera_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# O app DEVE conectar com um usuário de banco sem superusuário e sem BYPASSRLS.
# Veja docs/COMO_RODAR_E_PUBLICAR.md (parte B, "usuário do banco").
DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", "postgres://hera_app:hera@localhost:5432/hera"),
        conn_max_age=0,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage" if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Login (allauth): e-mail e senha, sessão persistente ----
# O criador cria a senha em /primeiro-acesso/ com o código que a gestão envia no grupo (crm/first_access.py).
# O e-mail é informado pelo próprio criador e não é conferido. Por isso ele NUNCA recupera acesso: não existe
# código por e-mail, "esqueci a senha" por e-mail (bloqueado em config/urls.py) nem login com Google.
SITE_ID = 1
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1"]  # cadastro público desligado (ver ACCOUNT_ADAPTER)
ACCOUNT_USER_MODEL_USERNAME_FIELD = "username"
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_ALLOW_REGISTRATION = False  # só entra quem recebeu o código de acesso
ACCOUNT_ADAPTER = "core.adapters.InviteOnlyAccountAdapter"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 90  # 90 dias
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/entrar/"
LOGIN_URL = "/entrar/"

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Hera Creator Hub <nao-responda@hera.local>")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}

# Versão do termo LGPD exibido no primeiro acesso
CONSENT_VERSION = "2026-09"

if DEBUG:
    ACCOUNT_RATE_LIMITS = False  # em produção ficam os limites padrão contra tentativa de senha
