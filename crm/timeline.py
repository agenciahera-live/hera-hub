"""Linha do tempo da ficha: tudo o que foi enviado, respondido, anotado e registrado sobre um criador,
em ordem, com data e autor (visão, princípio 8: nada é sobrescrito).

Só leitura: junta os registros das tabelas internas. Só a gestão vê.
"""
import datetime as dt
from dataclasses import dataclass

from django.utils import timezone


@dataclass
class Entry:
    when: dt.datetime
    icon: str
    title: str
    detail: str = ""
    author: object = None


def _at(d):
    """Data sem hora vira meio-dia local, só para ordenar junto com os horários."""
    if isinstance(d, dt.datetime):
        return d
    return timezone.make_aware(dt.datetime.combine(d, dt.time(12, 0)))


def _name(user):
    return (user.first_name or user.email) if user else ""


def timeline(creator, limit=60):
    out = []
    for x in creator.contacts.select_related("user")[:limit]:
        out.append(Entry(x.sent_at, "📤", f"Enviei: {x.template_code or 'mensagem livre'}", x.body, x.user))
    for x in creator.replies.select_related("author")[:limit]:
        out.append(Entry(x.created_at, "💬", x.get_kind_display(), x.note, x.author))
    for x in creator.notes.select_related("author")[:limit]:
        out.append(Entry(x.created_at, "📝", "Nota", x.body, x.author))
    for x in creator.one_on_ones.select_related("manager")[:limit]:
        out.append(Entry(_at(x.date), "🤝", "1:1 registrado" + ("" if x.complete else " (incompleto)"), x.b1_performance, x.manager))
    for x in creator.stop_reasons.select_related("author")[:limit]:
        title = f"Motivo de quem parou: {x.get_reason_display()}" + (f" ({x.get_detail_display()})" if x.detail else "")
        detail = " ".join(p for p in [f"Volta em {x.return_date:%d/%m/%Y}." if x.return_date else "", x.note] if p)
        out.append(Entry(x.created_at, "⏸️", title, detail, x.author))
    for x in creator.reminders.select_related("author", "done_by")[:limit]:
        out.append(Entry(x.created_at, "⏰", f"Lembrete para {x.due_date:%d/%m}", x.text, x.author))
        if x.done_at:
            out.append(Entry(x.done_at, "✅", "Lembrete concluído", x.text, x.done_by))
    for x in creator.battle_records.select_related("author")[:limit]:
        placar = f" · {x.diamonds} x {x.opponent_diamonds} 💎" if x.diamonds is not None and x.opponent_diamonds is not None else ""
        out.append(Entry(x.created_at, "⚔️", f"Batalha de {x.date:%d/%m}: {x.get_result_display()}{placar}",
                         " ".join(p for p in [f"Oponente: {x.opponent}." if x.opponent else "", x.note] if p), x.author))
    for x in creator.exits.all()[:limit]:
        out.append(Entry(_at(x.requested_at), "🚪", f"Saída: {x.get_action_display()}",
                         " ".join(p for p in [x.get_reason_code_display() if x.reason_code else "", x.reason] if p)))
    for x in creator.visits.select_related("author")[:limit]:
        out.append(Entry(_at(x.date), "👀", f"Visita à LIVE: nota {x.score}", x.note, x.author))
    for x in creator.account_cases.select_related("author", "resolved_by")[:limit]:
        out.append(Entry(_at(x.opened_on), "⚠️", f"{x.get_kind_display()} na conta: caso aberto", x.note, x.author))
        if x.escalated_at:
            out.append(Entry(x.escalated_at, "⚠️", f"{x.get_kind_display()} na conta: subiu para as sócias"))
        if x.resolved_at:
            out.append(Entry(x.resolved_at, "✅", f"{x.get_kind_display()} na conta: caso encerrado", x.resolution, x.resolved_by))
    for x in creator.dismissals.select_related("by")[:limit]:
        if x.reason:
            out.append(Entry(x.created_at, "⏭️", f"Item da fila adiado até {timezone.localtime(x.until):%d/%m}", x.reason, x.by))
    # troca de carteira: o histórico do criador vai junto, e a troca fica registrada aqui
    moves = list(creator.assignments.select_related("manager", "assigned_by").order_by("valid_from")[:limit])
    for n, x in enumerate(moves):
        prev = moves[n - 1] if n else None
        out.append(Entry(x.valid_from, "🗂️", f"Carteira: {_name(x.manager)}",
                         f"Antes: {_name(prev.manager)}." if prev else "", x.assigned_by))
        nxt = moves[n + 1] if n + 1 < len(moves) else None
        if x.valid_to and (nxt is None or nxt.valid_from > x.valid_to):
            out.append(Entry(x.valid_to, "🗂️", "Carteira: sem gestora", f"Saiu da carteira de {_name(x.manager)}."))
    for x in creator.approvals.select_related("requested_by", "decided_by")[:limit]:  # pedidos de decisão às sócias (passo 4.1)
        out.append(Entry(x.requested_at, "🗳️", f"Pedido às sócias: {x.get_kind_display().lower()}", x.note or x.reason, x.requested_by))
        if x.decided_at:
            out.append(Entry(x.decided_at, "🗳️", f"Decisão das sócias: {x.decision_label}", x.decision_note, x.decided_by))
    for x in creator.risk_signals.select_related("author")[:limit]:  # sinais de risco pela conversa (passo 4.3)
        out.append(Entry(x.created_at, "🚩", f"Sinal de risco: {x.get_kind_display().lower()}", x.note, x.author))
    for x in creator.access_codes.select_related("created_by")[:limit]:
        out.append(Entry(x.created_at, "🔑", "Código de acesso ao app gerado", "", x.created_by))
        if x.used_at:
            out.append(Entry(x.used_at, "📱", "Entrou no app com o código"))
    for e in out:
        e.author_name = _name(e.author)
    out.sort(key=lambda e: e.when, reverse=True)
    return out[:limit]
