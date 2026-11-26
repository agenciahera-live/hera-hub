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

Passo 4.5 (decisões da Mariana de 22/11/2026):
- Campanha nova da plataforma chega "aguardando" e só vale depois de avaliada (`approve`). Desde 23/11 (decisão 2-A)
  avalia a gestora, no Dashboard (leitura da manhã), ou uma sócia, no Painel: vale quem avaliar primeiro, fica
  registrado quem foi e as sócias podem reabrir (`reopen`).
- A leitura traz a posição e os pontos de cada criador da Hera (`CampaignPosition`), que só a gestão vê, uma frase por
  criador (`position_phrase`). Nunca uma tabela ordenada por posição: o app não tem ranking em nenhuma tela.
- Três listas para a gestão (`follow_lists`) e o acompanhamento na fila do dia (`queue_items`), na agenda do Playbook.
- "Perto de prêmio" = na faixa premiada ou até 3 posições depois dela (`NEAR_PRIZE_POSITIONS`).
"""
import datetime as dt
import re

from django.db import transaction
from django.utils import timezone

from data import engine as E

from .models import Campaign, CampaignParticipant, CampaignPick, CampaignPosition
from .services import matches_audience

CREATOR_STATUS_LABEL = {"qualifica": "Você pode se inscrever", "inscrito": "Inscrição feita", "andamento": "Valendo agora", "": ""}
MAX_CAMPAIGNS = 300
MAX_STATUS_ROWS = 20000
NEAR_PRIZE_POSITIONS = 3  # "perto de prêmio": até 3 posições depois da última premiada (decisão de 22/11)
SHORT_CAMPAIGN_DAYS = 3  # campanhas de até 3 dias: só abertura e véspera (Playbook, "Acompanhamento de campanha")
AFTER_END_DAYS = 2  # "dia seguinte ao fim": o item fica até 2 dias depois do fim, até o "Enviei"
DROP_REPEAT_DAYS = 3  # "pode perder posição": no máximo um aviso a cada 3 dias por criador


class ReadingError(ValueError):
    """Leitura recusada inteira; a mensagem volta para quem enviou."""


# ---------------------------------------------------------------- o que vale para o criador
def _visible_qs(agency, today):
    return (Campaign.objects.filter(agency=agency, published=True, do_not_offer=False, start__lte=today, end__gte=today)
            .exclude(approval__in=("aguardando", "recusada")).prefetch_related("participants"))


def creator_campaigns(creator, facts, today=None, pick=None, include_unfocused=False, camps=None):
    """Campanhas que o criador vê no app: as de foco em que participa, mais a escolhida para ele pela gestora.

    `include_unfocused`: também as do TikTok que não são foco (opções da gestora na ficha).
    `pick=False`: sem escolha da gestora (sem consultar). `camps`: as campanhas visíveis já carregadas (fila do dia).
    `facts=None`: o público só é calculado se alguma campanha precisar dele (as cadastradas à mão)."""
    today = today or E.tiktok_today()
    pick = pick if pick is not None else CampaignPick.objects.filter(creator=creator).first()
    picked_id = pick.campaign_id if pick else None
    out = []
    for c in (camps if camps is not None else _visible_qs(creator.agency, today)):
        if c.source == "backstage" and not c.featured and c.pk != picked_id and not include_unfocused:
            continue  # do TikTok, só o que a gestão escolheu como foco (ou a campanha do momento escolhida para ele)
        rows = list(c.participants.all())
        if rows or c.read_at:  # campanha lida do Backstage: vale só a situação lida (ninguém listado = ninguém da Hera)
            mine = next((r for r in rows if r.creator_id == creator.pk), None)
            if mine is None or mine.status not in CampaignParticipant.ACTIVE:
                continue
            status = mine.status
        else:
            if facts is None:
                from .services import creator_facts

                facts = creator_facts(creator, today)
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
    """A escolha da gestora vence (inclusive "nenhuma"); sem escolha, a sugestão pela nota. `pick=False`: sem escolha."""
    pick = pick if pick is not None else CampaignPick.objects.filter(creator=creator).first()
    if pick:
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


def _given(v):
    """O campo veio preenchido no JSON. Campo ausente, null ou texto vazio = "não mexer" (envio parcial)."""
    return v is not None and str(v).strip() != ""


SUMMARY_FIELDS = (("what_to_do", "resumo"), ("prizes", "premios"), ("mechanic", "mecanica"), ("prize_until", "premia_ate"))


def missing_summary(c):
    """Campos da leitura das regras que ainda faltam (nomes do JSON)."""
    return [json_name for field, json_name in SUMMARY_FIELDS if getattr(c, field) in (None, "")]


def _needs_reading(c, today):
    """Campanha ainda aberta que vale a pena completar ("não oferecer" fica de fora: a gestão já decidiu)."""
    return c.end >= today and c.approval != "recusada" and not c.do_not_offer


def receive_reading(agency, payload, now=None):
    """Grava a leitura de campanhas (campanhas + situação de cada criador). Devolve o resumo para a resposta da porta.

    - Cada campanha é achada pelo "id" do Backstage ou, sem ID, pelo nome com a data de início: reenviar não duplica.
    - Envio parcial (pedido de 26/11/2026): para campanha já gravada, basta o "id" e os campos que mudaram. Campo
      ausente ou vazio mantém o valor gravado; nunca vira vazio. Campanha nova continua precisando de nome, início e fim.
    - O que a gestão decide (foco, "não oferecer", mecânica e "premia até" já conferidos) nunca é sobrescrito: a
      leitura só preenche link, resumo, prêmios, mecânica e "premia até" quando ainda estão vazios.
    - A situação de cada criador é trocada inteira, campanha por campanha, só nas campanhas que aparecem em
      "criadores" (quem sumiu da leitura deixa de valer). Inclusões manuais da gestão ficam como estão.
    - @ que não é da agência é ignorado e contado.
    """
    now = now or timezone.now()
    today = timezone.localtime(now).date()
    if not isinstance(payload, dict) or not isinstance(payload.get("campanhas"), list):
        raise ReadingError("Envie um JSON com a lista “campanhas” (e, se tiver, “criadores”).")
    camps, rows = payload["campanhas"], payload.get("criadores") or []
    if not isinstance(rows, list):
        raise ReadingError("“criadores” precisa ser uma lista.")
    if len(camps) > MAX_CAMPAIGNS or len(rows) > MAX_STATUS_ROWS:
        raise ReadingError("Leitura grande demais para a tela de campanhas do Backstage.")
    counts = {"campanhas_novas": 0, "campanhas_atualizadas": 0, "situacoes": 0, "criadores_desconhecidos": 0, "sem_link": 0,
              "para_aprovar": 0, "posicoes": 0}
    ids = {"ids_novas": {}, "ids_para_aprovar": {}, "ids_sem_link": {}, "ids_sem_resumo": {}}  # pk -> id (sem repetir)
    with transaction.atomic():
        by_key = {}
        for raw in camps:
            if not isinstance(raw, dict):
                raise ReadingError("Toda campanha precisa de “nome”.")
            given_id = str(raw.get("id") or "").strip()[:160]
            c = Campaign.objects.filter(agency=agency, backstage_key=given_id).first() if given_id else None
            if c is None:  # campanha nova, ou enviada sem ID: nome, início e fim são obrigatórios, como sempre
                if not str(raw.get("nome") or "").strip():
                    raise ReadingError("Toda campanha precisa de “nome”.")
                name = str(raw["nome"]).strip()[:120]
                start, end = _date(raw.get("inicio"), "inicio", name), _date(raw.get("fim"), "fim", name)
                key = (given_id or f"{_norm(name)}|{start.isoformat()}")[:160]
                c = Campaign.objects.filter(agency=agency, backstage_key=key).first()
            else:  # já gravada e achada pelo ID: o que não veio fica como está
                key = given_id
                name = str(raw.get("nome") or "").strip()[:120] or c.name
                start = _date(raw["inicio"], "inicio", name) if _given(raw.get("inicio")) else c.start
                end = _date(raw["fim"], "fim", name) if _given(raw.get("fim")) else c.end
            if end < start:
                raise ReadingError(f"Campanha “{name}”: o fim vem antes do início.")
            fields = {"name": name, "start": start, "end": end, "read_at": now}
            if _given(raw.get("aba")) or c is None:
                fields["backstage_tab"] = "agencia" if _norm(raw.get("aba")) == "agencia" else "plataforma"
            if _KIND_IN.get(_norm(raw.get("tipo"))):
                fields["tiktok_kind"] = _KIND_IN[_norm(raw.get("tipo"))]
            if _given(raw.get("nivel_recomendado")):
                fields["recommended_level"] = str(raw["nivel_recomendado"]).strip()[:60]
            for json_name, field in (("participantes", "participants_n"), ("elegiveis", "eligible_n"), ("diamantes", "total_diamonds")):
                if _int(raw.get(json_name)) is not None:
                    fields[field] = _int(raw.get(json_name))
            link = _link(raw.get("link"))
            if c is None:
                c = Campaign(agency=agency, backstage_key=key, source="backstage", featured=False, published=True,
                             rules=str(raw.get("regras") or raw.get("resumo") or "")[:4000], **fields)
                if c.backstage_tab == "plataforma":  # decisão de 22/11: campanha nova do TikTok espera as sócias
                    c.approval = "aguardando"
                    counts["para_aprovar"] += 1
                c.what_to_do = str(raw.get("resumo") or "")[:1000]
                c.prizes = str(raw.get("premios") or "")[:1000]
                c.tiktok_url = link
                c.mechanic = _MECH_IN.get(_norm(raw.get("mecanica")), "")
                c.prize_until = _int(raw.get("premia_ate"))
                c.save()
                ids["ids_novas"][c.pk] = key
                if c.approval == "aguardando":
                    ids["ids_para_aprovar"][c.pk] = key
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
                ids["ids_sem_link"][c.pk] = c.backstage_key
            if _needs_reading(c, today) and missing_summary(c):
                ids["ids_sem_resumo"][c.pk] = c.backstage_key
            by_key[key] = c
            by_key.setdefault(_norm(name), c)
        # situação de cada criador em cada campanha
        from data.importer import _find_creator_by_username

        found = {}
        new_rows = {}
        new_pos = {}  # (campanha, criador) -> (posição, pontos, pontos para subir)
        in_rows = set()  # campanhas que aparecem em "criadores": só nelas a situação é trocada
        saved = {}  # envio parcial: campanha já gravada, citada em "criadores" só pelo ID
        for r in rows:
            if not isinstance(r, dict):
                continue
            ref = str(r.get("campanha") or "").strip()
            camp = by_key.get(ref) or by_key.get(_norm(ref))
            if camp is None and ref:
                if ref not in saved:
                    saved[ref] = Campaign.objects.filter(agency=agency, backstage_key=ref[:160]).first()
                camp = saved[ref]
            status = _STATUS_IN.get(_norm(r.get("situacao")))
            handle = str(r.get("usuario") or "").strip().lstrip("@")
            if camp is not None:
                in_rows.add(camp.pk)
            if camp is None or not handle:
                continue
            if status is None and _given(r.get("situacao")):
                continue  # situação que a leitura não reconhece: a linha não vale (como antes)
            if handle not in found:
                found[handle] = _find_creator_by_username(agency, handle)
            creator = found[handle]
            if creator is None:
                counts["criadores_desconhecidos"] += 1
                continue
            new_rows[(camp.pk, creator.pk)] = status
            pos = _int(re.sub(r"\D", "", str(r.get("posicao") or "")))  # aceita "8", "8º" e "#8"
            if pos:  # posição na tabela de classificação (passo 4.5): só a gestão vê
                new_pos[(camp.pk, creator.pk)] = (pos, _int(r.get("pontos")), _int(r.get("pontos_para_subir")))
        _save_positions(new_pos, set(new_rows), now)
        counts["posicoes"] = len(new_pos)
        if in_rows:  # campanha que não aparece em "criadores" fica com a situação de antes (envio parcial)
            old = CampaignParticipant.objects.filter(campaign_id__in=in_rows, from_backstage=True)
            CampaignParticipant.objects.filter(pk__in=[p.pk for p in old if (p.campaign_id, p.creator_id) not in new_rows]).delete()
            for (cid, crid), status in new_rows.items():
                if status is None:  # linha sem "situacao" (envio parcial): a situação gravada fica como está
                    continue
                obj, created = CampaignParticipant.objects.get_or_create(campaign_id=cid, creator_id=crid,
                                                                         defaults={"status": status, "from_backstage": True})
                if not created and obj.from_backstage and obj.status != status:
                    obj.status = status
                    obj.save(update_fields=["status", "updated_at"])
                counts["situacoes"] += 1
    counts.update({name: list(found_ids.values()) for name, found_ids in ids.items()})
    counts["sem_resumo"] = len(counts["ids_sem_resumo"])
    return counts


def _save_positions(new_pos, listed, now):
    """Grava a posição de cada criador, campanha por campanha. Só troca as campanhas que vieram com alguma posição
    nesta leitura (uma leitura sem a tabela de classificação não apaga as posições de antes). Na campanha trocada,
    só sai a posição de quem sumiu da leitura; quem veio sem "posicao" (`listed`) fica com a última gravada, e
    "pontos" ou "pontos_para_subir" ausentes mantêm o valor de antes. A posição anterior guardada é a do último dia
    de leitura antes de hoje, para "pode perder posição" (reenviar no mesmo dia não apaga)."""
    with_pos = {cid for cid, _ in new_pos}
    if not with_pos:
        return
    today = timezone.localtime(now).date()
    old = {(p.campaign_id, p.creator_id): p for p in CampaignPosition.objects.filter(campaign_id__in=with_pos)}
    CampaignPosition.objects.filter(pk__in=[p.pk for k, p in old.items() if k not in new_pos and k not in listed]).delete()
    for (cid, crid), (pos, pts, to_next) in new_pos.items():
        p = old.get((cid, crid))
        if p is None:
            CampaignPosition.objects.create(campaign_id=cid, creator_id=crid, position=pos, points=pts, to_next=to_next, read_at=now)
            continue
        if timezone.localtime(p.read_at).date() < today:
            p.prev_position = p.position
        p.position, p.read_at = pos, now
        p.points = p.points if pts is None else pts
        p.to_next = p.to_next if to_next is None else to_next
        p.save()


def pending(agency, today=None):
    """O que falta a leitura preencher (GET /api/importacao/campanhas/pendentes/), só de campanhas ainda abertas.

    sem_resumo: primeiro as que esperam avaliação, depois as que têm criador da Hera inscrito ou em andamento, depois as
    que terminam antes. Campanha marcada "não oferecer" fica de fora: a gestão já decidiu não usar."""
    today = today or timezone.localdate()
    camps = [c for c in Campaign.objects.filter(agency=agency, source="backstage", end__gte=today).exclude(backstage_key="")
             if _needs_reading(c, today)]
    with_hera = set(CampaignParticipant.objects.filter(campaign__in=[c.pk for c in camps], status__in=("inscrito", "andamento"))
                    .values_list("campaign_id", flat=True))
    no_summary = sorted((c for c in camps if missing_summary(c)),
                        key=lambda c: (c.approval != "aguardando", c.pk not in with_hera, c.end, c.name))
    by_end = sorted(camps, key=lambda c: (c.end, c.name))
    return {
        "sem_resumo": [{"id": c.backstage_key, "nome": c.name, "aba": c.backstage_tab, "fim": c.end.isoformat(),
                        "tem_criador_hera": c.pk in with_hera, "falta": missing_summary(c)} for c in no_summary],
        "sem_link": [{"id": c.backstage_key, "nome": c.name} for c in by_end if not c.tiktok_url],
        "novas_para_aprovar": [{"id": c.backstage_key, "nome": c.name} for c in by_end if c.approval == "aguardando"],
    }


# ---------------------------------------------------------------- avaliação da campanha nova (passo 4.5; 23/11: gestora ou sócia)
class ApprovalError(ValueError):
    pass


def waiting_approval(agency):
    return list(Campaign.objects.filter(agency=agency, approval="aguardando").order_by("end", "name"))


def recently_decided(agency, days=14):
    """As campanhas novas avaliadas nos últimos dias, com quem avaliou: as sócias acompanham pelo Painel."""
    since = timezone.now() - dt.timedelta(days=days)
    return list(Campaign.objects.filter(agency=agency, approval__in=("aprovada", "recusada"), approved_at__gte=since)
                .select_related("approved_by").order_by("-approved_at"))


def approve(campaign, user, decision, mechanic="", prize_until=None, prizes="", recommended_level="", what_to_do="", focus=False):
    """A gestora (no Dashboard) ou uma sócia (no Painel) confere os quatro campos da visão (mecânica principal, até que
    posição premia, prêmios e nível recomendado, mais o resumo para o criador) e aprova, ou decide não oferecer. Vale a
    decisão de quem avaliar primeiro. `focus`: aprovar e já pôr no foco. Quem chama confere que é gestora ou sócia."""
    if campaign.approval != "aguardando":
        raise ApprovalError("Esta campanha já foi avaliada.")
    if decision not in ("aprovar", "recusar"):
        raise ApprovalError("Escolha aprovar ou não oferecer.")
    campaign.approved_by, campaign.approved_at = user, timezone.now()
    if decision == "recusar":
        campaign.approval, campaign.do_not_offer, campaign.featured = "recusada", True, False
    else:
        campaign.approval = "aprovada"
        campaign.mechanic = mechanic if mechanic in dict(Campaign.MECHANICS) else ""
        campaign.prize_until = prize_until or None
        campaign.prizes = (prizes or "")[:1000]
        campaign.recommended_level = (recommended_level or "")[:60]
        campaign.what_to_do = (what_to_do or "")[:1000]
        if focus:
            campaign.featured, campaign.do_not_offer = True, False
    campaign.save()
    return campaign


def reopen(campaign):
    """Uma sócia reabre a avaliação: a campanha volta para "aguardando" (sai do app e do foco até nova avaliação)."""
    if campaign.approval not in ("aprovada", "recusada"):
        raise ApprovalError("Esta campanha não tem avaliação para reabrir.")
    campaign.approval, campaign.approved_by, campaign.approved_at = "aguardando", None, None
    campaign.featured = campaign.do_not_offer = False
    campaign.save()
    return campaign


# ---------------------------------------------------------------- posição: uma frase por criador, só para a gestão
def _n(x):
    return f"{int(x):,}".replace(",", ".")


def near_prize(campaign, position):
    """Na faixa premiada ou até 3 posições depois dela. Sem "premia até" conferido, não dá para saber."""
    return bool(campaign.prize_until and position and position <= campaign.prize_until + NEAR_PRIZE_POSITIONS)


def position_phrase(campaign, p):
    """"está em 8º, faltam 1.200 pontos para o 7º (premia até o 10º)". Nunca cita outro criador."""
    txt = f"está em {p.position}º"
    if p.to_next and p.position > 1:
        txt += f", faltam {_n(p.to_next)} pontos para o {p.position - 1}º"
    if campaign.prize_until:
        txt += " (na faixa premiada" if p.position <= campaign.prize_until else " (fora da faixa premiada"
        txt += f", que vai até o {campaign.prize_until}º)"
    if p.prev_position and p.position > p.prev_position:
        txt += f"; caiu do {p.prev_position}º"
    return txt


def follow_lists(agency, creator_ids, today=None):
    """As três listas do acompanhamento (visão, "Campanhas: o que a gestora acompanha"), só da carteira de quem vê.

    Ordem: a campanha que fecha primeiro, depois o @ (nunca a posição: não é ranking)."""
    today = today or E.tiktok_today()
    camps = {c.pk: c for c in Campaign.objects.filter(agency=agency, published=True, do_not_offer=False, start__lte=today,
                                                       end__gte=today).exclude(approval__in=("aguardando", "recusada"))}
    out = {"inscricao": [], "premio": [], "queda": []}
    if not camps:
        return out
    for p in (CampaignParticipant.objects.filter(campaign_id__in=camps, creator_id__in=creator_ids, status="qualifica")
              .select_related("creator")):
        out["inscricao"].append({"c": camps[p.campaign_id], "creator": p.creator, "why": "pode se inscrever e ainda não se inscreveu"})
    for p in CampaignPosition.objects.filter(campaign_id__in=camps, creator_id__in=creator_ids).select_related("creator"):
        c = camps[p.campaign_id]
        row = {"c": c, "creator": p.creator, "why": position_phrase(c, p)}
        if near_prize(c, p.position):
            out["premio"].append(row)
        if p.prev_position and p.position > p.prev_position:
            out["queda"].append(row)
    for k in out:
        out[k].sort(key=lambda r: (r["c"].end, r["c"].name, r["creator"].username))
    return out


# ---------------------------------------------------------------- acompanhamento na fila do dia (Playbook)
def checkpoints(c):
    """Agenda de uma campanha: dia seguinte à abertura, metade e véspera do fechamento (as de até 3 dias: só abertura e
    véspera). O "dia seguinte ao fim" é tratado à parte."""
    days = (c.end - c.start).days + 1
    pts = {"abertura": c.start + dt.timedelta(days=1), "vespera": c.end - dt.timedelta(days=1)}
    if days > SHORT_CAMPAIGN_DAYS:
        pts["metade"] = c.start + dt.timedelta(days=days // 2)
    return pts


def campaign_vars(c):
    """Variáveis da ROD-CAMP (campanha, resumo da regra e link)."""
    rule = (c.what_to_do or "").strip().rstrip(".")
    return {"campanha": c.name, "campanha_regra": (rule[:1].lower() + rule[1:]) if rule else "[resumo da regra]",
            "campanha_link": c.tiktok_url or "[link]"}


def _sent_since(contacts, code, date):
    return any(x.template_code == code and timezone.localtime(x.sent_at).date() >= date for x in contacts)


def queue_items(ctx):
    """Itens "campanha_*" da fila do dia. A gestora só envia a campanha do momento de cada criador (visão, "Uma campanha
    de cada vez por criador"); o que ela vê de todas as campanhas fica nas listas da tela Campanhas.

    - campanha_inscricao (ROD-CAMP): pode se inscrever e não se inscreveu, a partir do dia seguinte à abertura e de novo
      a partir da metade; sai com o "Enviei" ou quando a leitura mostrar a inscrição.
    - campanha_posicao (CAMP-POS, com a posição e os pontos preenchidos): perto de prêmio, na metade e na véspera; ou
      caiu de posição perto da faixa premiada (no máximo a cada 3 dias). Nunca no último dia (os dados atrasam de 2 a 3
      horas e a véspera é o momento de falar). Na última semana do mês, é o "Quase lá" de campanha (prioridade 1).
    - campanha_fim (APO-06): terminou até 3 posições depois da faixa premiada, nos 2 dias depois do fim.
    """
    from web.month_items import in_last_week
    from web.services import QueueItem

    today, agency, info = ctx["today"], ctx["agency"], ctx["info"]
    ids = list(info)
    camps = list(_visible_qs(agency, today))
    ended = list(Campaign.objects.filter(agency=agency, published=True, do_not_offer=False,
                                         end__gte=today - dt.timedelta(days=AFTER_END_DAYS), end__lt=today)
                 .exclude(approval__in=("aguardando", "recusada")))
    if not camps and not ended:
        return []
    picks = {p.creator_id: p for p in CampaignPick.objects.filter(creator_id__in=ids)}
    positions = {(p.campaign_id, p.creator_id): p for p in
                 CampaignPosition.objects.filter(campaign_id__in=[c.pk for c in camps + ended], creator_id__in=ids)}
    prio_pos = 1 if in_last_week(today) else 2
    out = []
    for pk, d in info.items():
        c_obj, contacts = d["c"], d["contacts"]
        pick = picks.get(pk) or False
        moment = campaign_of_the_moment(c_obj, creator_campaigns(c_obj, None, today, pick=pick, camps=camps), snaps=d["snaps"], pick=pick)
        if moment:
            it = moment["item"]
            c, status = it["c"], it["status"]
            pts = checkpoints(c)
            passed = sorted((day, name) for name, day in pts.items() if day <= today)
            stage_day, stage = passed[-1] if passed else (None, None)
            p = positions.get((c.pk, pk))
            if status == "qualifica" and stage in ("abertura", "metade") and not _sent_since(contacts, "ROD-CAMP", stage_day):
                out.append(QueueItem(c_obj, "campanha_inscricao", 2, f"Campanha: pode se inscrever em “{c.name}”",
                                     f"Campanha do momento, fecha em {c.end:%d/%m}. Ainda não se inscreveu pela leitura do Backstage. "
                                     "Envie o link e o resumo da regra.", "ROD-CAMP", vars=campaign_vars(c)))
            elif p and p.position > 1 and today < c.end and near_prize(c, p.position):
                dropped = bool(p.prev_position and p.position > p.prev_position)
                due = stage in ("metade", "vespera") and not _sent_since(contacts, "CAMP-POS", stage_day)
                due_drop = dropped and not _sent_since(contacts, "CAMP-POS", today - dt.timedelta(days=DROP_REPEAT_DAYS - 1))
                if due or due_drop:
                    when = {"metade": "metade da campanha", "vespera": "véspera do fechamento"}.get(stage, "")
                    why = "caiu de posição" if due_drop and not due else (when or "perto de prêmio")
                    out.append(QueueItem(c_obj, "campanha_posicao", prio_pos, f"Campanha: perto de prêmio em “{c.name}”",
                                         f"{why[:1].upper() + why[1:]}: {position_phrase(c, p)}. Fecha em {c.end:%d/%m}. "
                                         "Confira no TikTok antes de enviar (os dados atrasam de 2 a 3 horas) e não cite outro criador.",
                                         "CAMP-POS", vars={"_replace": {"[campanha]": c.name, "[X]": str(p.position),
                                                                        **({"[Y]": _n(p.to_next)} if p.to_next else {})}}))
        # dia seguinte ao fim: chegou perto (até 3 posições depois da faixa premiada) e não ganhou
        for c in ended:
            p = positions.get((c.pk, pk))
            if not p or not c.prize_until or not (c.prize_until < p.position <= c.prize_until + NEAR_PRIZE_POSITIONS):
                continue
            if not (c.featured or (pick and pick.campaign_id == c.pk)):
                continue  # a gestora só acompanha a campanha que ofereceu
            if _sent_since(contacts, "APO-06", c.end + dt.timedelta(days=1)):
                continue
            out.append(QueueItem(c_obj, "campanha_fim", 3, f"Campanha: chegou perto em “{c.name}”",
                                 f"Terminou em {p.position}º e a campanha premiou até o {c.prize_until}º. Mensagem 2.6 (perdeu por pouco).",
                                 "APO-06", vars={"_replace": {"[campanha]": c.name}}))
            break
    return out
