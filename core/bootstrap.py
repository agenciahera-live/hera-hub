"""Cria a agência com todas as regras e conteúdos padrão (idempotente)."""
from django.db import transaction

from core.models import Agency, AgencySettings, PartnerGroup

BACKSTAGE_PT_MAP = {
    "Período dos dados": "period",
    "ID do criador": "tiktok_id",
    "Nome do criador": "name",
    "Grupo": "group",
    "Agente": "agent",
    "Horário de ingresso": "joined_at",
    "Dias desde que entrou para a rede": "days_in_network",
    "Diamantes": "diamonds",
    "Duração da LIVE": "live_duration",
    "Dias válidos de início de LIVE": "valid_days",
    "Novos seguidores": "new_followers",
    "Transmissões de LIVE": "streams",
    "Diamantes do mês passado": "lm_diamonds",
    "Duração de LIVE (horas) no último mês": "lm_live_duration",
    "Dias de início de LIVE válidos no mês passado": "lm_valid_days",
    "Novos seguidores no último mês": "lm_new_followers",
    "Transmissões de LIVE no mês passado": "lm_streams",
    "Diamantes - Porcentagem alcançada": "pct_diamonds",
    "Duração da LIVE - Porcentagem alcançada": "pct_hours",
    "Dias válidos de início de LIVE - Porcentagem alcançada": "pct_valid_days",
    "Novos seguidores - Porcentagem alcançada": "pct_followers",
    "Transmissões de LIVE - Porcentagem alcançada": "pct_streams",
    "Diamantes - vs. mês passado": "_vs",
    "Duração da LIVE - vs. mês passado": "_vs",
    "Dias válidos de início de LIVE - vs. mês passado": "_vs",
    "Novos seguidores - vs. mês passado": "_vs",
    "Transmissões de LIVE - vs. mês passado": "_vs",
    "Batalhas": "battles",
    "Diamantes obtidos de batalhas": "battle_diamonds",
    "Novos criadores de LIVE": "new_live_creator",
    "Diamantes de convidados": "guest_diamonds",
    "Diamantes de convidados (como apresentador)": "_extra",
    "Diamantes de convidados (como convidado)": "_extra",
    "Status da graduação": "graduation_status",
    "Status do nível": "level_status",
    "Novos fãs": "new_fans",
    "Total de Diamantes do Fã-clube": "_extra",
    "% de contribuição de fãs": "_extra",
    "Total de fãs": "_extra",
    "Fãs ativos do Fã-clube": "_extra",
    "Status": "status",
}
BACKSTAGE_PT_SIGNATURE = ["Período dos dados", "ID do criador", "Diamantes", "Duração da LIVE", "Dias válidos de início de LIVE"]

TASK_EN_MAP = {
    "Data Month": "month",
    "Creator ID": "tiktok_id",
    "Creator nickname": "name",
    "Handle": "handle",
    "Creator Network manager": "_extra",
    "Group": "group",
    "Group manager": "_extra",
    "Is violative creators": "violative",
    "The creator was Rookie at the time of first joining": "rookie",
    "Diamonds": "diamonds",
    "Valid days(d)": "valid_days",
    "LIVE duration(h)": "live_hours",
    # Colunas de bônus: ignoradas por decisão (29/09)
    "Estimated bonus": "_ignore",
    "Estimated bonus - Maintained tiers": "_ignore",
    "Estimated bonus - Incremental revenue incentive": "_ignore",
    "Estimated bonus - Activeness incentive": "_ignore",
    "Estimated bonus - Mature creator rank-up rate": "_ignore",
    "Estimated bonus - Mature creator maintenance rate": "_ignore",
    "Estimated bonus - Ranked up": "_ignore",
}
TASK_EN_SIGNATURE = ["Data Month", "Creator ID", "Diamonds", "Valid days(d)", "LIVE duration(h)"]

REQUIRED_FIELDS = {
    "backstage": ["period", "tiktok_id", "name", "diamonds", "live_duration", "valid_days"],
    "task": ["month", "tiktok_id", "diamonds", "valid_days", "live_hours"],
}


def ensure_import_templates():
    from data.models import ImportTemplate

    ImportTemplate.objects.update_or_create(
        agency=None, name="Backstage PT",
        defaults={"kind": "backstage", "signature": BACKSTAGE_PT_SIGNATURE, "column_map": BACKSTAGE_PT_MAP},
    )
    ImportTemplate.objects.update_or_create(
        agency=None, name="Task EN",
        defaults={"kind": "task", "signature": TASK_EN_SIGNATURE, "column_map": TASK_EN_MAP},
    )


@transaction.atomic
def setup_agency(name="Agência Hera", slug="hera"):
    from crm.models import OnboardingItem
    from data.models import GroupRule, TierRule
    from engage import defaults as D
    from engage.models import FaqItem, Tip

    agency, _ = Agency.objects.get_or_create(slug=slug, defaults={"name": name})
    AgencySettings.objects.get_or_create(agency=agency)
    PartnerGroup.objects.get_or_create(
        agency=agency, name="Não está em um grupo", defaults={"is_direct": True, "streamer_access_enabled": True}
    )
    for tier, mn, phase in D.TIERS:
        TierRule.objects.get_or_create(agency=agency, tier=tier, defaults={"min_diamonds": mn, "phase": phase})
    for i, (gname, tmin, tmax) in enumerate(D.GROUPS):
        GroupRule.objects.get_or_create(agency=agency, name=gname, defaults={"tier_min": tmin, "tier_max": tmax, "order": i})
    for i, (code, label, anchor, day, rule) in enumerate(D.ONBOARDING):
        OnboardingItem.objects.get_or_create(
            agency=agency, code=code, defaults={"label": label, "anchor": anchor, "day": day, "auto_rule": rule, "order": i}
        )
    from engage.library import sync_defaults

    sync_defaults(agency)  # biblioteca de mensagens do Playbook: só cria o que falta, nunca mexe em texto já editado
    if not FaqItem.objects.filter(agency=agency).exists():
        FaqItem.objects.bulk_create(
            [FaqItem(agency=agency, category=c, question=q, answer=a, keywords=k) for c, q, a, k in D.FAQ]
        )
    if not Tip.objects.filter(agency=agency).exists():
        Tip.objects.bulk_create([Tip(agency=agency, text=t) for t in D.TIPS])
    ensure_import_templates()
    return agency


CONTENT_MODELS = ["campaign", "campaignparticipant", "announcement", "course", "lesson", "tip", "partneroffer",
                  "survey", "surveyquestion", "faqitem", "messagetemplate"]


def ensure_permission_groups():
    """Grupo de permissões do Django para o papel Conteúdo (acesso aos cadastros de conteúdo)."""
    from django.contrib.auth.models import Group, Permission

    g, _ = Group.objects.get_or_create(name="Conteúdo")
    perms = Permission.objects.filter(content_type__app_label="engage", content_type__model__in=CONTENT_MODELS)
    g.permissions.set(perms)
    return g


def sync_user_flags(membership):
    """Admin vira superusuário do painel de cadastros; Conteúdo ganha acesso aos cadastros de conteúdo."""
    u = membership.user
    roles = set(u.memberships.filter(active=True).values_list("role", flat=True))
    u.is_superuser = "admin" in roles
    u.is_staff = bool(roles & {"admin", "conteudo"})
    u.save(update_fields=["is_superuser", "is_staff"])
    g = ensure_permission_groups()
    if "conteudo" in roles:
        u.groups.add(g)
    else:
        u.groups.remove(g)
