"""Aviso de restrição ou banimento enviado pelo criador na tela Ajuda (etapa 3, passo 3.5; visão, "Ajuda").

O aviso abre o caso da conta (AccountCase), que vai para o topo da fila do dia, e avisa a gestora (ou as sócias,
se o criador estiver sem gestora). O caso é uma tabela interna: o criador não lê o caso nem o que a gestão anotou.
Por isso a gravação do caso roda aqui, como sistema, e nunca na view. O criador guarda só o próprio aviso
(SupportTicket do tipo "restricao"), para ver na tela que a Hera já sabe.
"""
import datetime as dt

from django.utils import timezone

from core.models import Membership, Role
from core.rls import system_context

from .models import AccountCase

APPEAL = {"sim": "já fez o recurso", "nao": "ainda não fez o recurso", "nao_sei": "não sabe se fez o recurso"}


def report(creator, kind, when, what, appeal):
    """Grava o aviso do criador e abre (ou completa) o caso. Devolve o aviso (SupportTicket)."""
    from engage.models import SupportTicket
    from engage.services import notify

    kind = kind if kind in dict(AccountCase.KINDS) else "restricao"
    today = timezone.localdate()
    when = when if isinstance(when, dt.date) and when <= today else today
    label = dict(AccountCase.KINDS)[kind]
    text = (f"Aviso pelo app: {label.lower()} em {when:%d/%m}. O que apareceu: {what.strip() or '(não escreveu)'}. "
            f"O criador {APPEAL.get(appeal, APPEAL['nao_sei'])}.")[:2000]
    ticket = SupportTicket.objects.create(creator=creator, kind="restricao", question=text)
    with system_context():
        case = AccountCase.objects.filter(creator=creator, resolved_at__isnull=True).first()
        if case is None:
            AccountCase.objects.create(creator=creator, kind=kind, opened_on=when, note=text)
        else:
            case.note = f"{case.note}\n{text}".strip()[:4000]
            case.save(update_fields=["note"])
        mgr = creator.current_manager()
        users = [mgr] if mgr else [m.user for m in Membership.objects.filter(agency=creator.agency, role=Role.ADMIN, active=True)
                                   .select_related("user")]
        for u in users:
            notify(user=u, kind="restricao", title=f"@{creator.username} avisou: {label.lower()} na conta",
                   body=text[:300], url=f"/gestao/creators/{creator.pk}/")
    return ticket
