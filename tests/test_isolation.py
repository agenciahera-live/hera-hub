"""Isolamento de dados aplicado NO BANCO (RLS) e na aplicação."""
import datetime as dt

from django.db import connection
from django.test import TestCase

from core.access import assign_manager, scoped_creators
from core.rls import as_user, set_context, system_context
from crm.models import Creator, Note
from data.models import CreatorSnapshot
from engage.models import Notification

from . import factories as F


class DatabaseIsolationTests(TestCase):
    """Estes testes consultam o ORM SEM nenhum filtro de aplicação: só o RLS protege."""

    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.ua, cls.ub = F.user(), F.user()
        cls.a = F.creator(cls.ag, username="streamer.a", streamer_user=cls.ua)
        cls.b = F.creator(cls.ag, username="streamer.b", streamer_user=cls.ub)
        cls.c = F.creator(cls.ag, username="streamer.c")
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        cls.admin = F.user(role="admin", ag=cls.ag)
        assign_manager(cls.a, cls.gx)
        assign_manager(cls.b, cls.gy)
        assign_manager(cls.c, cls.gy)
        for cr in (cls.a, cls.b):
            F.snapshot(cr, dt.date(2026, 9, 1), dt.date(2026, 9, 7), diamonds=1000, hours=5, valid_days=3)
            Note.objects.create(creator=cr, body="nota interna")
        set_context()

    def tearDown(self):
        set_context()

    def test_anonymous_sees_nothing(self):
        set_context()
        self.assertEqual(Creator.objects.count(), 0)
        self.assertEqual(CreatorSnapshot.objects.count(), 0)

    def test_streamer_a_sees_only_own_creator_and_snapshots(self):
        with as_user(self.ua):
            self.assertEqual(list(Creator.objects.values_list("username", flat=True)), ["streamer.a"])
            self.assertEqual(CreatorSnapshot.objects.count(), 1)
            self.assertFalse(Creator.objects.filter(pk=self.b.pk).exists())
            self.assertFalse(CreatorSnapshot.objects.filter(creator_id=self.b.pk).exists())

    def test_streamer_never_reads_internal_notes_even_own(self):
        with as_user(self.ua):
            self.assertEqual(Note.objects.count(), 0)

    def test_campaign_position_only_for_staff_and_written_only_by_the_reading(self):
        """Passo 4.5: a posição na campanha é só da gestão; o criador nunca lê, nem a dele; só a leitura grava."""
        from django.db import DatabaseError, transaction
        from django.utils import timezone

        from engage.models import Campaign, CampaignPosition

        with system_context():
            camp = Campaign.objects.create(agency=self.ag, name="Campanha isolamento", rules="-", start=dt.date(2026, 9, 1),
                                           end=dt.date(2026, 9, 30))
            CampaignPosition.objects.create(campaign=camp, creator=self.a, position=8, read_at=timezone.now())
            CampaignPosition.objects.create(campaign=camp, creator=self.b, position=3, read_at=timezone.now())
            camp2 = Campaign.objects.create(agency=self.ag, name="Outra", rules="-", start=dt.date(2026, 9, 1), end=dt.date(2026, 9, 30))
        with as_user(self.ua):
            self.assertEqual(CampaignPosition.objects.count(), 0)  # nem a própria
        with as_user(self.gx):
            self.assertEqual(list(CampaignPosition.objects.values_list("creator__username", flat=True)), ["streamer.a"])
            self.assertEqual(CampaignPosition.objects.filter(creator=self.a).update(position=1), 0)  # a gestão não edita
            with self.assertRaises(DatabaseError), transaction.atomic():
                CampaignPosition.objects.create(campaign=camp2, creator=self.a, position=2, read_at=timezone.now())  # nem da carteira dela
        with as_user(self.admin):
            self.assertEqual(CampaignPosition.objects.count(), 2)

    def test_streamer_cannot_write_other_creator(self):
        with as_user(self.ua):
            updated = Creator.objects.filter(pk=self.b.pk).update(display_name="hack")
            self.assertEqual(updated, 0)
        with system_context():
            self.assertNotEqual(Creator.objects.get(pk=self.b.pk).display_name, "hack")

    def test_streamer_cannot_insert_note(self):
        from django.db import transaction
        from django.db.utils import ProgrammingError, DatabaseError

        with as_user(self.ua):
            with self.assertRaises(DatabaseError):
                with transaction.atomic():
                    Note.objects.create(creator_id=self.a.pk, body="x")

    def test_gestora_x_sees_only_her_portfolio(self):
        with as_user(self.gx):
            self.assertEqual(set(Creator.objects.values_list("username", flat=True)), {"streamer.a"})
            self.assertEqual(Note.objects.count(), 1)
        with as_user(self.gy):
            self.assertEqual(set(Creator.objects.values_list("username", flat=True)), {"streamer.b", "streamer.c"})

    def test_portfolio_change_moves_visibility(self):
        with system_context():
            assign_manager(Creator.objects.get(pk=self.c.pk), self.gx)
        with as_user(self.gy):
            self.assertFalse(Creator.objects.filter(pk=self.c.pk).exists())
        with as_user(self.gx):
            self.assertTrue(Creator.objects.filter(pk=self.c.pk).exists())

    def test_admin_sees_all(self):
        with as_user(self.admin):
            self.assertEqual(Creator.objects.count(), 3)

    def test_other_agency_admin_sees_nothing(self):
        with system_context():
            other = F.agency(slug="outra")
        adm2 = F.user(role="admin", ag=other)
        with as_user(adm2):
            self.assertEqual(Creator.objects.count(), 0)

    def test_notifications_are_private(self):
        with system_context():
            Notification.objects.create(user=self.ub, kind="x", title="só do B")
        with as_user(self.ua):
            self.assertEqual(Notification.objects.count(), 0)
        with as_user(self.ub):
            self.assertEqual(Notification.objects.count(), 1)

    def test_app_role_is_not_superuser(self):
        with connection.cursor() as cur:
            cur.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            self.assertEqual(cur.fetchone(), (False, False))

    def test_creator_who_left_cannot_enter_the_app(self):
        """Quem saiu (saiu/anonimizado) perde o acesso na hora; em aviso prévio ainda entra."""
        with system_context():
            Creator.objects.filter(pk=self.a.pk).update(status="saiu")
        self.client.force_login(self.ua)
        for url in ["/", "/desempenho/", "/campanhas/", "/academy/", "/duvidas/", "/batalhas/nova/", "/boas-vindas/"]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 403, url)
            self.assertContains(r, "Seu acesso foi encerrado", status_code=403)
        with system_context():
            Creator.objects.filter(pk=self.a.pk).update(status="em_saida")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_exit_registered_in_first_15_days_blocks_access(self):
        import django.utils.timezone as tz

        with system_context():
            Creator.objects.filter(pk=self.a.pk).update(joined_at=tz.now() - dt.timedelta(days=5))
        self.client.force_login(self.gx)
        self.client.post(f"/gestao/creators/{self.a.pk}/acao/", {"a": "exit", "reason_code": "trabalho_estudo", "reason": "sem tempo"})
        with system_context():
            self.assertEqual(Creator.objects.get(pk=self.a.pk).status, "saiu")
        self.client.force_login(self.ua)
        self.assertEqual(self.client.get("/").status_code, 403)

    def test_access_code_is_readable_only_by_who_edits_the_creator(self):
        """Código de acesso ao app: só as sócias e a gestora da carteira leem. Nem o próprio criador."""
        from crm import first_access as FA
        from crm.models import AccessCode

        with system_context():
            FA.new_code(Creator.objects.get(pk=self.a.pk))
            Creator.objects.filter(pk=self.a.pk).update(recruited_by=self.gy)
        recrutadora, analista = F.user(role="recrutadora", ag=self.ag), F.user(role="analista", ag=self.ag)
        with system_context():
            Creator.objects.filter(pk=self.a.pk).update(recruited_by=recrutadora)
        for quem in (self.ua, self.ub, self.gy, recrutadora, analista):
            with as_user(quem):
                self.assertEqual(AccessCode.objects.count(), 0, quem)
        set_context()
        self.assertEqual(AccessCode.objects.count(), 0)  # anônimo
        for quem in (self.gx, self.admin):
            with as_user(quem):
                self.assertEqual(AccessCode.objects.count(), 1, quem)

    def test_scoped_creators_mirrors_rls(self):
        with as_user(self.gx):
            self.assertEqual(list(scoped_creators(self.gx).values_list("username", flat=True)), ["streamer.a"])
