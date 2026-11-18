"""Importação das exportações do TikTok Backstage.

Fluxo: ler arquivo → detectar template → mapear colunas → validar → pré-visualizar
→ gravar (snapshot) → recalcular → (desfazer, se preciso).

Regras:
- Upsert por creator (ID do TikTok) + período. Reimportar o mesmo arquivo não duplica nada.
- Creator novo vira cadastro pendente (sem convite automático).
- Linha "O criador deixou a agência" é reconhecida pelo @ e abre registro de saída.
"""
import csv
import datetime as dt
import hashlib
import io
from decimal import Decimal

import openpyxl
from django.db import transaction
from django.utils import timezone

from core.bootstrap import REQUIRED_FIELDS
from core.models import AgencySettings, PartnerGroup
from crm.models import Creator, CreatorStatus, CreatorUsername, ExitRecord

from . import parsing as P
from .models import CreatorSnapshot, ImportBatch, ImportRow, ImportTemplate, MonthlyResult, TaskResult

LEFT_MARKER = "O criador deixou a agência"

SNAPSHOT_FIELDS = [
    "diamonds", "live_seconds", "valid_days", "new_followers", "streams",
    "lm_diamonds", "lm_live_seconds", "lm_valid_days", "lm_new_followers", "lm_streams",
    "pct_diamonds", "pct_hours", "pct_valid_days", "pct_followers", "pct_streams",
    "battles", "battle_diamonds", "guest_diamonds", "new_fans", "graduation_status", "level_status",
    "username_at", "group_name", "agent_email",
]


# ---------------------------------------------------------------- leitura
def read_table(file_bytes, filename):
    """Devolve (cabeçalhos, linhas como dict de texto)."""
    name = filename.lower()
    if name.endswith(".csv"):
        text = file_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        rows = [r for r in reader if any(c.strip() for c in r)]
    else:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.worksheets[0]
        rows = [list(r) for r in ws.iter_rows(values_only=True) if any(v not in (None, "") for v in r)]
    if not rows:
        return [], []
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    out = []
    for r in rows[1:]:
        out.append({headers[i]: (r[i] if i < len(r) else None) for i in range(len(headers)) if headers[i]})
    return headers, out


def detect_template(headers, agency):
    candidates = ImportTemplate.objects.filter(agency__isnull=True) | ImportTemplate.objects.filter(agency=agency)
    best = None
    for t in candidates.order_by("-agency_id"):
        if all(h in headers for h in t.signature):
            known = sum(1 for h in headers if h in t.column_map)
            if best is None or known > best[1]:
                best = (t, known)
    return best[0] if best else None


def build_mapping(template, headers, overrides=None):
    """Mapa cabeçalho→campo para este arquivo + campos obrigatórios faltando + colunas desconhecidas."""
    cmap = dict(template.column_map) if template else {}
    cmap.update(overrides or {})
    mapping = {h: cmap[h] for h in headers if h in cmap}
    unknown = [h for h in headers if h not in cmap]
    kind = template.kind if template else None
    mapped_fields = set(mapping.values())
    missing = [f for f in REQUIRED_FIELDS.get(kind, []) if f not in mapped_fields]
    return mapping, unknown, missing


# ---------------------------------------------------------------- parse por linha
def _by_field(raw, mapping):
    d = {}
    for h, f in mapping.items():
        if f.startswith("_"):
            continue
        d[f] = raw.get(h)
    return d


