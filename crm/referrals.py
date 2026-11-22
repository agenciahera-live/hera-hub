"""Quem indicou quem e o Indique e ganhe (passo 4.7; regulamento de novembro de 2026; decisões da Mariana de 22/11/2026).

A indicação pode cruzar carteiras: a gestora registra que o criador dela foi indicado por um criador de outra
carteira, que ela não enxerga. Por isso estas funções rodam como sistema e devolvem só o @ (que é público
no TikTok), nunca os dados do outro criador.

Regras do programa (valores em Configurações: AgencySettings.referral_* e ReferralBand):
- A indicação nasce com o "indicado por" da ficha (`register`). Registrada mais de N dias depois da entrada (N = janela
  do onboarding) fica marcada "registrada depois da entrada", para as sócias decidirem.
- O app recusa sozinho quem já fez parte da Hera (tem saída registrada antes) e quem é de grupo parceiro (o programa
  vale só para criadores da Hera). O resto as sócias conferem (`decide`).
- Mês 1 = mês da entrada; entrada depois do dia 15 → mês seguinte. Meses 2 e 3 em seguida (`program_months`).
- Bônus do mês: a maior faixa atingida (horas E dias válidos), mais diamantes mínimos nos Meses 2 e 3; só se quem
  indicou fez 25h e 8 dias válidos naquele mês; só para meses que fecharam antes da saída de qualquer um dos dois.
- Graduação: bônus único quando a pessoa indicada gradua (mesma regra do app: X diamantes em um mês dentro da janela).
- Quem indicou vê só a situação e o bônus, nunca os números da pessoa indicada (os motivos não citam números dela).
"""
import datetime as dt
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.rls import system_context

from .models import Creator, CreatorStatus, ExitRecord, Referral, ReferralBand, ReferralBonus

# Faixas do regulamento de novembro de 2026: (mês da pessoa indicada, horas, dias válidos, bônus em R$)
DEFAULT_BANDS = [
    (1, 25, 8, 20), (1, 40, 14, 30), (1, 60, 17, 40), (1, 80, 20, 50), (1, 100, 22, 65),
    (2, 40, 14, 10), (2, 60, 17, 15), (2, 80, 20, 20), (2, 100, 22, 30),
    (3, 40, 14, 5), (3, 60, 17, 10), (3, 80, 20, 15), (3, 100, 22, 20),
]
LEFT = (CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO)


def ensure_bands(agency):
    """Cria as faixas do regulamento se a agência ainda não tiver nenhuma (nunca mexe nas editadas)."""
    if not ReferralBand.objects.filter(agency=agency).exists():
        ReferralBand.objects.bulk_create([ReferralBand(agency=agency, program_month=m, min_hours=h, min_valid_days=d, amount=v)
                                          for m, h, d, v in DEFAULT_BANDS])


# ------------------------------------------------------------------ @ de quem indicou (ficha)
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


def handles(creator_ids):
    """{id: @} de vários criadores. Só o @, que é público no TikTok (a indicação pode cruzar carteiras)."""
    if not creator_ids:
        return {}
    with system_context():
        return dict(Creator.objects.filter(pk__in=creator_ids).values_list("pk", "username"))


def referred_handles(creator):
    """@ de quem este criador indicou."""
    with system_context():
        return list(Creator.objects.filter(referred_by_id=creator.pk).order_by("username").values_list("username", flat=True))


# ------------------------------------------------------------------ registro e validação
class ReferralError(ValueError):
    pass


def _auto_issue(referred, referrer, registered_at):
    if ExitRecord.objects.filter(creator=referred, requested_at__lt=timezone.localtime(registered_at).date()).exists():
        return "Já fez parte da Hera antes (tem saída registrada)."
    for c, who in ((referred, "A pessoa indicada"), (referrer, "Quem indicou")):
        if c.partner_group_id and not c.partner_group.is_direct:
            return f"{who} é de grupo parceiro: o programa vale só para criadores da Hera."
    return ""


