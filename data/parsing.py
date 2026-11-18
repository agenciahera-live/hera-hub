"""Conversões dos formatos de exportação do TikTok (tudo vem como texto)."""
import datetime as dt
import re
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

UTC = dt.timezone.utc
SP = ZoneInfo("America/Sao_Paulo")

EMPTY = {"", "-", "--", "—", "n/a", "N/A", None}


class ParseError(ValueError):
    pass


def is_empty(v):
    return v is None or (isinstance(v, str) and v.strip() in EMPTY)


_DUR = re.compile(r"^\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m(?:in)?)?\s*(?:(\d+)\s*s)?\s*$", re.I)


def duration_to_seconds(v):
    """'90h 2m 52s' → 324172; '59m 31s' → 3571; '0s' → 0; também aceita número de horas (Task)."""
    if is_empty(v):
        return 0
    if isinstance(v, (int, float, Decimal)):
        return int(round(float(v) * 3600))
    s = str(v).strip()
    m = _DUR.match(s)
    if not m or not any(m.groups()):
        try:
            return int(round(float(s.replace(",", ".")) * 3600))
        except ValueError:
            raise ParseError(f"duração ilegível: {v!r}")
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se


def pct_to_fraction(v):
    """'48.81%' → Decimal('0.4881'); '-100.00%' → -1; '-' → None."""
    if is_empty(v):
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v))
    s = str(v).strip().replace(",", ".")
    if not s.endswith("%"):
        raise ParseError(f"percentual ilegível: {v!r}")
    try:
        return (Decimal(s[:-1]) / Decimal(100)).quantize(Decimal("0.000001"))
    except InvalidOperation:
        raise ParseError(f"percentual ilegível: {v!r}")


def to_int(v, default=0):
    if is_empty(v):
        return default
    if isinstance(v, (int, float, Decimal)):
        return int(v)
    s = str(v).strip().replace(".", "").replace(",", "") if re.fullmatch(r"[\d.,]+", str(v).strip()) else str(v).strip()
    try:
        return int(float(s))
    except ValueError:
        raise ParseError(f"número ilegível: {v!r}")


def to_decimal(v):
    if is_empty(v):
        return None
    try:
        return Decimal(str(v).replace(",", "."))
    except InvalidOperation:
        raise ParseError(f"número ilegível: {v!r}")


def to_bool(v):
    if is_empty(v):
        return None
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"sim", "yes", "true", "1", "verdadeiro"}


_TS = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}(?::\d{2})?)\s*(?:\(UTC([+-]\d{1,2})(?::?(\d{2}))?\))?\s*$")


def utc_timestamp(v):
    """'2025-05-02 04:07:59 (UTC+0)' → datetime aware em UTC."""
    if is_empty(v):
        return None
    if isinstance(v, dt.datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    m = _TS.match(str(v))
    if not m:
        raise ParseError(f"data/hora ilegível: {v!r}")
    date_s, time_s, off_h, off_m = m.groups()
    fmt = "%Y-%m-%d %H:%M:%S" if time_s.count(":") == 2 else "%Y-%m-%d %H:%M"
    naive = dt.datetime.strptime(f"{date_s} {time_s}", fmt)
    offset = dt.timedelta(hours=int(off_h or 0), minutes=int(off_m or 0) * (1 if not off_h or int(off_h) >= 0 else -1))
    return naive.replace(tzinfo=dt.timezone(offset)).astimezone(UTC)


def to_sao_paulo(d):
    return d.astimezone(SP) if d else None


def parse_period(v):
    """'2026-05-01 ~ 2026-05-19' → (date(2026,5,1), date(2026,5,19))."""
    if is_empty(v):
        raise ParseError("período vazio")
    parts = [p.strip() for p in str(v).split("~")]
    if len(parts) != 2:
        raise ParseError(f"período ilegível: {v!r}")
    try:
        return dt.date.fromisoformat(parts[0]), dt.date.fromisoformat(parts[1])
    except ValueError:
        raise ParseError(f"período ilegível: {v!r}")


def parse_task_month(v):
    """'202606' → date(2026, 6, 1)."""
    s = str(v).strip()
    if not re.fullmatch(r"\d{6}", s):
        raise ParseError(f"mês ilegível: {v!r}")
    return dt.date(int(s[:4]), int(s[4:]), 1)


_FNAME = re.compile(r"(\d{4})_(\d{2})_(\d{2})[ _](\d{2})_(\d{2})(?:_(\d{2}))?\s*UTC([+-]\d+)?")


def export_time_from_filename(name):
    """'Dados do criador 2026_05_20 10_05 UTC+0.xlsx' → datetime UTC (quando houver)."""
    m = _FNAME.search(name or "")
    if not m:
        return None
    y, mo, d, h, mi, s, off = m.groups()
    naive = dt.datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0))
    return naive.replace(tzinfo=dt.timezone(dt.timedelta(hours=int(off or 0)))).astimezone(UTC)
