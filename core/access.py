"""Camada de acesso no Django (primeira camada). A segunda camada é o RLS no Postgres.

- scoped_creators: o que é do usuário (carteira, recrutados, grupo parceiro; sócias veem tudo). Listas e relatórios.
- visible_creators: o mesmo, mais a carteira que ele cobre hoje ("Hoje não trabalho"). Ficha e ações de contato.
"""
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .models import Membership, Role, STAFF_ROLES


def staff_roles(user):
    if not user.is_authenticated:
        return set()
    cache = getattr(user, "_hera_roles", None)
    if cache is None:
        cache = set(Membership.objects.filter(user=user, active=True).values_list("role", flat=True)) & set(STAFF_ROLES)
        user._hera_roles = cache
    return cache


def get_agency(user):
    if not user.is_authenticated:
        return None
    cache = getattr(user, "_hera_agency", None)
    if cache is None:
        m = Membership.objects.filter(user=user, active=True).select_related("agency").first()
        cache = m.agency if m else None
        if cache is None and hasattr(user, "creator"):
            try:
                cache = user.creator.agency
            except Exception:
                cache = None
        user._hera_agency = cache
    return cache


def require_roles(user, *roles):
    if not staff_roles(user) & set(roles):
        raise PermissionDenied


def scoped_creators(user):
    """Creators que este usuário pode ver na gestão (espelha as políticas de RLS)."""
    from crm.models import Creator

    agency = get_agency(user)
    roles = staff_roles(user)
    qs = Creator.objects.filter(agency=agency)
    if roles & {Role.ADMIN, Role.ANALISTA, Role.FINANCEIRO}:
        return qs
    q = Creator.objects.none()
    if Role.GESTORA in roles:
        q = q | qs.filter(assignments__manager=user, assignments__valid_to__isnull=True)
    if Role.RECRUTADORA in roles:
        q = q | qs.filter(recruited_by=user)
    if Role.GESTOR_PARCEIRA in roles:
        pg_ids = Membership.objects.filter(user=user, role=Role.GESTOR_PARCEIRA).values_list("partner_group_id", flat=True)
        q = q | qs.filter(partner_group_id__in=list(pg_ids))
    return q.distinct()


def can_edit_creator(user, creator):
    roles = staff_roles(user)
    if Role.ADMIN in roles:
        return True
    if Role.GESTORA in roles:
        return creator.assignments.filter(manager=user, valid_to__isnull=True).exists()
    return False


# ------------------------------------------------------------------ cobertura ("Hoje não trabalho")
# Quem cobre a gestora ausente enxerga a carteira dela só naquele dia e só pode registrar o contato:
# "Enviei", "Respondeu", "O criador me escreveu" e nota. Espelha as funções hera_covers e hera_staff_can_contact do banco.
COVER_ROLES = {Role.ADMIN, Role.RECRUTADORA}  # visão: "uma das sócias ou uma recrutadora"


def covered_manager_ids(user):
    """Gestoras ausentes hoje que este usuário cobre (lista vazia para quem não cobre ninguém)."""
    from crm.models import Absence

    if not user.is_authenticated or not staff_roles(user) & COVER_ROLES:
        return []
    return list(Absence.objects.filter(agency=get_agency(user), cover=user, day=timezone.localdate(), cancelled_at__isnull=True)
                .values_list("manager_id", flat=True))


def covering_creators(user):
    """Criadores das carteiras que este usuário cobre hoje."""
    from crm.models import Creator

    ids = covered_manager_ids(user)
    if not ids:
        return Creator.objects.none()
    return Creator.objects.filter(agency=get_agency(user), assignments__manager_id__in=ids, assignments__valid_to__isnull=True).distinct()


def covers_creator(user, creator):
    ids = covered_manager_ids(user)
    return bool(ids) and creator.assignments.filter(manager_id__in=ids, valid_to__isnull=True).exists()


def visible_creators(user):
    """Tudo o que este usuário pode abrir: o que é dele (scoped_creators) mais o que ele cobre hoje.
    As listas e os relatórios continuam usando scoped_creators; a ficha e as ações de contato usam esta."""
    from django.db.models import Q

    from crm.models import Creator

    ids = covered_manager_ids(user)
    if not ids:
        return scoped_creators(user)
    return Creator.objects.filter(agency=get_agency(user)).filter(
        Q(pk__in=scoped_creators(user).values("pk")) | Q(assignments__manager_id__in=ids, assignments__valid_to__isnull=True)).distinct()


def can_contact_creator(user, creator):
    """Pode registrar contato (Enviei, Respondeu, nota): quem edita o criador ou quem cobre a carteira dele hoje."""
    return can_edit_creator(user, creator) or covers_creator(user, creator)


# ------------------------------------------------------------------ carteira
def assign_manager(creator, manager, by=None):
    """Troca a gestora do creator mantendo o histórico. O histórico do criador (contatos, notas, 1:1) vai junto,
    porque pertence ao criador: a nova gestora passa a ver tudo, e a anterior deixa de ver."""
    from crm.models import PortfolioAssignment

    now = timezone.now()
    current = creator.assignments.filter(valid_to__isnull=True).first()
    if current and current.manager_id == manager.id:
        return current
    creator.assignments.filter(valid_to__isnull=True).update(valid_to=now)
    return PortfolioAssignment.objects.create(creator=creator, manager=manager, valid_from=now, assigned_by=by)


def unassign_manager(creator):
    """Tira o creator da carteira atual (fica sem gestora, só com as sócias). O histórico fica guardado."""
    return creator.assignments.filter(valid_to__isnull=True).update(valid_to=timezone.now())
