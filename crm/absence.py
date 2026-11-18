"""Ausência da gestora: o botão "Hoje não trabalho" (visão, "Regras de contato da carteira").

- Os itens do dia passam para o dia seguinte, na ordem da fila. Nada precisa ser movido: a fila é montada a cada dia
  e um item só sai com "Enviei", adiamento ou mudança no dado.
- Os itens que não podem esperar (D10, D12, D14, encerramento, batalha oficial e restrição) vão para quem cobre:
  uma das sócias ou uma recrutadora. Quem cobre é definido pelas sócias na tela Carteiras; sem definição, cobrem as sócias.
- Quem cobre enxerga a carteira da gestora só naquele dia (core/access.py e a função hera_covers do banco).
- Os dias pulados ficam guardados e aparecem para as sócias.

O "dia" da ausência é o dia de trabalho em Brasília (timezone.localdate), o mesmo que o banco usa em hera_today().
"""
import datetime as dt

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.access import COVER_ROLES
from core.models import Membership, Role

from .models import Absence

MAX_DAYS_AHEAD = 60


class AbsenceError(Exception):
    pass


def today():
    return timezone.localdate()


def name_of(user):
    return (user.get_full_name() or user.first_name or user.email) if user else ""


def cover_candidates(agency):
    """Quem pode cobrir: as sócias e as recrutadoras ativas da agência."""
    User = get_user_model()
    return (User.objects.filter(memberships__agency=agency, memberships__role__in=list(COVER_ROLES), memberships__active=True)
            .distinct().order_by("first_name", "email"))


def default_cover(agency, manager):
    """Quem as sócias definiram para cobrir esta gestora (None = as sócias). Só vale se a pessoa ainda pode cobrir."""
    m = Membership.objects.filter(agency=agency, user=manager, role=Role.GESTORA).select_related("covered_by").first()
    cover = m.covered_by if m else None
    if cover is not None and not cover_candidates(agency).filter(pk=cover.pk).exists():
        return None
    return cover


def set_default_cover(agency, manager, cover):
    """Sócias definem quem cobre a gestora. Vale também para as ausências já marcadas de hoje em diante."""
    if cover is not None and (cover.pk == manager.pk or not cover_candidates(agency).filter(pk=cover.pk).exists()):
        raise AbsenceError("Quem cobre precisa ser uma sócia ou uma recrutadora ativa (e não a própria gestora).")
    Membership.objects.filter(agency=agency, user=manager, role=Role.GESTORA).update(covered_by=cover)
    Absence.objects.filter(agency=agency, manager=manager, day__gte=today(), cancelled_at__isnull=True).update(cover=cover)


def active(manager, day=None):
    return Absence.objects.filter(manager=manager, day=day or today(), cancelled_at__isnull=True).select_related("cover", "manager").first()


def start(agency, manager, by, day=None):
    """Marca que a gestora não trabalha no dia e avisa quem cobre e as sócias. Devolve a ausência."""
    from engage.services import notify

    day = day or today()
    if day < today():
        raise AbsenceError("A ausência só pode ser marcada para hoje ou para um dia que ainda vai chegar.")
    if (day - today()).days > MAX_DAYS_AHEAD:
        raise AbsenceError(f"A ausência pode ser marcada com até {MAX_DAYS_AHEAD} dias de antecedência.")
    if not Membership.objects.filter(agency=agency, user=manager, role=Role.GESTORA, active=True).exists():
        raise AbsenceError("Só quem tem o papel Gestora, ativo, tem carteira para cobrir.")
    existing = active(manager, day)
    if existing:
        return existing
    cover = default_cover(agency, manager)
    try:
        with transaction.atomic():
            a = Absence.objects.create(agency=agency, manager=manager, day=day, cover=cover, created_by=by)
    except IntegrityError:  # dois cliques ao mesmo tempo
        return active(manager, day)
    quando = "hoje" if day == today() else f"em {day:%d/%m}"
    who = name_of(manager)
    admins = list(Membership.objects.filter(agency=agency, role=Role.ADMIN, active=True).values_list("user_id", flat=True))
    if cover is not None and cover.pk not in admins:
        notify(user_id=cover.pk, kind="cobertura", url="/gestao/", title=f"Você cobre a carteira de {who} {quando}",
               body="Os itens que não podem esperar aparecem no seu Dashboard, no quadro Cobertura.")
    for uid in admins:
        if uid == manager.pk:
            continue
        notify(user_id=uid, kind="cobertura", url="/gestao/", title=f"{who} não trabalha {quando}",
               body=(f"Cobre: {name_of(cover)}." if cover else "Cobrem as sócias.") + " Os itens que não podem esperar estão no Dashboard, no quadro Cobertura.")
    return a


def cancel(absence, by):
    """ "Voltei": a gestora (ou uma sócia) desfaz a ausência. A cobertura termina na hora; o registro fica."""
    if absence.cancelled_at is None:
        absence.cancelled_at, absence.cancelled_by = timezone.now(), by
        absence.save(update_fields=["cancelled_at", "cancelled_by"])
    return absence


def to_show(user, agency, is_admin):
    """Ausências de hoje que aparecem no Dashboard de quem cobre. As sócias veem todas (elas respondem pela carteira)."""
    qs = Absence.objects.filter(agency=agency, day=today(), cancelled_at__isnull=True).select_related("manager", "cover")
    if not is_admin:
        qs = qs.filter(cover=user)
    return list(qs.order_by("manager__first_name", "manager__email"))


def skipped_days(agency, month_start=None):
    """Dias pulados por gestora no mês (para as sócias): {manager_id: [dias]}. Só o que já aconteceu ou é hoje."""
    t = today()
    first = (month_start or t).replace(day=1)
    nxt = (first + dt.timedelta(days=32)).replace(day=1)
    out = {}
    for mid, day in (Absence.objects.filter(agency=agency, cancelled_at__isnull=True, day__gte=first, day__lt=nxt, day__lte=t)
                     .order_by("day").values_list("manager_id", "day")):
        out.setdefault(mid, []).append(day)
    return out


def upcoming(agency):
    """Ausências marcadas para os próximos dias: {manager_id: [ausências]}."""
    out = {}
    for a in Absence.objects.filter(agency=agency, cancelled_at__isnull=True, day__gt=today()).select_related("cover").order_by("day"):
        out.setdefault(a.manager_id, []).append(a)
    return out