def parse_backstage_row(raw, mapping):
    r = _by_field(raw, mapping)
    tid = str(r.get("tiktok_id") or "").strip()
    status = str(r.get("status") or "").strip()
    name = str(r.get("name") or "").strip()
    if tid == LEFT_MARKER or status.lower() == "saiu":
        start, end = P.parse_period(r.get("period"))
        return {"kind": "exit", "username": name, "period_start": start, "period_end": end}
    if not tid or not tid.isdigit():
        raise P.ParseError(f"ID do criador inválido: {tid!r}")
    start, end = P.parse_period(r.get("period"))
    joined = P.utc_timestamp(r.get("joined_at")) if not P.is_empty(r.get("joined_at")) else None
    out = {
        "kind": "data",
        "tiktok_id": tid,
        "username": name,
        "group": str(r.get("group") or "").strip(),
        "agent": str(r.get("agent") or "").strip(),
        "joined_at": joined,
        "days_in_network": P.to_int(r.get("days_in_network"), None),
        "period_start": start,
        "period_end": end,
        "diamonds": P.to_int(r.get("diamonds")),
        "live_seconds": P.duration_to_seconds(r.get("live_duration")),
        "valid_days": P.to_int(r.get("valid_days")),
        "new_followers": P.to_int(r.get("new_followers")),
        "streams": P.to_int(r.get("streams")),
        "lm_diamonds": P.to_int(r.get("lm_diamonds"), None),
        "lm_live_seconds": P.duration_to_seconds(r.get("lm_live_duration")) if not P.is_empty(r.get("lm_live_duration")) else None,
        "lm_valid_days": P.to_int(r.get("lm_valid_days"), None),
        "lm_new_followers": P.to_int(r.get("lm_new_followers"), None),
        "lm_streams": P.to_int(r.get("lm_streams"), None),
        "pct_diamonds": P.pct_to_fraction(r.get("pct_diamonds")),
        "pct_hours": P.pct_to_fraction(r.get("pct_hours")),
        "pct_valid_days": P.pct_to_fraction(r.get("pct_valid_days")),
        "pct_followers": P.pct_to_fraction(r.get("pct_followers")),
        "pct_streams": P.pct_to_fraction(r.get("pct_streams")),
        "battles": P.to_int(r.get("battles")),
        "battle_diamonds": P.to_int(r.get("battle_diamonds")),
        "guest_diamonds": P.to_int(r.get("guest_diamonds")),
        "new_fans": P.to_int(r.get("new_fans"), None),
        "graduation_status": "" if P.is_empty(r.get("graduation_status")) else str(r.get("graduation_status")),
        "level_status": "" if P.is_empty(r.get("level_status")) else str(r.get("level_status")),
    }
    if end < start:
        raise P.ParseError("período com fim antes do início")
    if out["valid_days"] > (end - start).days + 1:
        raise P.ParseError("dias válidos maior que os dias do período")
    return out


def parse_task_row(raw, mapping):
    r = _by_field(raw, mapping)
    tid = str(r.get("tiktok_id") or "").strip()
    if not tid.isdigit():
        raise P.ParseError(f"Creator ID inválido: {tid!r}")
    return {
        "kind": "task",
        "tiktok_id": tid,
        "username": str(r.get("handle") or r.get("name") or "").strip(),
        "group": str(r.get("group") or "").strip(),
        "month": P.parse_task_month(r.get("month")),
        "diamonds": P.to_int(r.get("diamonds")),
        "valid_days": P.to_int(r.get("valid_days")),
        "live_hours": P.to_decimal(r.get("live_hours")) or Decimal(0),
        "violative": bool(P.to_bool(r.get("violative"))),
        "rookie": P.to_bool(r.get("rookie")),
    }


def _jsonable(d):
    out = {}
    for k, v in d.items():
        if isinstance(v, (dt.date, dt.datetime)):
            out[k] = v.isoformat()
        elif isinstance(v, Decimal):
            out[k] = str(v)
        else:
            out[k] = v
    return out


def _find_creator_by_username(agency, username):
    if not username:
        return None
    c = Creator.objects.filter(agency=agency, username__iexact=username).first()
    if c:
        return c
    u = CreatorUsername.objects.filter(creator__agency=agency, username__iexact=username).select_related("creator").first()
    return u.creator if u else None


def _snapshot_values(p):
    return {
        "diamonds": p["diamonds"], "live_seconds": p["live_seconds"], "valid_days": p["valid_days"],
        "new_followers": p["new_followers"], "streams": p["streams"],
        "lm_diamonds": p["lm_diamonds"], "lm_live_seconds": p["lm_live_seconds"], "lm_valid_days": p["lm_valid_days"],
        "lm_new_followers": p["lm_new_followers"], "lm_streams": p["lm_streams"],
        "pct_diamonds": p["pct_diamonds"], "pct_hours": p["pct_hours"], "pct_valid_days": p["pct_valid_days"],
        "pct_followers": p["pct_followers"], "pct_streams": p["pct_streams"],
        "battles": p["battles"], "battle_diamonds": p["battle_diamonds"], "guest_diamonds": p["guest_diamonds"],
        "new_fans": p["new_fans"], "graduation_status": p["graduation_status"], "level_status": p["level_status"],
        "username_at": p["username"], "group_name": p["group"], "agent_email": p["agent"],
    }


