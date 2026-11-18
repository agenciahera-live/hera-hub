"""Quem indicou quem (base do Indique e ganhe).

A indicação pode cruzar carteiras: a gestora registra que o criador dela foi indicado por um criador de outra
carteira, que ela não enxerga. Por isso estas funções rodam como sistema e devolvem só o @ (que é público
no TikTok), nunca os dados do outro criador.
"""
from core.rls import system_context

from .models import Creator, CreatorStatus


def find_by_handle(agency, handle, exclude_pk=None):
    """ID e @ do criador da agência com esse @ (ou None)."""
    handle = (handle or "").strip().lstrip("@")
    if not handle:
        return None
    with system_context():
        qs = Creator.objects.filter(agency=agency, username__iexact=handle).exclude(status=CreatorStatus.ANONIMIZADO)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        return qs.values("pk", "username").first()


def handle_of(creator_id):
    if not creator_id:
        return ""
    with system_context():
        return Creator.objects.filter(pk=creator_id).values_list("username", flat=True).first() or ""


def referred_handles(creator):
    """@ de quem este criador indicou."""
    with system_context():
        return list(Creator.objects.filter(referred_by_id=creator.pk).order_by("username").values_list("username", flat=True))
