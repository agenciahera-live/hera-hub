"""Marco da primeira LIVE (etapa 5, passo 5.1; visão, "Detalhes que fazem diferença": "Marco da primeira LIVE").

Na manhã seguinte à leitura do Backstage que mostra a 1ª LIVE, o Meu progresso abre com um cartão: "Sua primeira LIVE
com a Hera durou X e contou (ou não contou) como dia válido, pela regra do TikTok". Junto vêm três perguntas
opcionais, de um toque (o que foi mais difícil, como se sentiu, com o que quer ajuda agora). As respostas vão para a
ficha e para o card da fila do novato; a gestora recebe aviso na primeira resposta. O retorno depois da LIVE
continua no grupo individual, com a gestora.

Regras:
- A 1ª LIVE é o primeiro intervalo de leitura com LIVE (`data.engine.intervals`). Só com leitura de um dia dá para
  dizer quanto durou e se contou; com leitura de vários dias juntos, o cartão comemora sem número.
- Só para quem fez a 1ª LIVE até `MAX_DAYS_AFTER_JOIN` dias depois da entrada (a base antiga, carregada de uma vez,
  não recebe o cartão).
- O cartão fica até `CARD_DAYS` dias depois da 1ª LIVE, até o criador responder as três ou tocar em "Fechar".
- "com a Hera": vale para quem veio de outra agência ou já tinha público.
"""
import datetime as dt

from django.utils import timezone

from data import engine as E

from .models import FirstLiveCheckin

CARD_DAYS = 7
MAX_DAYS_AFTER_JOIN = 30
SHOW_IN_QUEUE_DAYS = 14  # as respostas aparecem nos cards do novato por duas semanas


def fmt_duration(seconds):
    """3h05, 1h, 45 min."""
    minutes = int(round((seconds or 0) / 60))
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h{m:02d}"
    if h:
        return f"{h}h"
    return f"{m} min"


def first_live(creator, snaps=None):
    """O fato da 1ª LIVE pela leitura: {"date", "seconds", "valid", "exact"} ou None.

    `exact` = a leitura cobre um dia só (dá para dizer a duração e se contou)."""
    snaps = snaps if snaps is not None else list(creator.snapshots.all())
    iv = next((i for i in E.intervals(snaps) if i.had_live), None)
    if iv is None:
        return None
    exact = iv.days == 1
    return {"date": iv.start if exact else iv.end, "start": iv.start, "end": iv.end, "seconds": iv.live_seconds,
            "valid": iv.valid_days > 0, "exact": exact}


def eligible(creator, fact):
    if not fact or not creator.joined_at:
        return False
    joined = creator.joined_at.date()
    start = max(fact["start"], joined)  # leitura que começa antes da entrada: a LIVE foi depois dela (como em recalculate)
    return fact["end"] >= joined and (start - joined).days <= MAX_DAYS_AFTER_JOIN


def headline(fact):
    if not fact["exact"]:
        return "Você fez a sua primeira LIVE com a Hera! 🎉"
    counted = "contou como dia válido" if fact["valid"] else "ainda não contou como dia válido"
    return f"Sua primeira LIVE com a Hera durou {fmt_duration(fact['seconds'])} e {counted}, pela regra do TikTok. 🎉"


def card(creator, snaps=None, today=None):
    """O cartão do Meu progresso, ou None quando não deve aparecer."""
    today = today or E.tiktok_today()
    fact = first_live(creator, snaps)
    if not eligible(creator, fact) or (today - fact["end"]).days > CARD_DAYS:
        return None
    ck = FirstLiveCheckin.objects.filter(creator=creator).first()
    if ck and (ck.closed_at or ck.complete):
        return None
    return {"headline": headline(fact), "fact": fact, "checkin": ck, "questions": questions(ck)}


def questions(ck):
    """As três perguntas, com a resposta já dada (se houver)."""
    return [
        {"key": "hardest", "title": "O que foi mais difícil?", "options": FirstLiveCheckin.HARDEST, "value": ck.hardest if ck else ""},
        {"key": "feeling", "title": "Como você se sentiu?", "options": FirstLiveCheckin.FEELING, "value": ck.feeling if ck else ""},
        {"key": "help", "title": "Com o que você quer ajuda agora?", "options": FirstLiveCheckin.HELP, "value": ck.help if ck else ""},
    ]


class CheckinError(ValueError):
    pass


def answer(creator, key, value, snaps=None):
    """O criador tocou numa resposta (ou em "Fechar", key="close"). Devolve (checkin, primeira_resposta)."""
    fact = first_live(creator, snaps)
    if not eligible(creator, fact):
        raise CheckinError("Ainda não há primeira LIVE na leitura.")
    ck, _ = FirstLiveCheckin.objects.get_or_create(creator=creator, defaults={"live_date": fact["date"]})
    first = not ck.answered
    now = timezone.now()
    if key == "close":
        ck.closed_at = now
        ck.save(update_fields=["closed_at"])
        return ck, False
    options = {"hardest": FirstLiveCheckin.HARDEST, "feeling": FirstLiveCheckin.FEELING, "help": FirstLiveCheckin.HELP}.get(key)
    if options is None or value not in dict(options):
        raise CheckinError("Resposta inválida.")
    setattr(ck, key, value)
    ck.answered_at = now
    ck.save(update_fields=[key, "answered_at"])
    return ck, first


def notify_manager(creator, ck):
    """Aviso no sininho da gestora na primeira resposta (as outras ela vê na ficha e na fila)."""
    from .services import notify

    mgr = creator.current_manager()
    if mgr:
        notify(user=mgr, kind="primeira_live", title=f"@{creator.username} contou no app como foi a 1ª LIVE",
               body=ck.summary()[:200], url=f"/gestao/creators/{creator.pk}/?tab=onboarding")


def for_queue(creator_ids, today=None):
    """{creator_id: "mais difícil: … · sentiu: … · quer ajuda: …"} das respostas recentes, para os cards do novato."""
    today = today or timezone.localdate()
    since = today - dt.timedelta(days=SHOW_IN_QUEUE_DAYS)
    out = {}
    for ck in FirstLiveCheckin.objects.filter(creator_id__in=creator_ids, live_date__gte=since):
        if ck.answered:
            out[ck.creator_id] = ck.summary()
    return out