def _snapshot_to_dict(s):
    return _jsonable({f: getattr(s, f) for f in SNAPSHOT_FIELDS} | {"batch_id": s.batch_id, "exported_at": s.exported_at})


# ---------------------------------------------------------------- pré-visualização
class ImportError_(Exception):
    pass


def create_preview(agency, file_bytes, filename, user=None, mapping_overrides=None, via="tela"):
    """Monta a pré-visualização. A permissão de quem importa é conferida na tela (ou pela chave, na porta de
    importação: data/port.py); a leitura roda como sistema, porque o arquivo traz a agência inteira e a gestora
    só enxerga a própria carteira."""
    from core.rls import system_context

    with system_context():
        return _create_preview(agency, file_bytes, filename, user, mapping_overrides, via)


@transaction.atomic
def _create_preview(agency, file_bytes, filename, user=None, mapping_overrides=None, via="tela"):
    headers, rows = read_table(file_bytes, filename)
    if not headers:
        raise ImportError_("Arquivo vazio ou ilegível.")
    template = detect_template(headers, agency)
    if template is None and not mapping_overrides:
        raise ImportError_("Formato não reconhecido. Mapeie as colunas.")
    mapping, unknown, missing = build_mapping(template, headers, mapping_overrides)
    if missing:
        raise ImportError_("Colunas obrigatórias não encontradas: " + ", ".join(missing))
    kind = template.kind if template else "backstage"
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    batch = ImportBatch.objects.create(
        agency=agency, template=template, kind=kind, filename=filename, file_hash=file_hash,
        uploaded_by=user, mapping=mapping, via=via,
        exported_at=P.export_time_from_filename(filename) or timezone.now(),
    )
    counts = {"new": 0, "updated": 0, "unchanged": 0, "exit": 0, "error": 0, "skip": 0,
              "unknown_columns": unknown,
              "duplicate_of": ImportBatch.objects.filter(agency=agency, file_hash=file_hash, status="committed").exclude(pk=batch.pk).values_list("pk", flat=True).first()}
    periods = set()
    import_rows = []
    for i, raw in enumerate(rows, start=2):
        raw_s = {k: (v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v) for k, v in raw.items()}
        try:
            p = parse_backstage_row(raw, mapping) if kind == "backstage" else parse_task_row(raw, mapping)
        except P.ParseError as e:
            counts["error"] += 1
            import_rows.append(ImportRow(batch=batch, row_number=i, raw=raw_s, action="error", errors=str(e)))
            continue
        creator = None
        if p["kind"] == "exit":
            creator = _find_creator_by_username(agency, p["username"])
            action = "exit" if creator and creator.status not in (CreatorStatus.SAIU, CreatorStatus.ANONIMIZADO) else "skip"
            periods.add((p["period_start"], p["period_end"]))
        else:
            creator = Creator.objects.filter(agency=agency, tiktok_id=p["tiktok_id"]).first()
            if p["kind"] == "data":
                periods.add((p["period_start"], p["period_end"]))  # vale também para creator novo
            if creator is None:
                action = "new"
            elif p["kind"] == "data":
                snap = CreatorSnapshot.objects.filter(creator=creator, period_start=p["period_start"], period_end=p["period_end"]).first()
                if snap is None:
                    action = "updated"
                else:
                    same = all(getattr(snap, f) == v for f, v in _snapshot_values(p).items())
                    action = "unchanged" if same else "updated"
            else:
                tr = TaskResult.objects.filter(creator=creator, month=p["month"]).first()
                action = "unchanged" if tr and tr.diamonds == p["diamonds"] and tr.valid_days == p["valid_days"] else "updated"
        counts[action] += 1
        import_rows.append(ImportRow(batch=batch, row_number=i, raw=raw_s, parsed=_jsonable(p), creator=creator, action=action))
    ImportRow.objects.bulk_create(import_rows)
    if periods:
        batch.period_start = min(s for s, _ in periods)
        batch.period_end = max(e for _, e in periods)
    batch.counts = counts
    batch.save()
    return batch