def register(referred, referrer_pk, user, now=None):
    """Sincroniza a indicação com o "indicado por" da ficha. `referrer_pk` vazio apaga a indicação.

    Trocar ou apagar não é permitido depois de algum bônus pago (o histórico do pagamento fica)."""
    now = now or timezone.now()
    with system_context():
        old = Referral.objects.filter(referred=referred).first()
        if old and old.referrer_id == referrer_pk:
            return old
        if old and old.bonuses.filter(paid_at__isnull=False).exists():
            raise ReferralError("Esta indicação já tem bônus pago: o “indicado por” não pode mais ser trocado.")
        if old:
            old.delete()
        if not referrer_pk:
            return None
        from core.models import AgencySettings

        referrer = Creator.objects.select_related("partner_group").get(pk=referrer_pk)
        referred = Creator.objects.select_related("partner_group").get(pk=referred.pk)
        st = AgencySettings.objects.get(agency=referred.agency)
        late = bool(referred.joined_at and (now - referred.joined_at).days > st.onboarding_window_days)
        issue = _auto_issue(referred, referrer, now)
        return Referral.objects.create(
            agency=referred.agency, referred=referred, referrer=referrer, registered_at=now, registered_by=user, late=late,
            auto_issue=issue, status="nao_validada" if issue else "", reason=issue)


def decide(referral, user, status, reason=""):
    """As sócias marcam a indicação como válida ou não validada (com o motivo). Quem chama confere que é sócia."""
    if status not in ("valida", "nao_validada"):
        raise ReferralError("Escolha válida ou não validada.")
    if status == "nao_validada" and not reason.strip():
        raise ReferralError("Escreva o motivo: quem indicou vai ver.")
    referral.status, referral.reason = status, (reason.strip()[:240] if status == "nao_validada" else "")
    referral.decided_by, referral.decided_at = user, timezone.now()
    referral.save(update_fields=["status", "reason", "decided_by", "decided_at"])
    return referral


# ------------------------------------------------------------------ cálculo do bônus
def _add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, 1)


def program_months(referred, st):
    """Mês 1, 2 e 3 da pessoa indicada (primeiro dia de cada mês). Sem data de entrada: vazio."""
    if not referred.joined_at:
        return []
    joined = referred.joined_at.astimezone(dt.timezone.utc).date()  # o dia do TikTok é UTC
    m1 = joined.replace(day=1) if joined.day <= st.referral_entry_cutoff_day else _add_months(joined, 1)
    return [m1, _add_months(m1, 1), _add_months(m1, 2)]


def exit_date(creator):
    """Data da saída de quem já saiu da Hera (None = continua na Hera, inclusive em aviso prévio)."""
    if creator.status not in LEFT:
        return None
    ex = ExitRecord.objects.filter(creator=creator).order_by("-requested_at").first()
    return ex.requested_at if ex else timezone.localdate()


def _band(bands, hours, days):
    best = None
    for b in bands:
        if hours >= b.min_hours and days >= b.min_valid_days and (best is None or b.amount > best.amount):
            best = b
    return best


def _month_bonus(n, month, referred_mr, referrer_mr, bands, st, left_on):
    """(valor, motivo) do Mês n. Os motivos são fatos e não citam números da pessoa indicada."""
    from data import engine as E

    end = E.month_end(month)
    if left_on and left_on <= end:
        return Decimal(0), "Saída da Hera antes do fim do mês."
    if referrer_mr is None or referrer_mr.live_seconds < st.referral_referrer_min_hours * 3600 \
            or referrer_mr.valid_days < st.referral_referrer_min_days:
        return Decimal(0), (f"Você não chegou ao mínimo do programa neste mês ({st.referral_referrer_min_hours}h e "
                            f"{st.referral_referrer_min_days} dias válidos).")
    if referred_mr is None:
        return Decimal(0), "A pessoa indicada não chegou à primeira faixa deste mês."
    need = {2: st.referral_m2_min_diamonds, 3: st.referral_m3_min_diamonds}.get(n, 0)
    band = _band([b for b in bands if b.program_month == n], referred_mr.live_seconds / 3600, referred_mr.valid_days)
    if band is None or referred_mr.diamonds < need:
        return Decimal(0), "A pessoa indicada não chegou à primeira faixa deste mês."
    return band.amount, ""


