"""Campanhas no app (etapa 3, passo 3.4; visão, "Campanhas" e "Uma campanha de cada vez por criador").

De onde vêm: o Claude lê no Backstage, junto com a leitura diária, a tela Operações › Campanhas (as campanhas da
plataforma e as dirigidas pela Agência, a situação de cada criador em cada uma e o link de "Compartilhar") e envia
pela porta de importação (`receive_reading`). Ninguém cadastra campanha do TikTok à mão no app.

O que o criador vê: só as campanhas em que participa (situação "qualifica-se", "inscrito" ou "em andamento" na
leitura; ou a inclusão manual; ou, sem nenhuma das duas, o público da campanha), e só as que a gestão marcou como
foco, com o resumo da regra e o botão para o TikTok. Nunca posição nem ranking: isso fica no app do TikTok.

Campanha do momento: a escolha da gestora na ficha (`CampaignPick`) vence; sem escolha, a de melhor encaixe com o que
o criador já faz nas últimas semanas (`suggest`), com o motivo em uma frase para a gestora. A chance (participantes
sobre elegíveis e até que posição premia) entra quando a leitura traz os números.
"""
import datetime as dt
import re

from django.db import transaction
from django.utils import timezone

from data import engine as E

from .models import Campaign, CampaignParticipant, CampaignPick
from .services import matches_audience

CREATOR_STATUS_LABEL = {"qualifica": "Você pode se inscrever", "inscrito": "Inscrição feita", "andamento": "Valendo agora", "": ""}
MAX_CAMPAIGNS = 300
MAX_STATUS_ROWS = 20000


class ReadingError(ValueError):
    """Leitura recusada inteira; a mensagem volta para quem enviou."""


# ---------------------------------------------------------------- o que vale para o criador
def _visible_qs(agency, today):
    return (Campaign.objects.filter(agency=agency, published=True, do_not_offer=False, start__lte=today, end__gte=today)
            .prefetch_related("participants"))


def creator_campaigns(creator, facts, today=None, pick=None, include_unfocused=False):
    """Campanhas que o criador vê no app: as de foco em que participa, mais a escolhida para ele pela gestora.

    `include_unfocused`: também as do TikTok que não são foco (opções da gestora na ficha)."""
    today = today or E.tiktok_today()
    pick = pick if pick is not None else CampaignPick.objects.filter(creator=creator).first()
    picked_id = pick.campaign_id if pick else None
    out = []
    for c in _visible_qs(creator.agency, today):
        if c.source == "backstage" and not c.featured and c.pk != picked_id and not include_unfocused:
            continue  # do TikTok, só o que a gestão escolheu como foco (ou a campanha do momento escolhida para ele)
        rows = list(c.participants.all())
        if rows or c.read_at:  # campanha lida do Backstage: vale só a situação lida (ninguém listado = ninguém da Hera)
            mine = next((r for r in rows if r.creator_id == creator.pk), None)
            if mine is None or mine.status not in CampaignParticipant.ACTIVE:
                continue
            status = mine.status
        else:
            if not matches_audience(c, facts):
                continue
            status = ""
        out.append({"c": c, "days_left": (c.end - today).days, "status": status, "status_label": CREATOR_STATUS_LABEL.get(status, ""),
                    "status_staff": dict(CampaignParticipant.STATUSES).get(status, "")})
    return sorted(out, key=lambda x: (x["c"].end, x["c"].pk))


# ---------------------------------------------------------------- encaixe com o que o criador já faz
def profile(snaps, today=None):
    """O que o criador fez nas últimas 4 semanas completas ou em andamento (média por semana), pela leitura diária."""
    weeks = E.weekly_intervals(snaps)[-4:]
    n = len(weeks) or 1
    last = snaps[-1] if snaps else None
    guest_share = (last.guest_diamonds / last.diamonds) if last and last.diamonds else 0
    return {
        "weeks": len(weeks),
        "battles": sum(w.battles for w in weeks) / n,
        "hours": sum(w.hours for w in weeks) / n,
        "valid_days": sum(w.valid_days for w in weeks) / n,
        "new_fans": sum(w.new_fans for w in weeks) / n,
        "diamonds": sum(w.diamonds for w in weeks) / n,
        "guest_share": guest_share,
    }


def _fmt(x):
    return f"{x:.0f}" if x >= 10 else f"{x:.1f}".replace(".", ",").replace(",0", "")


