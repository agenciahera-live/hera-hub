"""Motor de fases e radar de graduação (passo 2.3)."""
import datetime as dt

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.models import AgencySettings
from core.rls import set_context, system_context
from crm.models import Contact, Creator
from data import phases
from data.models import MonthlyResult

from . import factories as F

# As fábricas contam a entrada a partir de 28/09/2026 (joined_days_ago=0 → D1 em 28/09).
HOJE = dt.date(2026, 9, 28)
SET = (dt.date(2026, 9, 1), dt.date(2026, 9, 27))


class MotorDeFasesTests(TestCase):
    def setUp(self):
        set_context(system=True)
        self.ag = F.agency()
        self.st = AgencySettings.objects.get(agency=self.ag)

    def tearDown(self):
        set_context()

    def _fase(self, c, **kw):
        return phases.phase_for(Creator.objects.get(pk=c.pk), settings_=self.st, today=HOJE, **kw)

    def test_chegada_ate_o_primeiro_contato(self):
        c = F.creator(self.ag, joined_days_ago=1)
        f = self._fase(c)
        self.assertEqual((f.code, f.day, f.label), ("chegada", 2, "Chegada"))
        Contact.objects.create(creator=c, template_code="ONB-D1-01", body="oi")
        self.assertEqual(self._fase(c).code, "novato")

    def test_novato_ate_fechar_a_regra_ou_chegar_ao_d15(self):
        c = F.creator(self.ag, joined_days_ago=5)
        F.snapshot(c, *SET, hours=3, valid_days=1, streams=1)
        f = self._fase(c)
        self.assertEqual((f.code, f.day), ("novato", 6))
        self.assertIn("regra do TikTok", f.detail)
        fechou = F.creator(self.ag, joined_days_ago=9)
        F.snapshot(fechou, *SET, hours=16, valid_days=5, streams=6)
        self.assertEqual(self._fase(fechou).code, "primeiro_mes")  # fechou 5 dias e 15h antes do D15
        d15 = F.creator(self.ag, joined_days_ago=14)
        F.snapshot(d15, *SET, hours=3, valid_days=1, streams=1)
        self.assertEqual(self._fase(d15).code, "primeiro_mes")  # chegou ao D15 sem fechar

    def test_primeiro_mes_graduacao_e_veterano_pelo_tempo_de_casa(self):
        casos = {19: "primeiro_mes", 29: "primeiro_mes", 30: "graduacao", 89: "graduacao", 90: "veterano", 300: "veterano"}
        for dias, esperado in casos.items():
            c = F.creator(self.ag, joined_days_ago=dias)
            F.snapshot(c, *SET, diamonds=1000, hours=20, valid_days=8, streams=9)
            self.assertEqual(self._fase(c).code, esperado, dias)

    def test_pausa_fica_por_cima_da_fase_da_jornada(self):
        c = F.creator(self.ag, joined_days_ago=200)
        F.snapshot(c, dt.date(2026, 9, 1), dt.date(2026, 9, 24), hours=10, valid_days=5, streams=5)
        F.snapshot(c, *SET, hours=10, valid_days=5, streams=5)  # 3 dias sem LIVE
        self.assertEqual(self._fase(c).code, "veterano")
        self.st.pause_after_days = 3  # o limite é configurável
        f = self._fase(c)
        self.assertEqual((f.code, f.base, f.base_label), ("pausa", "veterano", "Veterano"))
        self.assertIn("Sem LIVE há 3 dias", f.detail)

    def test_quem_nunca_abriu_live_depois_do_d14_e_quem_esta_saindo(self):
        nunca = F.creator(self.ag, joined_days_ago=20)
        f = self._fase(nunca)
        self.assertEqual((f.code, f.base), ("pausa", "primeiro_mes"))
        self.assertIn("nunca abriu LIVE", f.detail)
        aviso = F.creator(self.ag, joined_days_ago=200, status="em_saida")
        self.assertEqual(self._fase(aviso).code, "pausa")
        saiu = F.creator(self.ag, joined_days_ago=200, status="saiu")
        self.assertEqual(self._fase(saiu).code, "saida")

    # ------------------------------------------------------------ radar
    def _radar(self, c):
        c = Creator.objects.get(pk=c.pk)
        return phases.graduation_radar_row(c, list(c.snapshots.all()), self.st, HOJE)

    def test_radar_de_graduacao_le_o_mes_corrente(self):
        acelerar = F.creator(self.ag, joined_days_ago=40)
        F.snapshot(acelerar, *SET, diamonds=60_000)
        r = self._radar(acelerar)
        self.assertEqual((r.status, r.diamonds, r.missing, r.last_month), ("acelerar", 60_000, 20_000, False))
        self.assertAlmostEqual(r.avg_per_day, 60_000 / 27, places=1)
        self.assertAlmostEqual(r.needed_per_day, 20_000 / 3, places=1)
        ritmo = F.creator(self.ag, joined_days_ago=40)
        F.snapshot(ritmo, *SET, diamonds=78_000)
        self.assertEqual(self._radar(ritmo).status, "no_ritmo")
        graduou = F.creator(self.ag, joined_days_ago=40)
        F.snapshot(graduou, *SET, diamonds=85_000)
        self.assertEqual(self._radar(graduou).status, "graduou")
        sem = F.creator(self.ag, joined_days_ago=40)
        self.assertEqual(self._radar(sem).status, "no_radar")  # sem LIVE na semana
        self.assertIsNone(self._radar(F.creator(self.ag, joined_days_ago=200)))  # fora da janela

    def test_radar_marca_o_ultimo_mes_e_conta_graduacoes_anteriores(self):
        c = F.creator(self.ag, joined_days_ago=88)  # entrou em 02/07: a janela de 90 dias termina em 29/09
        F.snapshot(c, *SET, diamonds=30_000)
        MonthlyResult.objects.create(creator=c, month=dt.date(2026, 8, 1), diamonds=90_000, source="backstage", tier=3)
        MonthlyResult.objects.create(creator=c, month=dt.date(2026, 7, 1), diamonds=20_000, source="backstage", tier=1)
        r = self._radar(c)
        self.assertEqual((r.last_month, r.graduations, r.window_end), (True, 1, dt.date(2026, 9, 29)))


class TelasDeFaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        hoje = dt.date.today()
        agora = timezone.now()
        cls.janela = F.creator(cls.ag, username="janela.demo")
        cls.vet = F.creator(cls.ag, username="vet.demo")
        cls.alheio = F.creator(cls.ag, username="alheio.demo")
        Creator.objects.filter(pk__in=[cls.janela.pk, cls.alheio.pk]).update(joined_at=agora - dt.timedelta(days=40))
        for c in (cls.janela, cls.vet, cls.alheio):
            F.snapshot(c, hoje.replace(day=1), hoje, diamonds=85_000, hours=30, valid_days=10, streams=12)
        assign_manager(cls.janela, cls.gx)
        assign_manager(cls.vet, cls.gx)
        assign_manager(cls.alheio, cls.gy)
        set_context()

    def tearDown(self):
        set_context()

    def test_radar_lista_fica_na_carteira_e_aparece_na_ficha(self):
        self.client.force_login(self.gx)
        tela = self.client.get(reverse("g_graduation"))
        self.assertContains(tela, "Radar de graduação")
        self.assertContains(tela, "janela.demo")
        self.assertContains(tela, "Bateu a marca no mês")
        self.assertNotContains(tela, "vet.demo")  # fora da janela
        self.assertNotContains(tela, "alheio.demo")  # de outra carteira
        ficha = self.client.get(reverse("g_creator", args=[self.janela.pk]))
        self.assertContains(ficha, "Fase: Graduação")
        self.assertContains(ficha, "Ver o radar de graduação")
        self.assertContains(self.client.get(reverse("g_creator", args=[self.vet.pk])), "Fase: Veterano")

    def test_lista_de_creators_mostra_e_filtra_por_fase(self):
        self.client.force_login(self.gx)
        tela = self.client.get("/gestao/creators/")
        self.assertContains(tela, "Graduação")
        self.assertContains(tela, "Veterano")
        so_vet = self.client.get("/gestao/creators/?fase=veterano")
        self.assertContains(so_vet, "vet.demo")
        self.assertNotContains(so_vet, "janela.demo")
        self.assertContains(self.client.get("/gestao/creators/?fase=veterano&export=csv"), "Veterano")

    def test_tela_do_criador_mostra_os_grupos_da_configuracao(self):
        u = F.user()
        with system_context():
            c = F.creator(self.ag, username="grupos.demo", streamer_user=u)
        self.client.force_login(u)
        tela = self.client.get(reverse("my_level"))  # no app, o criador vê "Nível" no lugar de "Tier"
        for texto in ["Bronze", "Nível 1", "Prata", "Nível 2 a 3", "Ouro", "Nível 4", "Diamante", "Nível 5 ou mais"]:
            self.assertContains(tela, texto)
        self.assertNotContains(tela, "Tier")
