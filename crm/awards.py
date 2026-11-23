"""Premiações de campanha (etapa 4, passo 4.6; decisões da Mariana de 23/11/2026).

- O criador não pede prêmio: a Hera envia quando ele ganha. A gestora ou uma sócia registra na ficha (`register`).
- Todo prêmio passa pelas sócias: o registro abre um pedido "premiacao" no Painel das sócias › Aprovações.
- Entrega (`deliver`): diamantes na LIVE (gestora ou sócia marca a data da LIVE) ou Pix (financeiro ou sócia marca o dia
  do pagamento). Pix tem recibo preenchido (`receipt`, texto provisório até a revisão da Mariana) e "recibo recebido".
- Dados do Pix: o cadastro do app (`PixInfo`, Indique e ganhe) quando o criador já preencheu; senão, a gestora manda a
  PIX-01 com o formulário Google da Hera, como hoje (decisão 1A), e o financeiro paga com os dados do formulário.
- Fila do dia (`queue_items`): PIX-01 (Pix aprovado sem Pix no app), entregar os diamantes (tarefa) e PIX-02 depois do
  pagamento. O criador não vê esta parte no app (as conquistas e prêmios do app são da etapa 5).
"""
import datetime as dt
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone

from core.rls import system_context

from .models import ApprovalRequest, Award, PixInfo

PIX02_DAYS = 7  # a PIX-02 ("prêmio enviado") fica na fila até 7 dias depois do pagamento


class AwardError(ValueError):
    pass


def register(creator, user, title, kind, won_on, campaign=None, campaign_name="", diamonds=None, value=None, note=""):
    """A gestão registra o prêmio que o criador ganhou e pede a aprovação das sócias."""
    from core.models import Membership, Role
    from engage.services import notify

    title = (title or "").strip()[:160]
    if not title:
        raise AwardError("Escreva o que o criador ganhou (ex.: 1º lugar).")
    if kind not in dict(Award.KINDS):
        raise AwardError("Escolha o tipo do prêmio: diamantes na LIVE ou Pix.")
    if won_on is None:
        raise AwardError("Informe a data em que ganhou.")
    if campaign is None and not (campaign_name or "").strip():
        raise AwardError("Escolha a campanha ou escreva o nome dela.")
    if kind == "diamantes":
        if not diamonds or diamonds <= 0:
            raise AwardError("Informe quantos diamantes.")
        value = None
    else:
        try:
            s = str(value or "0").strip().replace("R$", "").strip()
            value = Decimal(s.replace(".", "").replace(",", ".") if "," in s else s)  # "1.500,00" ou "1500.00"
        except InvalidOperation:
            value = Decimal(0)
        if value <= 0:
            raise AwardError("Informe o valor do Pix.")
        diamonds = None
    award = Award(agency=creator.agency, creator=creator, campaign=campaign, campaign_name=(campaign.name if campaign else campaign_name.strip())[:120],
                  title=title, kind=kind, diamonds=diamonds, value=value, won_on=won_on, note=(note or "").strip()[:240],
                  registered_by=user)
    ap = ApprovalRequest.objects.create(agency=creator.agency, creator=creator, kind="premiacao", item_code="premiacao",
                                        reason=f"{title} · {award.where} · {award.prize_label}"[:160], note=award.note, requested_by=user)
    award.approval = ap
    award.save()
    for m in Membership.objects.filter(agency=creator.agency, role=Role.ADMIN, active=True):
        if m.user_id != user.pk:
            notify(user=m.user, kind="aprovacao", url="/gestao/painel/#aprovacoes",
                   title=f"Premiação para aprovar: @{creator.username}", body=ap.reason)
    return award


def deliver(award, user, on):
    """Marca a entrega: a data da LIVE (diamantes) ou do Pix. Só depois da aprovação das sócias."""
    if award.status != "a_entregar":
        raise AwardError("Só dá para marcar a entrega de prêmio aprovado e ainda não entregue.")
    if on is None or on > timezone.localdate():
        raise AwardError("Informe a data da entrega (hoje ou antes).")
    from .models import Note

    award.delivered_on, award.delivered_by = on, user
    award.save(update_fields=["delivered_on", "delivered_by"])
    what = f"Prêmio em Pix pago em {on:%d/%m}" if award.kind == "pix" else f"Prêmio entregue na LIVE de {on:%d/%m}"
    with system_context():  # o financeiro paga o Pix mas não edita a ficha: a nota da linha do tempo sai pelo sistema
        Note.objects.create(creator_id=award.creator_id, author=user, body=f"{what}: {award.prize_label} ({award.where}).")
    return award


