"""1:1 com o modelo novo (etapa 4, passo 4.2).

Decisão da Mariana de 19/11/2026: o print não é enviado ao app; a gestora guarda no drive dela e marca que guardou.
Confere: cabeçalho (canal e quem conduziu), bloco 1 automático, anotações, o que conta como completo, a agenda e o
item "1:1 do mês" na fila."""
import datetime as dt

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from crm import one_on_one
from crm.models import ActionItem, Creator, OneOnOne
from data import engine as E
from data.models import MonthlyResult
from data.states import analysed_sunday
from web.services import action_queue

from . import factories as F


class UmAUmTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gestora = F.user(role="gestora", ag=cls.ag, first_name="Ana")
        cls.admin = F.user(role="admin", ag=cls.ag, first_name="Mari")
        cls.u_stream = F.user()
        cls.dia = F.creator(cls.ag, username="diamante.demo", streamer_user=cls.u_stream)
        cls.comum = F.creator(cls.ag, username="comum.demo")
        for c in (cls.dia, cls.comum):
            assign_manager(c, cls.gestora)
        today = E.tiktok_today()
        for m in {E.prev_month(today), E.prev_month(analysed_sunday(today))}:
            MonthlyResult.objects.create(creator=cls.dia, month=m, diamonds=300_000, live_seconds=80 * 3600, valid_days=20, source="task", tier=5)
            MonthlyResult.objects.create(creator=cls.comum, month=m, diamonds=2_000, live_seconds=3 * 3600, valid_days=2, source="task", tier=1)
        cls.today = today
        set_context()

    def tearDown(self):
        set_context()

    def _registrar(self, **extra):
        data = {"date": timezone.localdate().isoformat(), "channel": "video", "conducted_by": self.admin.pk,
                "b1": "Números", "b2": "Rotina", "b3": "Cenário", "b4": "Campanha", "b5": "Nada", "b7": (timezone.localdate() + dt.timedelta(days=30)).isoformat(),
                "action1": "Testar co-host", "owner1": "criador", "action2": "Mandar a aula", "owner2": "gestora",
                "notes": "Falou da viagem.", "print_saved": "on"}
        data.update(extra)
        self.client.force_login(self.gestora)
        return self.client.post(reverse("g_1a1", args=[self.dia.pk]), {k: v for k, v in data.items() if v is not None}, follow=True)

    # ------------------------------------------------------------ registro
    def test_registro_completo_com_canal_condutor_anotacoes_e_print(self):
        r = self._registrar()
        self.assertContains(r, "1:1 registrado.")
        self.assertNotContains(r, "registro incompleto")
        with system_context():
            o = OneOnOne.objects.get(creator=self.dia)
            self.assertEqual((o.channel, o.conducted_by_id, o.notes, o.print_saved, o.manager_id),
                             ("video", self.admin.pk, "Falou da viagem.", True, self.gestora.pk))
            self.assertTrue(o.complete)
        self.assertContains(r, "print guardado no drive")
        self.assertContains(r, "Falou da viagem.")

    def test_sem_print_ou_com_uma_acao_fica_incompleto(self):
        r = self._registrar(print_saved=None, action2=None)
        self.assertContains(r, "registro incompleto, falta 6. Plano (2 ações ou mais), print guardado")
        with system_context():
            self.assertFalse(OneOnOne.objects.get(creator=self.dia).complete)

    def test_bloco_1_preenchido_pelo_sistema(self):
        m0, pm = E.month_start(self.today), E.prev_month(self.today)
        day = max(self.today.day - 1, 1)
        F.snapshot(self.dia, pm, pm.replace(day=day), diamonds=100_000, hours=30, valid_days=10, streams=10, battles=20)
        F.snapshot(self.dia, m0, m0.replace(day=day), diamonds=120_000, hours=32, valid_days=11, streams=11, battles=25)
        with system_context():
            texto = one_on_one.performance_text(Creator.objects.get(pk=self.dia.pk), self.today)
        self.assertIn("120.000 diamantes, 32,0h de LIVE, 11 dias válidos e 25 batalhas", texto)
        self.assertIn("No mesmo ponto do mês passado", texto)
        self.assertIn("(+20% em diamantes)", texto)
        self.assertIn("Mês passado fechado: 300.000 diamantes", texto)
        self.assertNotIn("meta", texto)

    # ------------------------------------------------------------ agenda e fila
    def test_agenda_mostra_quem_precisa_de_1a1_todo_mes(self):
        self.client.force_login(self.gestora)
        r = self.client.get(reverse("g_1a1_agenda"))
        self.assertContains(r, "@diamante.demo")
        self.assertContains(r, "grupo Diamante")
        self.assertContains(r, "nunca teve 1:1 completo")
        self.assertNotContains(r, "@comum.demo</b></a></td>")
        self._registrar()
        r = self.client.get(reverse("g_1a1_agenda"))
        self.assertContains(r, "em dia")

    def test_1a1_completo_antigo_fica_atrasado(self):
        with system_context():
            o = OneOnOne.objects.create(creator=self.dia, manager=self.gestora, channel="audio", print_saved=True,
                                        date=timezone.localdate() - dt.timedelta(days=40), b1_performance="a", b2_constancia="b",
                                        b3_qualidade="c", b4_monetizacao="d", b5_dificuldades="e",
                                        b7_next_date=timezone.localdate() + dt.timedelta(days=3))
            for i in range(2):
                ActionItem.objects.create(one_on_one=o, creator=self.dia, action=f"a{i}", owner="x", due_date=timezone.localdate())
            ag = one_on_one.agenda(Creator.objects.filter(pk=self.dia.pk), self.ag)
        self.assertEqual(ag["monthly"][0]["status"], "atrasado")
        self.assertEqual(ag["scheduled"][0]["c"].pk, self.dia.pk)

    def test_fila_traz_1a1_do_mes_so_sem_1a1_marcado(self):
        if self.today.weekday() == 6:
            self.skipTest("domingo: a fila não traz tarefas")
        with system_context():
            codes = {(i.creator.username, i.code) for i in action_queue(Creator.objects.filter(agency=self.ag), self.ag, raw=True)}
        self.assertIn(("diamante.demo", "1a1_mes"), codes)
        self.assertNotIn(("comum.demo", "1a1_mes"), codes)
        self._registrar()  # 1:1 completo com o próximo marcado: sai da fila
        with system_context():
            codes = {(i.creator.username, i.code) for i in action_queue(Creator.objects.filter(agency=self.ag), self.ag, raw=True)}
        self.assertNotIn(("diamante.demo", "1a1_mes"), codes)

    def test_criador_nao_abre_a_agenda(self):
        self.client.force_login(self.u_stream)
        self.assertNotEqual(self.client.get(reverse("g_1a1_agenda")).status_code, 200)