def fit(campaign, p):
    """Nota de encaixe (0 a 3) e o motivo, pela mecânica da campanha e pelo perfil das últimas semanas."""
    mech = campaign.mechanic or ("batalha" if campaign.tiktok_kind == "batalha" else "")
    if not p["weeks"]:
        return 1, "ainda sem semanas de LIVE nos dados"
    if mech == "batalha":
        b = p["battles"]
        why = f"faz {_fmt(b)} batalha{'s' if b >= 2 else ''} por semana" if b >= 0.5 else "não fez batalha nas últimas semanas"
        return (3 if b >= 6 else 2 if b >= 3 else 0), why
    if mech == "horas":
        d = p["valid_days"]
        why = (f"faz {_fmt(d)} dia{'s' if d >= 2 else ''} válido{'s' if d >= 2 else ''} por semana" if d >= 0.5
               else "não teve dia válido nas últimas semanas")
        return (3 if d >= 5 else 2 if d >= 3 else 1), why
    if mech == "fa_clube":
        f = p["new_fans"]
        why = (f"ganha {_fmt(f)} fã{'s' if f >= 2 else ''} novo{'s' if f >= 2 else ''} no fã-clube por semana" if f >= 0.5
               else "sem fãs novos no fã-clube nas últimas semanas")
        return (3 if f >= 20 else 2 if f >= 5 else 1), why
    if mech == "cohost":
        g = p["guest_share"]
        return (3 if g >= 0.2 else 2 if g > 0 else 0), ("faz co-host e convidados" if g > 0 else "não aparece co-host nos dados")
    if mech == "presentes":
        return 2, "a campanha conta presentes, e todo criador recebe"
    if mech == "videos":
        return 1, "vídeos ainda não chegam na leitura"
    return 1, "a campanha ainda não tem mecânica marcada"


def chance(campaign):
    """Nota de chance (0 a 2) e o motivo, quando a leitura traz participantes e a campanha diz até que posição premia."""
    n, until = campaign.participants_n, campaign.prize_until
    if n is None:
        return 0, ""
    if n == 0:
        return 2, "ninguém participa ainda"
    if until and n <= until:
        return 2, f"só {n} participante{'s' if n != 1 else ''} e premia até o {until}º"
    if n <= 5:
        return 1, f"só {n} participante{'s' if n != 1 else ''}"
    return 0, f"{n} participantes"


def suggest(items, p):
    """A campanha do momento pela nota (encaixe pesa mais que a chance; empate: a que fecha primeiro)."""
    best = None
    for it in items:
        f, why_f = fit(it["c"], p)
        ch, why_c = chance(it["c"])
        score = f * 2 + ch
        key = (-score, it["c"].end, it["c"].pk)
        if best is None or key < best[0]:
            why = why_f + (f" e {why_c}" if why_c and ch else "")
            best = (key, {"item": it, "why": why, "score": score, "by": "nota"})
    return best[1] if best else None


def campaign_of_the_moment(creator, items, snaps=None, pick=None):
    """A escolha da gestora vence (inclusive "nenhuma"); sem escolha, a sugestão pela nota."""
    pick = pick if pick is not None else CampaignPick.objects.filter(creator=creator).first()
    if pick is not None:
        if pick.campaign_id is None:
            return None
        it = next((x for x in items if x["c"].pk == pick.campaign_id), None)
        if it is not None:
            return {"item": it, "why": "escolhida pela gestão", "by": "gestao"}
    snaps = snaps if snaps is not None else list(creator.snapshots.all())
    return suggest(items, profile(snaps))


# ---------------------------------------------------------------- leitura do Backstage (porta de importação)
_STATUS_IN = {
    "qualifica": "qualifica", "qualifica-se": "qualifica", "qualificado": "qualifica", "disponivel": "qualifica",
    "inscrito": "inscrito", "inscrita": "inscrito", "inscricao": "inscrito",
    "andamento": "andamento", "em andamento": "andamento", "em_andamento": "andamento", "participando": "andamento",
    "encerrada": "encerrada", "encerrado": "encerrada",
}
_KIND_IN = {"tabela": "tabela", "tabela de classificacao": "tabela", "classificacao": "tabela", "batalha": "batalha",
            "desafio de batalha": "batalha", "missao": "missao"}
_MECH_IN = {k: k for k, _ in Campaign.MECHANICS}


def _norm(txt):
    import unicodedata

    return unicodedata.normalize("NFKD", str(txt or "")).encode("ascii", "ignore").decode().strip().lower()


def _date(txt, field, name):
    try:
        return dt.date.fromisoformat(str(txt)[:10])
    except (TypeError, ValueError):
        raise ReadingError(f"Campanha “{name}”: “{field}” precisa ser uma data AAAA-MM-DD.") from None


def _int(v):
    try:
        return int(str(v).replace(".", "").replace(",", "").strip()) if v not in (None, "") else None
    except ValueError:
        return None


def _link(v):
    v = str(v or "").strip()
    return v if re.match(r"^https://(www\.|vm\.|vt\.)?tiktok\.com/", v) else ""


