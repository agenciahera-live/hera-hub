"""Rotina diária (agendar no Railway: todo dia às 06:00 de Brasília).

    python manage.py rotina_diaria

- publica avisos agendados e notifica o público;
- recalcula grupos (fim do Primeiro Mês, virada do mês) e o progresso das campanhas;
- conclui saídas cujo aviso prévio terminou;
- anonimiza dados pessoais de quem saiu há mais tempo que o configurado (LGPD);
- avisa as sócias (admin) e a gestão quando a importação diária está atrasada;
- cria os lembretes que cada criador ligou no Meu plano (engage/plan.py);
- tira o retrato da fila de cada gestora e, na segunda, sorteia 5 "Enviei" para as sócias (web/panel.py).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Agency, AgencySettings, AuditLog, Membership
from core.rls import system_context
from crm.models import Creator, CreatorPrivate, CreatorStatus, ExitRecord
from data.engine import recalculate
from engage import plan as plan_rules
from engage.models import Announcement
from engage.services import notify, publish_announcement
from web import month_items, month_summary, panel
from web.services import data_freshness


class Command(BaseCommand):
    help = "Rotina diária do Hera Creator Hub."

    def handle(self, *args, **opts):
        today = timezone.localdate()
        with system_context():
            for ag in Agency.objects.all():
                st = AgencySettings.objects.get(agency=ag)
                for ann in Announcement.objects.filter(agency=ag, notified=False, publish_at__lte=timezone.now()):
                    publish_announcement(ann)
                for ex in ExitRecord.objects.filter(creator__agency=ag, creator__status=CreatorStatus.EM_SAIDA, notice_ends_at__lte=today):
                    ex.creator.status = CreatorStatus.SAIU
                    ex.creator.save(update_fields=["status"])
                for ex in ExitRecord.objects.filter(creator__agency=ag, creator__status=CreatorStatus.SAIU, anonymize_at__lte=today):
                    c = ex.creator
                    c.display_name = f"Ex-creator {c.pk}"
                    c.bio = ""
                    c.status = CreatorStatus.ANONIMIZADO
                    c.user = None
                    c.save()
                    CreatorPrivate.objects.filter(creator=c).update(whatsapp="", email="")
                    c.notes.all().delete()
                    plan_rules.forget(c)  # Meu plano: dias e objetivos escritos pelo criador
                    AuditLog.objects.create(agency=ag, action="anonimizacao_lgpd", target=f"creator {c.pk}")
                # entrou e ainda não abriu LIVE: no D5 avisa quem recrutou; no D10 avisa as sócias (visão, "Regras de contato")
                for c in Creator.objects.filter(agency=ag, first_live_at__isnull=True, joined_at__isnull=False,
                                                status__in=[CreatorStatus.PENDENTE, CreatorStatus.CONVIDADO, CreatorStatus.ATIVO]):
                    day = c.days_in_agency(today)
                    if day == 5 and c.recruited_by_id:
                        notify(user_id=c.recruited_by_id, kind="onboarding", url=f"/gestao/creators/{c.pk}/",
                               title=f"@{c.username} está no D5 e ainda não abriu LIVE", body="A gestão pede a sua ajuda para entender o motivo.")
                    elif day == 10:
                        for m in Membership.objects.filter(agency=ag, role="admin", active=True):
                            notify(user=m.user, kind="onboarding", url=f"/gestao/creators/{c.pk}/",
                                   title=f"@{c.username} está no D10 e nunca abriu LIVE",
                                   body="Hoje é o último dia para fechar os 5 dias válidos. Encerramento até o D14 depende da aprovação das sócias.")
                # cadência de não-resposta: no dia seguinte ao +5 dias sem resposta, avisa quem recrutou (Playbook)
                from crm.models import Contact, Reply

                for ct in Contact.objects.filter(creator__agency=ag, template_code="NR-5D", sent_at__gte=timezone.now() - timezone.timedelta(hours=48),
                                                 sent_at__lt=timezone.now() - timezone.timedelta(hours=24)).select_related("creator"):
                    c = ct.creator
                    if c.recruited_by_id and not Reply.objects.filter(creator=c, created_at__gte=ct.sent_at).exists():
                        notify(user_id=c.recruited_by_id, kind="cadencia", url=f"/gestao/creators/{c.pk}/",
                               title=f"@{c.username} está sem responder à gestão há 5 dias", body="A gestão pede a sua ajuda para retomar o contato.")
                # restrição ou banimento sem solução no 4º dia (configurável): sobe para as sócias
                from crm.models import AccountCase

                for case in AccountCase.objects.filter(creator__agency=ag, resolved_at__isnull=True, escalated_at__isnull=True).select_related("creator"):
                    if case.days_open(today) >= st.restriction_escalate_days:
                        case.escalated_at = timezone.now()
                        case.save(update_fields=["escalated_at"])
                        for m in Membership.objects.filter(agency=ag, role="admin", active=True):
                            notify(user=m.user, kind="restricao", url=f"/gestao/creators/{case.creator_id}/",
                                   title=f"{case.get_kind_display()} na conta de @{case.creator.username}: dia {case.days_open(today)} sem solução",
                                   body="O caso subiu para as sócias. Veja a ficha.")
                recalculate(ag)
                # Meu plano: os lembretes que cada criador ligou, no sininho do app (passo 3.6)
                plan_rules.daily_reminders(ag, today)
                # painel das sócias (passo 4.1): retrato da fila de cada gestora e, na segunda, o sorteio de 5 "Enviei"
                panel.snapshot_queue(ag, today)
                if today.weekday() == 0:
                    panel.ensure_draw(ag, today)
                # sinais de risco dos criadores Diamante (passo 4.3): dois ou mais avisam as sócias
                month_items.notify_risks(ag)
                # resumo do mês no app: nos dias 2 e 3, avisa o criador no sininho que o resumo chegou
                month_summary.notify_ready(ag)
                fresh = data_freshness(ag)
                if fresh is None or (timezone.now() - fresh).days >= st.stale_data_days:
                    for m in Membership.objects.filter(agency=ag, role__in=["admin", "gestora"], active=True):
                        notify(user=m.user, kind="dados", title="Importação do Backstage atrasada", url="/gestao/importar/")
        self.stdout.write(self.style.SUCCESS("Rotina diária concluída."))
