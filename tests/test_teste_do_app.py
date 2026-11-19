"""Teste do app com poucos criadores (etapa 3, passo 3.7).

Decisões da Mariana de 19/11/2026: 5 criadores escolhidos por ela; de 2 semanas a 1 mês; pesquisa identificada no fim.
O que se confere: o registro de uso (um dia e uma área por dia), a tela só das sócias, a trava do código de acesso
e a pesquisa só para quem participa."""
import datetime as dt

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.models import AgencySettings, AppEvent
from core.rls import set_context, system_context
from crm import first_access
from crm.models import Creator
from engage.models import Course, Lesson, Survey
from engage.tom import verificar_tom
from web import app_test

from . import factories as F


class TesteDoAppTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.admin = F.user(role="admin", ag=cls.ag)
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        cls.u1, cls.u2 = F.user(), F.user()
        cls.c1 = F.creator(cls.ag, username="um.demo", streamer_user=cls.u1)
        cls.c2 = F.creator(cls.ag, username="dois.demo", streamer_user=cls.u2)
        cls.c3 = F.creator(cls.ag, username="tres.demo")  # ainda sem login
        for c in (cls.c1, cls.c2, cls.c3):
            assign_manager(c, cls.gestora)
        co = Course.objects.create(agency=cls.ag, title="1. Começar", opens_on="acesso")
        cls.aula = Lesson.objects.create(course=co, title="Abrir a LIVE", video_url="https://example.com/v")
        set_context()

    def tearDown(self):
        set_context()

    def _admin_post(self, **data):
        self.client.force_login(self.admin)
        return self.client.post(reverse("g_app_test"), data, follow=True)

    # ------------------------------------------------------------ uso do app
    def test_uso_conta_um_dia_e_cada_area_uma_vez_por_dia(self):
        self.client.force_login(self.u1)
        for url in ["/", "/", reverse("academy"), reverse("lesson", args=[self.aula.pk]), reverse("my_plan")]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        with system_context():
            eventos = list(AppEvent.objects.filter(user=self.u1).values_list("event", flat=True))
        self.assertEqual(eventos.count("app_open"), 1)
        self.assertEqual(sorted(e for e in eventos if e != "app_open"),
                         ["area:Hera Academy", "area:Meu plano", "area:Meu progresso"])

    # ------------------------------------------------------------ tela das sócias
    def test_so_as_socias_abrem_a_tela(self):
        self.client.force_login(self.gestora)
        self.assertNotEqual(self.client.get(reverse("g_app_test")).status_code, 200)
        self.client.force_login(self.admin)
        r = self.client.get(reverse("g_app_test"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ninguém no teste ainda")

    def test_colocar_e_tirar_do_teste_pelo_arroba(self):
        r = self._admin_post(a="add", handle="@UM.demo")
        self.assertContains(r, "@um.demo entrou no teste do app.")
        self.assertTrue(self._tester(self.c1))
        r = self._admin_post(a="add", handle="ninguem.demo")
        self.assertContains(r, "Não achei um criador ativo com o @ninguem.demo.")
        self._admin_post(a="remove", creator=self.c1.pk)
        self.assertFalse(self._tester(self.c1))

    def _tester(self, c):
        with system_context():
            return Creator.objects.get(pk=c.pk).app_tester

    def test_tabela_mostra_dias_e_areas(self):
        self._admin_post(a="add", handle="um.demo")
        self._admin_post(a="add", handle="tres.demo")
        self.client.force_login(self.u1)
        self.client.get("/")
        self.client.get(reverse("battles"))
        with system_context():
            rows = {r["c"].username: r for r in app_test.tester_rows(self.ag)}
        self.assertEqual(rows["um.demo"]["days_week"], 1)
        self.assertEqual(rows["um.demo"]["areas_week"], ["Meu progresso", "Batalhas"])
        self.assertFalse(rows["tres.demo"]["has_login"])
        self.client.force_login(self.admin)
        r = self.client.get(reverse("g_app_test"))
        self.assertContains(r, "1</b> de 2 já entraram no app")
        self.assertContains(r, "sem código")

    def test_datas_invertidas_nao_salvam(self):
        hoje = timezone.localdate()
        r = self._admin_post(a="dates", start=hoje.isoformat(), end=(hoje - dt.timedelta(days=1)).isoformat())
        self.assertContains(r, "O fim do teste precisa ser depois do início.")
        with system_context():
            self.assertIsNone(AgencySettings.objects.get(agency=self.ag).app_test_start)

    # ------------------------------------------------------------ trava do código de acesso
    def test_trava_so_quem_participa_recebe_codigo(self):
        hoje = timezone.localdate()
        self._admin_post(a="dates", start=hoje.isoformat(), end=(hoje + dt.timedelta(days=14)).isoformat(), only_testers="on")
        self._admin_post(a="add", handle="tres.demo")
        with system_context():
            st = AgencySettings.objects.get(agency=self.ag)
            self.assertTrue(st.app_test_only_testers)
            c2, c3 = Creator.objects.get(pk=self.c2.pk), Creator.objects.get(pk=self.c3.pk)
            with self.assertRaises(first_access.AccessError):
                first_access.new_code(c2)
            self.assertTrue(first_access.new_code(c3).code)
        # a ficha avisa em vez de mostrar o botão
        self.client.force_login(self.gestora)
        r = self.client.get(reverse("g_creator", args=[self.c2.pk]))
        self.assertContains(r, "só quem participa recebe código de acesso")
        self.assertNotContains(r, "Gerar código de acesso")
        r = self.client.post(reverse("g_access_code", args=[self.c2.pk]), follow=True)
        self.assertContains(r, "Durante o teste do app")
        self.assertContains(self.client.get(reverse("g_creator", args=[self.c3.pk])), "no teste do app")

    def test_trava_desligada_nao_muda_nada(self):
        with system_context():
            self.assertTrue(first_access.new_code(Creator.objects.get(pk=self.c2.pk)).code)

    # ------------------------------------------------------------ pesquisa do fim do teste
    def test_pesquisa_identificada_so_para_quem_participa(self):
        self._admin_post(a="add", handle="um.demo")
        r = self._admin_post(a="survey")
        self.assertContains(r, "Pesquisa do fim do teste criada.")
        self._admin_post(a="survey")
        with system_context():
            self.assertEqual(Survey.objects.filter(agency=self.ag, only_app_testers=True).count(), 1)
            sv = Survey.objects.get(agency=self.ag, only_app_testers=True)
            self.assertFalse(sv.anonymous)
            self.assertEqual(sv.questions.count(), 5)
            sv.opens_at = timezone.now() - dt.timedelta(minutes=1)
            sv.save()
        self.client.force_login(self.u1)
        self.assertContains(self.client.get("/"), "Pesquisa")
        self.assertEqual(self.client.get(reverse("survey", args=[sv.pk])).status_code, 200)
        self.client.force_login(self.u2)  # não participa
        self.assertEqual(self.client.get(reverse("survey", args=[sv.pk])).status_code, 404)

    def test_textos_da_pesquisa_sem_palavra_vetada(self):
        textos = [app_test.SURVEY_TITLE, app_test.SURVEY_INTRO] + [q for _, q, opts in app_test.SURVEY_QUESTIONS] + \
                 [o for _, _, opts in app_test.SURVEY_QUESTIONS for o in opts]
        for t in textos:
            self.assertEqual(verificar_tom(t), [], t)