def compute(agency, today=None, now=None):
    """Calcula (ou atualiza) os bônus de todas as indicações nos meses já fechados. Idempotente; nunca mexe em bônus pago.

    Roda na rotina diária (o mês fecha com a leitura do dia 1). Devolve quantos bônus foram gravados."""
    from core.models import AgencySettings
    from data import engine as E
    from data.models import MonthlyResult

    today = today or E.tiktok_today()
    now = now or timezone.now()
    current = E.month_start(today)
    n = 0
    with system_context(), transaction.atomic():
        st = AgencySettings.objects.get(agency=agency)
        bands = list(ReferralBand.objects.filter(agency=agency))
        refs = list(Referral.objects.filter(agency=agency).select_related("referred", "referrer"))
        ids = {r.referred_id for r in refs} | {r.referrer_id for r in refs}
        mrs = {(m.creator_id, m.month): m for m in MonthlyResult.objects.filter(creator_id__in=ids)}
        for r in refs:
            done = {b.kind: b for b in r.bonuses.all()}
            months = program_months(r.referred, st)
            left = [d for d in (exit_date(r.referred), exit_date(r.referrer)) if d]
            left_on = min(left) if left else None
            rows = []
            for i, m in enumerate(months, start=1):
                if m >= current:
                    break  # mês ainda não fechou
                amount, why = _month_bonus(i, m, mrs.get((r.referred_id, m)), mrs.get((r.referrer_id, m)), bands, st, left_on)
                rows.append((f"m{i}", m, amount, why))
            # graduação: um mês fechado, dentro da janela, com os diamantes da graduação
            if r.referred.joined_at:
                start = r.referred.joined_at.astimezone(dt.timezone.utc).date()
                window_end = start + dt.timedelta(days=st.graduation_window_days - 1)
                for (cid, m), mr in sorted(mrs.items(), key=lambda x: x[0][1]):
                    if cid == r.referred_id and m < current and E.month_start(start) <= m <= window_end \
                            and mr.diamonds >= st.graduation_diamonds and not (left_on and left_on <= E.month_end(m)):
                        rows.append(("grad", m, Decimal(st.referral_graduation_bonus), ""))
                        break
            for kind, m, amount, why in rows:
                b = done.get(kind)
                if b and b.paid_at:
                    continue
                if b is None:
                    ReferralBonus.objects.create(referral=r, kind=kind, month=m, amount=amount, reason=why, computed_at=now)
                elif (b.month, b.amount, b.reason) != (m, amount, why):
                    b.month, b.amount, b.reason, b.computed_at = m, amount, why, now
                    b.save(update_fields=["month", "amount", "reason", "computed_at"])
                n += 1
    return n


# ------------------------------------------------------------------ o que cada um vê
STATUS_FOR_REFERRER = {"": "Em andamento", "valida": "Válida", "nao_validada": "Não validada"}


def for_referrer(creator):
    """Tela do criador: as indicações dele, a situação de cada uma e os bônus. Nunca os números da pessoa indicada."""
    rows, total_due, total_paid = [], Decimal(0), Decimal(0)
    refs = list(Referral.objects.filter(referrer=creator).prefetch_related("bonuses"))
    names = handles([r.referred_id for r in refs])  # só o @ da pessoa indicada
    for r in refs:
        bonuses = []
        for b in r.bonuses.all():
            payable = r.status == "valida" and b.amount > 0
            bonuses.append({"b": b, "label": b.get_kind_display(), "payable": payable})
            if payable:
                if b.paid_at:
                    total_paid += b.amount
                else:
                    total_due += b.amount
        rows.append({"r": r, "handle": names.get(r.referred_id, ""), "status": STATUS_FOR_REFERRER.get(r.status, ""),
                     "bonuses": bonuses})
    return {"rows": rows, "due": total_due, "paid": total_paid}


def eligible(creator):
    """O programa vale só para criadores da Hera (grupo parceiro fica de fora)."""
    return not (creator.partner_group_id and not creator.partner_group.is_direct)


def _payable(agency, month):
    return (ReferralBonus.objects.filter(referral__agency=agency, referral__status="valida", month=month, amount__gt=0)
            .select_related("referral__referrer", "referral__referred"))


def month_to_pay(agency, month):
    """Bônus do mês apurado a pagar (indicações válidas, valor acima de zero), por quem indicou, com o Pix cadastrado.
    Só sócias e financeiro (o banco também barra os valores e o Pix para os outros papéis)."""
    from .models import PixInfo

    out = {}
    for b in _payable(agency, month):
        d = out.setdefault(b.referral.referrer_id, {"referrer": b.referral.referrer, "items": [], "total": Decimal(0)})
        d["items"].append(b)
        d["total"] += b.amount
    pix = {p.creator_id: p for p in PixInfo.objects.filter(creator_id__in=out)}
    for cid, d in out.items():
        d["pix"] = pix.get(cid)
        d["paid_at"] = d["items"][0].paid_at if all(b.paid_at for b in d["items"]) else None
        d["receipt_at"] = d["items"][0].receipt_at if all(b.receipt_at for b in d["items"]) else None
    return sorted(out.values(), key=lambda x: x["referrer"].username)