# ---------------------------------------------------------------- gravar
def _partner_group(agency, name):
    if not name:
        return None
    pg, _ = PartnerGroup.objects.get_or_create(
        agency=agency, name=name,
        defaults={"is_direct": name == "Não está em um grupo", "streamer_access_enabled": name == "Não está em um grupo"},
    )
    return pg


def _touch_username(creator, username, when):
    if not username:
        return
    obj, created = CreatorUsername.objects.get_or_create(
        creator=creator, username=username, defaults={"first_seen": when, "last_seen": when}
    )
    if not created and obj.last_seen < when:
        obj.last_seen = when
        obj.save(update_fields=["last_seen"])
    if creator.username != username:
        creator.username = username
        creator.save(update_fields=["username"])


def _parsed(row, kind):
    """Re-lê a linha a partir do texto bruto (fonte da verdade)."""
    mapping = row.batch.mapping
    return parse_backstage_row(row.raw, mapping) if kind == "backstage" else parse_task_row(row.raw, mapping)


def commit(batch, recalc=True):
    """Grava o lote. A permissão de quem importa é conferida na tela; a gravação roda como sistema."""
    from core.rls import system_context

    with system_context():
        return _commit(batch, recalc)


@transaction.atomic
def _commit(batch, recalc=True):
    if batch.status != "preview":
        raise ImportError_("Este lote já foi processado.")
    agency = batch.agency
    settings_ = AgencySettings.objects.get(agency=agency)
    exported_at = batch.exported_at or timezone.now()
    touched = set()
    for row in batch.rows.exclude(action__in=["error", "skip", "unchanged"]).select_related("batch").order_by("row_number"):
        p = _parsed(row, batch.kind)
        if p["kind"] == "exit":
            creator = row.creator
            if creator is None:
                continue
            days = creator.days_in_agency(p["period_end"]) or 0
            within = days <= settings_.free_exit_days
            ex = ExitRecord.objects.create(
                creator=creator, requested_at=p["period_end"], within_free_period=within, action="detectada",
                reason="Detectada na importação do Backstage",
                return_eligible_at=p["period_end"] if within else p["period_end"] + dt.timedelta(days=settings_.return_wait_days),
                anonymize_at=p["period_end"] + dt.timedelta(days=settings_.anonymize_after_days),
            )
            row.previous = {"status": creator.status, "exit_id": ex.pk}
            row.save(update_fields=["previous"])
            creator.status = CreatorStatus.SAIU
            creator.save(update_fields=["status"])
            touched.add(creator.pk)
            continue

        creator = row.creator or Creator.objects.filter(agency=agency, tiktok_id=p["tiktok_id"]).first()
        if creator is None:
            joined = p.get("joined_at")
            if joined is None and p.get("days_in_network") is not None and p["kind"] == "data":
                joined = dt.datetime.combine(p["period_end"] - dt.timedelta(days=p["days_in_network"]), dt.time(), tzinfo=dt.timezone.utc)
            creator = Creator.objects.create(
                agency=agency, tiktok_id=p["tiktok_id"], display_name=p["username"] or p["tiktok_id"],
                username=p["username"] or p["tiktok_id"], status=CreatorStatus.PENDENTE, joined_at=joined,
                partner_group=_partner_group(agency, p.get("group")), suggested_agent_email=p.get("agent", ""),
            )
            row.previous = {"created_creator": True}
            row.creator = creator
            row.save(update_fields=["previous", "creator"])
        else:
            changed = []
            pg = _partner_group(agency, p.get("group"))
            if pg and creator.partner_group_id != pg.pk:
                creator.partner_group = pg
                changed.append("partner_group")
            if p.get("agent") and creator.suggested_agent_email != p["agent"]:
                creator.suggested_agent_email = p["agent"]
                changed.append("suggested_agent_email")
            if p.get("joined_at") and not creator.joined_at:
                creator.joined_at = p["joined_at"]
                changed.append("joined_at")
            if changed:
                creator.save(update_fields=changed)
        _touch_username(creator, p["username"], exported_at)
        touched.add(creator.pk)

        if p["kind"] == "data":
            values = _snapshot_values(p)
            existing = CreatorSnapshot.objects.filter(creator=creator, period_start=p["period_start"], period_end=p["period_end"]).first()
            if existing:
                if row.previous is None or "created_creator" not in (row.previous or {}):
                    row.previous = {"snapshot": _snapshot_to_dict(existing)}
                    row.save(update_fields=["previous"])
                for f, v in values.items():
                    setattr(existing, f, v)
                existing.batch = batch
                existing.exported_at = exported_at
                existing.save()
            else:
                CreatorSnapshot.objects.create(
                    batch=batch, agency=agency, creator=creator, period_start=p["period_start"],
                    period_end=p["period_end"], exported_at=exported_at, **values,
                )
        else:
            existing = TaskResult.objects.filter(creator=creator, month=p["month"]).first()
            if existing:
                row.previous = (row.previous or {}) | {"task": {
                    "batch_id": existing.batch_id, "diamonds": existing.diamonds, "valid_days": existing.valid_days,
                    "live_hours": str(existing.live_hours), "is_violative": existing.is_violative, "rookie_at_join": existing.rookie_at_join}}
                row.save(update_fields=["previous"])
                existing.batch = batch
                existing.diamonds, existing.valid_days, existing.live_hours = p["diamonds"], p["valid_days"], p["live_hours"]
                existing.is_violative, existing.rookie_at_join = p["violative"], p["rookie"]
                existing.save()
            else:
                TaskResult.objects.create(
                    batch=batch, creator=creator, month=p["month"], diamonds=p["diamonds"], valid_days=p["valid_days"],
                    live_hours=p["live_hours"], is_violative=p["violative"], rookie_at_join=p["rookie"],
                )
    batch.status = "committed"
    batch.committed_at = timezone.now()
    batch.save(update_fields=["status", "committed_at"])
    if recalc:
        from .engine import recalculate

        recalculate(agency, creator_ids=touched)
    return batch


