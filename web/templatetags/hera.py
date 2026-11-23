from zoneinfo import ZoneInfo

from django import template

register = template.Library()
SP = ZoneInfo("America/Sao_Paulo")


@register.simple_tag
def edit_reasons():
    """Motivos da mensagem editada (decisão de 23/11, 1-B: opcional), para a caixa de edição."""
    from crm.models import Contact

    return Contact.EDIT_REASONS


@register.filter
def intbr(v):
    try:
        return f"{int(round(float(v))):,}".replace(",", ".")
    except OverflowError:  # infinito (ex.: quanto precisa por dia quando o mês já acabou)
        return "—"
    except (TypeError, ValueError):
        return v


@register.filter
def pct(v, digits=0):
    try:
        return f"{float(v) * 100:.{int(digits)}f}%".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


@register.filter
def div(v, d):
    """v ÷ d (para porcentagens na tela); — quando não dá para dividir."""
    try:
        return float(v) / float(d) if float(d) else None
    except (TypeError, ValueError):
        return None


@register.filter
def signed_pct(v):
    try:
        f = float(v) * 100
        return f"{'+' if f >= 0 else ''}{f:.0f}%"
    except (TypeError, ValueError):
        return "—"


@register.filter
def hours(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    return (f"{f:.1f}".rstrip("0").rstrip(".")).replace(".", ",")


@register.filter
def secs_hours(v):
    return hours((v or 0) / 3600)


@register.filter
def width(v):
    try:
        return f"{max(0.0, min(float(v), 1.0)) * 100:.0f}%"
    except (TypeError, ValueError):
        return "0%"


@register.filter
def sp(dt, fmt="%d/%m às %H:%M"):
    if not dt:
        return ""
    return dt.astimezone(SP).strftime(fmt).replace(":", "h", 1) if "%H:%M" in fmt else dt.astimezone(SP).strftime(fmt)


@register.filter
def get(d, k):
    try:
        return d.get(k)
    except AttributeError:
        return None


@register.filter
def source_label(v):
    return {"tiktok": "TikTok", "padrao": "padrão Hera"}.get(v, v)