def months_open(agency):
    """Meses com bônus válido ainda sem pagamento (para o financeiro não esquecer mês antigo)."""
    return sorted(set(ReferralBonus.objects.filter(referral__agency=agency, referral__status="valida", amount__gt=0,
                                                   paid_at__isnull=True).values_list("month", flat=True)))


# ------------------------------------------------------------------ Pix (decisão 2A de 22/11: no app; vale também para o 4.6)
def valid_cpf(cpf):
    """Confere os dois dígitos verificadores do CPF (só números)."""
    if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
        return False
    for n in (9, 10):
        s = sum(int(cpf[i]) * (n + 1 - i) for i in range(n))
        if (s * 10 % 11) % 10 != int(cpf[n]):
            return False
    return True


def save_pix(creator, full_name, cpf, key_type, key):
    """O próprio criador cadastra ou troca os dados do Pix. A chave precisa ser da conta do CPF cadastrado (regulamento)."""
    import re as _re

    from .models import PixInfo

    full_name = " ".join((full_name or "").split())[:160]
    cpf = _re.sub(r"\D", "", cpf or "")
    key = (key or "").strip()[:140]
    if len(full_name.split()) < 2:
        raise ReferralError("Escreva o nome completo, como está no CPF.")
    if not valid_cpf(cpf):
        raise ReferralError("Confira o CPF: os números não batem.")
    if key_type not in dict(PixInfo.KEY_TYPES):
        raise ReferralError("Escolha o tipo da chave Pix.")
    if key_type == "cpf":
        key = cpf
    elif key_type == "email" and not _re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", key):
        raise ReferralError("Confira o e-mail da chave Pix.")
    elif key_type == "telefone":
        key = _re.sub(r"\D", "", key)
        if len(key) not in (10, 11, 12, 13):
            raise ReferralError("Confira o celular da chave Pix, com DDD.")
    elif key_type == "aleatoria" and len(key) < 20:
        raise ReferralError("Cole a chave aleatória completa.")
    pix, _ = PixInfo.objects.update_or_create(creator=creator, defaults={"full_name": full_name, "cpf": cpf, "key_type": key_type, "key": key})
    return pix


# ------------------------------------------------------------------ pagamento e recibo (decisão 3A de 22/11)
def _group(agency, referrer_id, month):
    items = list(_payable(agency, month).filter(referral__referrer_id=referrer_id))
    if not items:
        raise ReferralError("Não há bônus válido desse mês para esta pessoa.")
    return items


def mark_paid(agency, referrer_id, month, user, paid_on):
    """O financeiro (ou uma sócia) marca o Pix do mês como pago. Avisa quem indicou no sininho do app."""
    from engage.services import notify

    items = [b for b in _group(agency, referrer_id, month) if not b.paid_at]
    if not items:
        raise ReferralError("Este mês já está marcado como pago.")
    for b in items:
        b.paid_at, b.paid_by = paid_on, user
        b.save(update_fields=["paid_at", "paid_by"])
    total = sum(b.amount for b in items)
    referrer = items[0].referral.referrer
    if referrer.user_id:
        notify(user_id=referrer.user_id, kind="indique", title="Bônus do Indique e ganhe pago 💜",
               body=f"R$ {total:.2f}".replace(".", ",") + f" referente a {month:%m/%Y}, por Pix.", url="/indique-e-ganhe/")
    return total


def mark_receipt(agency, referrer_id, month, user, received_on):
    """O financeiro marca que recebeu o recibo assinado. Só depois do pagamento."""
    items = _group(agency, referrer_id, month)
    if not all(b.paid_at for b in items):
        raise ReferralError("Marque o pagamento antes do recibo.")
    for b in items:
        b.receipt_at, b.receipt_by = received_on, user
        b.save(update_fields=["receipt_at", "receipt_by"])


def receipt(agency, referrer_id, month):
    """Dados do recibo do mês (modelo "Recibo — Indique e Ganhe Hera"), preenchido para imprimir e assinar fora do app."""
    from core.models import AgencySettings

    from .models import PixInfo

    items = _group(agency, referrer_id, month)
    referrer = items[0].referral.referrer
    return {"referrer": referrer, "pix": PixInfo.objects.filter(creator_id=referrer_id).first(), "month": month,
            "items": items, "total": sum(b.amount for b in items), "paid_at": items[0].paid_at if all(b.paid_at for b in items) else None,
            "st": AgencySettings.objects.get(agency=agency)}
