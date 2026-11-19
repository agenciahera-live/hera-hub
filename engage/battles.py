"""Batalha oficial (etapa 3, passo 3.3; visão, "Batalhas").

O pedido segue o modelo oficial do roteiro (mensagem BAT-PEDIDO): duas opções de data, a hora, rounds (1, 3 ou tanto
faz), quantos diamantes o criador quer fazer (se não souber, a Hera sugere pelo histórico), se pode ser com criador de
outra agência e se quer ajuda com o banner. As datas começam em hoje + `AgencySettings.battle_notice_days` (7).

A gestão confirma com a data, a hora, os rounds, o oponente e a faixa de diamantes esperada. A confirmação tem o texto
pronto da BAT-CONF para copiar no grupo. O criador vê a batalha confirmada com o checklist do roteiro e marca o que
já fez; o histórico mostra as que já passaram (sem resultado nem diamantes: o registro da gestão é interno).

O app não sugere hora para a batalha: quem escolhe é o criador. O único fato mostrado é o dia do TikTok virar às 21h.
"""
import datetime as dt
import re

from django.utils import timezone

from .models import BattleRequest

# Checklist da confirmação (mensagem BAT-CONF do roteiro), palavra por palavra. A chave fica guardada no pedido.
CHECKLIST = [
    ("antes", "seguir", "Seguir o oponente e divulgar nos vídeos até o dia"),
    ("antes", "testar", "Testar luz, áudio e internet"),
    ("antes", "ferramentas", "Separar as ferramentas (luva, névoa)"),
    ("dia", "abrir", "Abrir a LIVE 30 min antes e já chamar o público"),
    ("dia", "evento", "Desativar o evento, se tiver criado, e conferir o controle de público +18"),
    ("dia", "depois", "Não encerrar logo depois: a entrega da LIVE costuma subir"),
]
CHECKLIST_KEYS = {k for _g, k, _t in CHECKLIST}
OPEN_STATUSES = ("pendente", "outro_horario")


class BattleError(ValueError):
    """Pedido que não pode ser gravado; a mensagem vai para a tela do criador."""


def earliest_date(settings_, today=None):
    today = today or timezone.localdate()
    return today + dt.timedelta(days=settings_.battle_notice_days)


def _date(txt):
    try:
        return dt.date.fromisoformat(txt)
    except (TypeError, ValueError):
        raise BattleError("Confira as datas.") from None


def _yes_no(txt):
    return {"sim": True, "nao": False}.get(txt)


def build_request(creator, settings_, data, today=None):
    """Monta o pedido a partir do formulário do app (não grava). Erros saem como BattleError com o texto para o criador."""
    first = earliest_date(settings_, today)
    d1, d2 = _date(data.get("date")), _date(data.get("date2"))
    if d1 == d2:
        raise BattleError("Escolha duas datas diferentes.")
    if min(d1, d2) < first:
        raise BattleError(f"As datas começam em {first:%d/%m}: a Hera precisa de {settings_.battle_notice_days} dias para achar o oponente e vocês divulgarem.")
    try:
        time = dt.time.fromisoformat(data.get("time") or "")
    except ValueError:
        raise BattleError("Escolha a hora em que a batalha começa.") from None
    try:
        rounds = int(data.get("rounds"))
    except (TypeError, ValueError):
        rounds = -1
    if rounds not in dict(BattleRequest.ROUNDS_ASK):
        raise BattleError("Escolha quantos rounds.")
    # decisão da Mariana de 19/11/2026: o criador não escolhe se o oponente é da Hera ou de outra agência (campo vazio)
    goal = (data.get("goal_diamonds") or "").replace(".", "").strip()
    if goal and not goal.isdigit():
        raise BattleError("Escreva os diamantes só com números.")
    return BattleRequest(
        creator=creator, kind="oficial", date=min(d1, d2), time=time, rounds=rounds,
        other_options=[{"date": max(d1, d2).isoformat(), "time": time.strftime("%H:%M")}],
        goal_diamonds=int(goal) if goal else None, other_agency_ok=None,
        banner_help=_yes_no(data.get("banner")) is True, notes=(data.get("notes") or "")[:1000],
    )


