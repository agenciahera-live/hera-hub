"""Fábricas de dados FICTÍCIOS para testes."""
import datetime as dt
import itertools

from django.contrib.auth import get_user_model
from django.conf import settings

from core.bootstrap import setup_agency
from core.models import Consent, Membership
from core.rls import system_context
from crm.models import Creator, CreatorStatus
from data.models import CreatorSnapshot, ImportBatch

_seq = itertools.count(1)



def agency(slug="hera"):
    with system_context():
        return setup_agency(name="Agência Teste", slug=slug)


def user(email=None, role=None, ag=None, **kw):
    n = next(_seq)
    User = get_user_model()
    u = User.objects.create_user(username=f"u{n}", email=email or f"user{n}@teste.local", password="x", **kw)
    if role and ag:
        Membership.objects.create(user=u, agency=ag, role=role)
    return u


def creator(ag, username=None, streamer_user=None, joined_days_ago=200, status=CreatorStatus.ATIVO, **kw):
    n = next(_seq)
    with system_context():
        c = Creator.objects.create(
            agency=ag, tiktok_id=str(7000000000000000000 + n), display_name=f"Teste {n}", username=username or f"teste.{n}",
            user=streamer_user, status=status,
            joined_at=dt.datetime(2026, 9, 28, 12, tzinfo=dt.timezone.utc) - dt.timedelta(days=joined_days_ago), **kw,
        )
        if streamer_user:
            Membership.objects.create(user=streamer_user, agency=ag, role="streamer")
            Consent.objects.create(user=streamer_user, version=settings.CONSENT_VERSION)
    return c


def snapshot(c, start, end, diamonds=0, hours=0, valid_days=0, streams=0, battles=0, pct_diamonds=None, **kw):
    with system_context():
        b = ImportBatch.objects.create(agency=c.agency, kind="backstage", filename="teste.xlsx", file_hash="x", status="committed")
        return CreatorSnapshot.objects.create(
            batch=b, agency=c.agency, creator=c, period_start=start, period_end=end,
            exported_at=dt.datetime.combine(end + dt.timedelta(days=1), dt.time(10), tzinfo=dt.timezone.utc),
            diamonds=diamonds, live_seconds=int(hours * 3600), valid_days=valid_days, streams=streams, battles=battles,
            pct_diamonds=pct_diamonds, **kw,
        )