# ---------------------------------------------------------------- desfazer
def revert(batch, recalc=True):
    from core.rls import system_context

    with system_context():
        return _revert(batch, recalc)


@transaction.atomic
def _revert(batch, recalc=True):
    if batch.status != "committed":
        raise ImportError_("Só é possível desfazer um lote gravado.")
    touched = set()
    created_creators = []
    for row in batch.rows.exclude(action__in=["error", "skip", "unchanged"]).order_by("-row_number"):
        prev = row.previous or {}
        if row.creator_id:
            touched.add(row.creator_id)
        if "exit_id" in prev:
            ExitRecord.objects.filter(pk=prev["exit_id"]).delete()
            Creator.objects.filter(pk=row.creator_id).update(status=prev["status"])
            continue
        if "snapshot" in prev:
            s = prev["snapshot"]
            snap = CreatorSnapshot.objects.filter(batch=batch, creator_id=row.creator_id).first()
            if snap:
                for f in SNAPSHOT_FIELDS:
                    val = s.get(f)
                    field = CreatorSnapshot._meta.get_field(f)
                    setattr(snap, f, field.to_python(val) if val is not None else None)
                snap.batch_id = s["batch_id"]
                snap.exported_at = dt.datetime.fromisoformat(s["exported_at"])
                snap.save()
        if "task" in prev:
            t = prev["task"]
            TaskResult.objects.filter(batch=batch, creator_id=row.creator_id).update(
                batch_id=t["batch_id"], diamonds=t["diamonds"], valid_days=t["valid_days"],
                live_hours=Decimal(t["live_hours"]), is_violative=t["is_violative"], rookie_at_join=t["rookie_at_join"])
        if prev.get("created_creator"):
            created_creators.append(row.creator_id)
    # O que sobrou ligado a este lote foi criado por ele.
    CreatorSnapshot.objects.filter(batch=batch).delete()
    TaskResult.objects.filter(batch=batch).delete()
    for cid in created_creators:
        c = Creator.objects.filter(pk=cid).first()
        if c and not c.snapshots.exists() and not c.task_results.exists() and c.user_id is None:
            touched.discard(cid)
            c.delete()
    batch.status = "reverted"
    batch.reverted_at = timezone.now()
    batch.save(update_fields=["status", "reverted_at"])
    if recalc:
        from .engine import recalculate

        recalculate(batch.agency, creator_ids=touched)
    return batch
