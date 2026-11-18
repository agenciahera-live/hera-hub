from django.conf import settings
from django.core.checks import Error, Tags, register
from django.db import connection


@register(Tags.database, deploy=True)
def rls_role_check(app_configs, **kwargs):
    """Em produção, o usuário do banco não pode ignorar o RLS."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            sup, byp = cur.fetchone()
    except Exception:
        return []
    if sup or byp:
        return [Error(
            "O app está conectado ao banco com um usuário que IGNORA as regras de segurança (superusuário/BYPASSRLS).",
            hint="Crie o usuário do app com: python manage.py criar_usuario_banco (docs/COMO_RODAR_E_PUBLICAR.md, parte B).",
            id="hera.E001")]
    return []


# Logins criados por seed_demo (@hera.demo) e demo_semana (@semana.demo). A senha deles é pública (está na documentação).
DEMO_EMAIL_DOMAINS = ("@hera.demo", "@semana.demo")


@register(Tags.database, deploy=True)
def demo_logins_check(app_configs, **kwargs):
    """Em produção não pode existir login de demonstração: a senha deles é conhecida."""
    if not settings.IS_PRODUCTION:
        return []
    try:
        from django.contrib.auth import get_user_model
        from django.db.models import Q

        q = Q()
        for domain in DEMO_EMAIL_DOMAINS:
            q |= Q(email__iendswith=domain)
        found = get_user_model().objects.filter(q).count()
    except Exception:
        return []  # banco ainda sem tabelas (primeira publicação)
    if found:
        return [Error(
            f"Existem {found} login(s) de demonstração neste banco (e-mails @hera.demo ou @semana.demo, com senha conhecida).",
            hint="Produção usa um banco novo, sem seed_demo nem demo_semana. Não copie o banco de demonstração para produção.",
            id="hera.E002")]
    return []