def options(b):
    """As datas e horas que o criador ofereceu, na ordem: a primeira e as outras."""
    out = [(b.date, b.time)]
    for o in b.other_options or []:
        try:
            out.append((dt.date.fromisoformat(o["date"]), dt.time.fromisoformat(o["time"])))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def confirm(b, date, time, rounds, opponent, expected_range, reply=""):
    """A gestão confirma: a batalha passa a ser a data e a hora escolhidas. A opção original fica guardada."""
    if rounds not in dict(BattleRequest.ROUNDS):
        raise BattleError("Escolha 1 ou 3 rounds.")
    if not opponent.strip():
        raise BattleError("Informe o oponente.")
    if (date, time) != (b.date, b.time):
        kept = [o for o in options(b) if o != (date, time)]
        b.other_options = [{"date": d.isoformat(), "time": t.strftime("%H:%M")} for d, t in kept]
        b.date, b.time = date, time
    b.rounds, b.opponent_text, b.expected_range = rounds, opponent.strip()[:120], expected_range.strip()[:60]
    b.manager_reply = reply[:240]
    b.status, b.confirmed_at = "aprovada", b.confirmed_at or timezone.now()
    return b


def opponent_handle(txt, empty="@[oponente]"):
    """O oponente como aparece nas mensagens ("@nome · Agência"). Sem oponente, devolve `empty`."""
    txt = (txt or "").strip()
    if not txt:
        return empty
    return txt if txt.startswith("@") else f"@{txt}"


def fill_confirmation(body, b):
    """Preenche o texto da BAT-CONF com os dados da batalha (os colchetes que a Hera não editou)."""
    repl = {
        "[dd/mm]": f"{b.date:%d/%m}", "[hora]": f"{b.time:%H:%M}", "[1 ou 3]": str(b.rounds),
        "[faixa]": b.expected_range or "[faixa]", "@[criador]": f"@{b.creator.username}", "@[oponente]": opponent_handle(b.opponent_text),
    }
    return re.sub("|".join(re.escape(k) for k in repl), lambda m: repl[m.group(0)], body)


def toggle_check(b, key):
    """O criador marca ou desmarca um item do checklist da batalha confirmada."""
    if key not in CHECKLIST_KEYS:
        raise BattleError("Item desconhecido.")
    done = set(b.checklist_done or [])
    done.symmetric_difference_update({key})
    b.checklist_done = [k for _g, k, _t in CHECKLIST if k in done]
    return b


def checklist(b):
    done = set(b.checklist_done or [])
    groups = [(label, [{"key": k, "text": t, "done": k in done} for g, k, t in CHECKLIST if g == code])
              for code, label in (("antes", "Antes"), ("dia", "No dia"))]
    return {"groups": groups, "n_done": len(done & CHECKLIST_KEYS), "n_total": len(CHECKLIST)}


def for_creator(creator, today=None):
    """O que o criador vê em Minhas batalhas: a próxima confirmada (com checklist), os pedidos em aberto e o histórico."""
    today = today or timezone.localdate()
    qs = list(BattleRequest.objects.filter(creator=creator).order_by("date", "time"))
    upcoming = [b for b in qs if b.status == "aprovada" and b.date >= today]
    pending = [b for b in qs if b.status in OPEN_STATUSES]
    history = sorted([b for b in qs if b.status == "realizada" or (b.status == "aprovada" and b.date < today)],
                     key=lambda b: (b.date, b.time), reverse=True)[:20]
    declined = sorted([b for b in qs if b.status == "recusada"], key=lambda b: b.created_at, reverse=True)[:5]
    nxt = upcoming[0] if upcoming else None
    return {"next": nxt, "next_checklist": checklist(nxt) if nxt else None, "next_days": (nxt.date - today).days if nxt else None,
            "later": upcoming[1:], "pending": pending, "history": history, "declined": declined}


def next_confirmed(creator, today=None):
    today = today or timezone.localdate()
    return BattleRequest.objects.filter(creator=creator, status="aprovada", date__gte=today).order_by("date", "time").first()