def receive_reading(agency, payload, now=None):
    """Grava a leitura de campanhas (campanhas + situação de cada criador). Devolve o resumo para a resposta da porta.

    - Cada campanha é achada pelo "id" do Backstage ou, sem ID, pelo nome com a data de início: reenviar não duplica.
    - O que a gestão decide (foco, "não oferecer", mecânica e "premia até" já conferidos) nunca é sobrescrito: a
      leitura só preenche a mecânica e o "premia até" quando ainda estão vazios.
    - A situação de cada criador é trocada inteira, campanha por campanha (quem sumiu da leitura deixa de valer).
      Inclusões manuais da gestão ficam como estão.
    - @ que não é da agência é ignorado e contado.
    """
    now = now or timezone.now()
    if not isinstance(payload, dict) or not isinstance(payload.get("campanhas"), list):
        raise ReadingError("Envie um JSON com a lista “campanhas” (e, se tiver, “criadores”).")
    camps, rows = payload["campanhas"], payload.get("criadores") or []
    if not isinstance(rows, list):
        raise ReadingError("“criadores” precisa ser uma lista.")
    if len(camps) > MAX_CAMPAIGNS or len(rows) > MAX_STATUS_ROWS:
        raise ReadingError("Leitura grande demais para a tela de campanhas do Backstage.")
    counts = {"campanhas_novas": 0, "campanhas_atualizadas": 0, "situacoes": 0, "criadores_desconhecidos": 0, "sem_link": 0}
    with transaction.atomic():
        by_key = {}
        for raw in camps:
            if not isinstance(raw, dict) or not str(raw.get("nome") or "").strip():
                raise ReadingError("Toda campanha precisa de “nome”.")
            name = str(raw["nome"]).strip()[:120]
            start, end = _date(raw.get("inicio"), "inicio", name), _date(raw.get("fim"), "fim", name)
            if end < start:
                raise ReadingError(f"Campanha “{name}”: o fim vem antes do início.")
            key = str(raw.get("id") or "").strip() or f"{_norm(name)}|{start.isoformat()}"
            c = Campaign.objects.filter(agency=agency, backstage_key=key[:160]).first()
            fields = {
                "name": name, "start": start, "end": end, "backstage_tab": "agencia" if _norm(raw.get("aba")) == "agencia" else "plataforma",
                "tiktok_kind": _KIND_IN.get(_norm(raw.get("tipo")), ""), "recommended_level": str(raw.get("nivel_recomendado") or "")[:60],
                "participants_n": _int(raw.get("participantes")), "eligible_n": _int(raw.get("elegiveis")),
                "total_diamonds": _int(raw.get("diamantes")), "read_at": now,
            }
            link = _link(raw.get("link"))
            if c is None:
                c = Campaign(agency=agency, backstage_key=key[:160], source="backstage", featured=False, published=True,
                             rules=str(raw.get("regras") or raw.get("resumo") or "")[:4000], **fields)
                c.what_to_do = str(raw.get("resumo") or "")[:1000]
                c.prizes = str(raw.get("premios") or "")[:1000]
                c.tiktok_url = link
                c.mechanic = _MECH_IN.get(_norm(raw.get("mecanica")), "")
                c.prize_until = _int(raw.get("premia_ate"))
                c.save()
                counts["campanhas_novas"] += 1
            else:
                for k, v in fields.items():
                    setattr(c, k, v)
                c.tiktok_url = c.tiktok_url or link
                c.what_to_do = c.what_to_do or str(raw.get("resumo") or "")[:1000]
                c.prizes = c.prizes or str(raw.get("premios") or "")[:1000]
                c.rules = c.rules or str(raw.get("regras") or raw.get("resumo") or "")[:4000]
                c.mechanic = c.mechanic or _MECH_IN.get(_norm(raw.get("mecanica")), "")
                c.prize_until = c.prize_until or _int(raw.get("premia_ate"))
                c.save()
                counts["campanhas_atualizadas"] += 1
            if not c.tiktok_url:
                counts["sem_link"] += 1
            by_key[key[:160]] = c
            by_key.setdefault(_norm(name), c)
        # situação de cada criador em cada campanha
        from data.importer import _find_creator_by_username

        found = {}
        new_rows = {}
        for r in rows:
            if not isinstance(r, dict):
                continue
            camp = by_key.get(str(r.get("campanha") or "").strip()) or by_key.get(_norm(r.get("campanha")))
            status = _STATUS_IN.get(_norm(r.get("situacao")))
            handle = str(r.get("usuario") or "").strip().lstrip("@")
            if camp is None or status is None or not handle:
                continue
            if handle not in found:
                found[handle] = _find_creator_by_username(agency, handle)
            creator = found[handle]
            if creator is None:
                counts["criadores_desconhecidos"] += 1
                continue
            new_rows[(camp.pk, creator.pk)] = status
        touched = {c.pk for c in by_key.values()}
        if rows:  # sem a lista de criadores, a situação de antes continua valendo
            old = CampaignParticipant.objects.filter(campaign_id__in=touched, from_backstage=True)
            CampaignParticipant.objects.filter(pk__in=[p.pk for p in old if (p.campaign_id, p.creator_id) not in new_rows]).delete()
            for (cid, crid), status in new_rows.items():
                obj, created = CampaignParticipant.objects.get_or_create(campaign_id=cid, creator_id=crid,
                                                                         defaults={"status": status, "from_backstage": True})
                if not created and obj.from_backstage and obj.status != status:
                    obj.status = status
                    obj.save(update_fields=["status", "updated_at"])
                counts["situacoes"] += 1
    return counts
