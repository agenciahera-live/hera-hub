"""Primeiro acesso do criador ao app (visão de 14/11/2026).

A gestão gera um código na ficha e envia no grupo individual. O criador abre "Primeiro acesso", informa o @,
o código, o e-mail e cria a senha. Depois entra sempre com e-mail e senha. Esqueceu a senha: código novo.

Segurança:
- o e-mail é informado pelo próprio criador e não é conferido; por isso ele nunca serve para recuperar acesso
  (não existe código por e-mail, "esqueci a senha" por e-mail nem login com Google);
- o código vale uma vez, vence, e é cancelado depois de MAX_ATTEMPTS erros;
- quem saiu da agência não ativa o acesso.

`activate` roda como sistema porque quem chama ainda não tem login (o RLS não mostra nada a anônimos).
"""
import datetime as dt
import re
import secrets

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from core.models import AgencySettings, AuditLog, Membership, Role
from core.rls import system_context

from .models import AccessCode, Creator, CreatorPrivate, CreatorStatus

LEFT = (CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO)
GENERIC_ERROR = "Confira o seu @ e o código. Se o código venceu ou já foi usado, peça um novo à Hera no seu grupo."
EMAIL_IN_USE = "Este e-mail já está em uso no app. Informe outro e-mail."


class AccessError(Exception):
    """Erro que pode ser mostrado ao criador."""


def normalize_code(text):
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def normalize_handle(text):
    return (text or "").strip().lstrip("@").strip().lower()


def active_code(creator, now=None):
    now = now or timezone.now()
    return creator.access_codes.filter(used_at__isnull=True, revoked_at__isnull=True, expires_at__gt=now).first()


def new_code(creator, by=None, now=None):
    """Gera um código novo para o criador e cancela os anteriores que ainda valiam."""
    if creator.status in LEFT:
        raise AccessError("Este criador saiu da agência: não é possível gerar código de acesso.")
    now = now or timezone.now()
    st = AgencySettings.objects.get(agency=creator.agency)
    if st.app_test_only_testers and not creator.app_tester:
        raise AccessError("Durante o teste do app, só quem participa do teste recebe código de acesso. "
                          "As sócias marcam quem participa em Gestão › Teste do app.")
    days = st.access_code_days
    with transaction.atomic():
        creator.access_codes.filter(used_at__isnull=True, revoked_at__isnull=True).update(revoked_at=now)
        code = "".join(secrets.choice(AccessCode.ALPHABET) for _ in range(AccessCode.LENGTH))
        ac = AccessCode.objects.create(creator=creator, code=code, created_by=by, created_at=now,
                                       expires_at=now + dt.timedelta(days=days))
        if creator.status == CreatorStatus.PENDENTE:
            creator.status = CreatorStatus.CONVIDADO
            creator.save(update_fields=["status"])
    return ac


def _match(handle, code, now):
    """Acha o criador pelo @ e confere o código. Código errado conta tentativa (e cancela no limite)."""
    found = None
    for c in Creator.objects.filter(username__iexact=handle).exclude(status__in=LEFT):
        ac = active_code(c, now)
        if ac is None:
            continue
        if constant_time_compare(ac.code, code):
            found = (c, ac)
            continue
        ac.failed_attempts += 1
        if ac.failed_attempts >= AccessCode.MAX_ATTEMPTS:
            ac.revoked_at = now
        ac.save(update_fields=["failed_attempts", "revoked_at"])
    return found


def activate(handle, code, email, password, now=None):
    """Liga o criador a um login com e-mail e senha (ou troca a senha de quem já tem login). Devolve o usuário."""
    from allauth.account.models import EmailAddress

    User = get_user_model()
    now = now or timezone.now()
    handle, code, email = normalize_handle(handle), normalize_code(code), (email or "").strip().lower()
    if not handle or not code or not email or not password:
        raise AccessError(GENERIC_ERROR)
    with system_context():
        found = _match(handle, code, now)  # fora da transação: a tentativa errada fica gravada
        if found is None:
            raise AccessError(GENERIC_ERROR)
        creator, ac = found
        user = creator.user
        taken = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email))
        taken_addr = EmailAddress.objects.filter(email__iexact=email)
        if user is not None:
            taken, taken_addr = taken.exclude(pk=user.pk), taken_addr.exclude(user=user)
        if taken.exists() or taken_addr.exists():
            raise AccessError(EMAIL_IN_USE)
        with transaction.atomic():
            if user is None:
                user = User(username=email[:150], email=email, first_name=creator.first_name.split(".")[0].title()[:150])
            else:
                user.username, user.email = email[:150], email
            user.set_password(password)
            user.save()
            EmailAddress.objects.filter(user=user).exclude(email__iexact=email).delete()
            EmailAddress.objects.update_or_create(user=user, email=email, defaults={"primary": True, "verified": False})
            creator.user = user
            creator.confirmed_username = True  # informou o próprio @ junto com o código
            if creator.status in (CreatorStatus.PENDENTE, CreatorStatus.CONVIDADO):
                creator.status = CreatorStatus.ATIVO
            creator.save(update_fields=["user", "confirmed_username", "status"])
            Membership.objects.get_or_create(user=user, agency=creator.agency, role=Role.STREAMER)
            priv, _ = CreatorPrivate.objects.get_or_create(creator=creator)
            priv.email = email
            priv.save(update_fields=["email"])
            ac.used_at = now
            ac.save(update_fields=["used_at"])
            AuditLog.objects.create(agency=creator.agency, actor=user, action="primeiro_acesso", target=f"creator {creator.pk}")
    return user