def mark_receipt(award, user, on):
    if award.kind != "pix" or award.status != "entregue":
        raise AwardError("O recibo é do prêmio em Pix já pago.")
    award.receipt_at, award.receipt_by = on or timezone.localdate(), user
    award.save(update_fields=["receipt_at", "receipt_by"])


def receipt(award):
    """Dados do recibo do prêmio em Pix (texto provisório, no modelo do recibo do Indique e ganhe)."""
    from core.models import AgencySettings

    if award.kind != "pix":
        raise AwardError("Só prêmio em Pix tem recibo.")
    return {"a": award, "pix": PixInfo.objects.filter(creator=award.creator).first(),
            "st": AgencySettings.objects.get(agency=award.agency)}


def has_pix(creator_ids):
    """Quem já tem o Pix cadastrado no app. Só o sim ou não (a gestora não lê os dados do Pix)."""
    with system_context():
        return set(PixInfo.objects.filter(creator_id__in=creator_ids).values_list("creator_id", flat=True))


# ------------------------------------------------------------------ fila do dia
def _sent_since(contacts, code, date):
    return any(x.template_code == code and timezone.localtime(x.sent_at).date() >= date for x in contacts)


def queue_items(ctx):
    from web.services import QueueItem

    info, today = ctx["info"], ctx["today"]
    awards = list(Award.objects.filter(creator_id__in=list(info))
                  .filter(Q(approval__decision="aprovar", delivered_on__isnull=True)
                          | Q(kind="pix", delivered_on__gte=today - dt.timedelta(days=PIX02_DAYS)))
                  .select_related("approval", "campaign"))
    if not awards:
        return []
    pix_ok = has_pix({a.creator_id for a in awards if a.kind == "pix"})
    out = []
    for a in awards:
        d = info[a.creator_id]
        c, contacts = d["c"], d["contacts"]
        if a.delivered_on is None and a.status == "a_entregar":
            decided = timezone.localtime(a.approval.decided_at).date()
            if a.kind == "diamantes":
                out.append(QueueItem(c, "premiacao_diamantes", 2, f"Entregar prêmio: {a.prize_label}",
                                     f"{a.title} · {a.where}. Entregue na LIVE e marque “Entregue” na ficha (quadro Prêmios)."))
            elif a.creator_id not in pix_ok and not _sent_since(contacts, "PIX-01", decided):
                out.append(QueueItem(c, "premiacao_pix", 2, f"Premiação aprovada: {a.prize_label}",
                                     f"{a.title} · {a.where}. Sem Pix cadastrado no app: peça os dados pelo formulário da Hera, no "
                                     "privado. O financeiro paga e marca em Premiações.", "PIX-01",
                                     vars={"_replace": {"[prêmio]": a.prize_label, "[campanha]": a.where}}))
        elif a.kind == "pix" and a.delivered_on and not _sent_since(contacts, "PIX-02", a.delivered_on):
            valor = f"R$ {a.value:.2f}".replace(".", ",")
            out.append(QueueItem(c, "premiacao_enviado", 2, "Prêmio em Pix enviado: avise o criador",
                                 f"Pago em {a.delivered_on:%d/%m}: {valor} · {a.where}.", "PIX-02",
                                 vars={"_replace": {"[valor]": valor, "[campanha]": a.where}}))
    return out


# ------------------------------------------------------------------ painel e tela
def cost_by_campaign(agency, since):
    """Prêmios aprovados desde `since`, por campanha: Pix em R$ e diamantes em quantidade (sem converter em reais:
    a compra de moedas ficou fora do app, decisão de 19/11/2026)."""
    out = {}
    for a in Award.objects.filter(agency=agency, approval__decision="aprovar", won_on__gte=since).select_related("campaign"):
        d = out.setdefault(a.where, {"name": a.where, "pix": Decimal(0), "diamonds": 0, "n": 0})
        d["n"] += 1
        if a.kind == "pix":
            d["pix"] += a.value or 0
        else:
            d["diamonds"] += a.diamonds or 0
    return sorted(out.values(), key=lambda x: x["name"])
