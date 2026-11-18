"""Porta de importação: recebe o arquivo da leitura diária do Backstage sem login (visão, "Dados e integrações").

Quem envia é o Claude, que lê o Backstage no computador da agência. A chave identifica a agência.
O arquivo passa pelo MESMO importador da tela (data/importer.py): mesma validação e mesmo "desfazer".

Diferença para a tela: aqui ninguém olha a pré-visualização antes de gravar. Por isso a porta só grava
sozinha quando a leitura está limpa. Com linha com erro, saídas demais ou período estranho, o lote fica em
pré-visualização, a gestão é avisada e alguém confere e confirma na tela (Importar dados).

Tudo roda como sistema (core.rls.system_context): a chave vale pela agência inteira, como a rotina diária.
"""
import hashlib
import logging
import secrets
from dataclasses import dataclass

from django.utils import timezone

from core.models import AgencySettings, AuditLog, Membership
from core.rls import system_context

from . import importer
from .engine import tiktok_today
from .models import ImportBatch, ImportKey

logger = logging.getLogger(__name__)

PREFIX = "hera_"
MAX_BYTES = 20 * 1024 * 1024  # a planilha do Backstage tem poucas centenas de KB
NOTIFY_ROLES = ["admin", "gestora"]
ONLY_BACKSTAGE = ("A porta recebe só a planilha “Dados do criador”. A planilha Task do fechamento "
                  "é enviada pela tela, pelas sócias ou pelo financeiro.")
UNREADABLE = "Arquivo ilegível. Envie a planilha .xlsx ou .csv exportada do Backstage, sem alterar."


# ---------------------------------------------------------------- chave
def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def active_key(agency):
    return ImportKey.objects.filter(agency=agency, revoked_at__isnull=True).first()


def revoke_key(agency):
    return ImportKey.objects.filter(agency=agency, revoked_at__isnull=True).update(revoked_at=timezone.now())


def new_key(agency, by=None):
    """Gera a chave da agência e cancela a anterior. Devolve o texto da chave: é a única vez em que ele existe."""
    revoke_key(agency)
    token = PREFIX + secrets.token_urlsafe(32)
    ImportKey.objects.create(agency=agency, key_hash=_hash(token), hint=token[:9], created_by=by)
    return token


def key_for_token(token):
    """Chave ativa que corresponde ao texto recebido (ou None)."""
    token = (token or "").strip()
    if not token.startswith(PREFIX):
        return None
    key = ImportKey.objects.filter(key_hash=_hash(token), revoked_at__isnull=True).select_related("agency").first()
    if key:
        ImportKey.objects.filter(pk=key.pk).update(last_used_at=timezone.now())
    return key


# ---------------------------------------------------------------- recebimento
@dataclass
class Result:
    status: str  # gravado | repetido | conferir | recusado
    message: str
    batch: ImportBatch = None

    @property
    def ok(self):
        return self.status in ("gravado", "repetido")

    @property
    def http_status(self):
        return 200 if self.ok else 422

    def as_dict(self):
        d = {"ok": self.ok, "situacao": self.status, "mensagem": self.message}
        b = self.batch
        if b is not None:
            d.update({
                "lote": b.pk,
                "periodo_inicio": b.period_start.isoformat() if b.period_start else None,
                "periodo_fim": b.period_end.isoformat() if b.period_end else None,
            })
            if self.status != "repetido":  # no repetido, o lote é o antigo: a contagem dele só confundiria
                c = b.counts or {}
                d.update({"novos": c.get("new", 0), "atualizados": c.get("updated", 0), "sem_mudanca": c.get("unchanged", 0),
                          "saidas": c.get("exit", 0), "erros": c.get("error", 0)})
        return d


def _notify(agency, title, body, url):
    """Avisa as sócias e as gestoras no app (uma vez por dia por título, enquanto o aviso não for lido)."""
    from engage.models import Notification
    from engage.services import notify

    today = timezone.localdate()
    for m in Membership.objects.filter(agency=agency, role__in=NOTIFY_ROLES, active=True).select_related("user"):
        repeated = Notification.objects.filter(user=m.user, kind="dados", title=title, read_at__isnull=True,
                                               created_at__date=today).exists()
        if not repeated:
            notify(user=m.user, kind="dados", title=title, body=body[:500], url=url)


def _refuse(agency, reason):
    _notify(agency, "A leitura automática do Backstage foi recusada", f"{reason} Plano B: suba a planilha pela tela.",
            "/gestao/importar/")
    return Result("recusado", reason)


def _problems(batch, settings_):
    """Motivos para NÃO gravar sozinho (lista vazia = leitura limpa)."""
    c = batch.counts
    out = []
    if c["new"] + c["updated"] + c["unchanged"] == 0:
        out.append("nenhuma linha válida no arquivo")
    if c["error"]:
        out.append(f"{c['error']} linha{'s' if c['error'] > 1 else ''} com erro")
    if c["exit"] > settings_.auto_import_max_exits:
        out.append(f"{c['exit']} saídas detectadas de uma vez (acima de {settings_.auto_import_max_exits}, alguém precisa conferir)")
    if batch.period_end and batch.period_end > tiktok_today():
        out.append("o período dos dados termina no futuro")
    return out


def receive(agency, data, filename):
    """Recebe o arquivo da leitura automática. Grava se estiver limpo; senão segura para conferência ou recusa."""
    with system_context():
        try:
            importer.read_table(data, filename)
        except Exception as e:  # qualquer falha ao abrir = não é a planilha (zip quebrado, texto em outra codificação...)
            logger.warning("Porta de importação: arquivo ilegível (%s): %s", filename, type(e).__name__)
            return _refuse(agency, UNREADABLE)
        try:
            batch = importer.create_preview(agency, data, filename, via="porta")
        except importer.ImportError_ as e:
            return _refuse(agency, str(e))
        if batch.kind != "backstage":
            batch.delete()
            return _refuse(agency, ONLY_BACKSTAGE)
        original = batch.counts.get("duplicate_of")
        if original:
            batch.delete()
            return Result("repetido", "Este arquivo já tinha sido importado. Nada mudou.", ImportBatch.objects.filter(pk=original).first())
        problems = _problems(batch, AgencySettings.objects.get(agency=agency))
        if problems:
            why = "; ".join(problems)
            batch.counts = {**batch.counts, "held": problems}
            batch.save(update_fields=["counts"])
            _notify(agency, "A leitura automática do Backstage ficou para conferência",
                    f"Motivo: {why}. Confira e confirme em Importar dados.", f"/gestao/importar/{batch.pk}/")
            return Result("conferir", f"Leitura recebida, mas não gravada: {why}. A gestão foi avisada para conferir na tela.", batch)
        importer.commit(batch)
        AuditLog.objects.create(agency=agency, action="importacao_automatica", target=f"lote {batch.pk}",
                                detail={k: batch.counts.get(k, 0) for k in ("new", "updated", "unchanged", "exit", "error")})
        return Result("gravado", "Leitura gravada. Os números do app e da fila já estão atualizados.", batch)
