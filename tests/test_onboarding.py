"""Quadro de onboarding (passo 2.5): relógio de quem entrou e não abriu LIVE, conferências, trava da não-resposta."""
import datetime as dt

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from crm.models import Contact, Creator, Reply
from engage.models import Notification
from web import services as S

from . import factories as F

HOJE = dt.date(2026, 9, 28)  # as fábricas contam a entrada a partir daqui: joined_days_ago=0 → D1


class OnboardingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.g = F.user(role="gestora", ag=cls.ag)
        cls.rec = F.user(role="recrutadora", ag=cls.ag, first_name="Fernanda")
        cls.admin = F.user(role="admin", ag=cls.ag)
        set_context()

    def tearDown(self):
        set_context()

    def _novato(self, dia, **kw):
        with system_context():
            c = F.creator(self.ag, joined_days_ago=dia - 1, **kw)
            assign_manager(c, self.g)
        return c

    def _passo(self, c, today=HOJE):
        """Próximo passo do roteiro para o criador (sem as regras de teto e de uma mensagem por dia)."""
        with system_context():
            itens = S.action_queue(Creator.objects.filter(pk=c.pk), self.ag, today=today, raw=True)
        return [i for i in itens if S.item_kind(i.code) in ("onboarding", "onboarding_risco", "cadencia")]

    def _enviei(self, c, code, quando):
        with system_context():
            Contact.objects.create(creator=c, user=self.g, template_code=code, body="x",
                                   sent_at=timezone.make_aware(dt.datetime.combine(quando, dt.time(10, 0))))

    def _com_live(self, c, fim, dias_validos, horas):
        with system_context():
            F.snapshot(c, dt.date(2026, 9, 1), fim, diamonds=500, hours=horas, valid_days=dias_validos, streams=dias_validos)

    # ------------------------------------------------------------ entrou e ainda não abriu LIVE
    def test_relogio_de_quem_ainda_nao_abriu_live(self):
        esperado = {1: ("onboarding_d1", "ONB-D1-01"), 2: ("onboarding_d2", "ONB-D2-04"), 3: ("onboarding_d2", "ONB-D2-04"),
                    5: ("onboarding_nl5", "ONB-NL-D5"), 7: ("onboarding_nl7", "ONB-NL-D7"), 9: ("onboarding_nl7", "ONB-NL-D7"),
                    10: ("onboarding_nl10", "ONB-NL-D10"), 12: ("onboarding_encerrar", "ONB-NL-ENC")}
        for dia, (codigo, modelo) in esperado.items():
            passo = self._passo(self._novato(dia))[0]
            self.assertEqual((passo.code, passo.template, passo.block), (codigo, modelo, 2), dia)
            self.assertTrue(passo.title.startswith(f"D{dia} ·"), passo.title)
        self.assertIn("aprovação das sócias", self._passo(self._novato(12))[0].detail)  # encerramento só com as sócias

    def test_d3_sem_data_combinada_depois_da_regra_enviada(self):
        c = self._novato(3)
        self._enviei(c, "ONB-D2-04", dt.date(2026, 9, 27))
        with system_context():
            Reply.objects.create(creator=c, kind="respondeu")  # respondeu: a cadência não entra
        # o D3 usa a mensagem de apoio do roteiro (a mesma de quando a LIVE combinada não acontece)
        self.assertEqual([(i.code, i.template) for i in self._passo(c)], [("onboarding_nl3", "DES-D1-04")])

    def test_d5_cita_quem_recrutou_e_a_rotina_avisa_recrutadora_e_socias(self):
        d5 = self._novato(5, recruited_by=self.rec)
        self.assertIn("acione quem recrutou: Fernanda", self._passo(d5)[0].detail)
        # a rotina diária usa a data real: recoloca a entrada para hoje ser o D5 e o D10
        agora = timezone.now()
        d10 = self._novato(1)
        with system_context():
            Creator.objects.filter(pk=d5.pk).update(joined_at=agora - dt.timedelta(days=4))
            Creator.objects.filter(pk=d10.pk).update(joined_at=agora - dt.timedelta(days=9))
        call_command("rotina_diaria", verbosity=0)
        with system_context():
            self.assertEqual(Notification.objects.filter(user=self.rec, kind="onboarding").count(), 1)
            self.assertEqual(Notification.objects.filter(user=self.admin, kind="onboarding").count(), 1)

    def test_data_combinada_que_passou_sem_live(self):
        c = self._novato(4, first_live_planned=dt.date(2026, 9, 27))
        self.assertEqual([(i.code, i.template) for i in self._passo(c)], [("onboarding_datapassou", "DES-D1-04")])
        self._enviei(c, "DES-D1-04", dt.date(2026, 9, 27))
        with system_context():
            Reply.objects.create(creator=c, kind="respondeu")
        self.assertEqual([(i.code, i.template) for i in self._passo(c)], [("onboarding_tudobem", "DES-D1-05")])
        # data combinada que ainda não chegou: a regra dos 14 dias vai do mesmo jeito; depois, só o convite para o app
        futuro = self._novato(2, first_live_planned=dt.date(2026, 9, 30))
        self.assertEqual([(i.code, i.template) for i in self._passo(futuro)], [("onboarding_d2", "ONB-D2-04")])
        self._enviei(futuro, "ONB-D2-04", dt.date(2026, 9, 28))
        with system_context():
            Reply.objects.create(creator=futuro, kind="respondeu")
        self.assertEqual([i.code for i in self._passo(futuro)], ["onboarding_app"])

    def test_gestora_registra_a_data_combinada_na_ficha(self):
        c = self._novato(2)
        self.client.force_login(self.g)
        self.client.post(reverse("g_creator_action", args=[c.pk]), {"a": "profile", "first_live_planned": "2026-09-30"})
        with system_context():
            self.assertEqual(Creator.objects.get(pk=c.pk).first_live_planned, dt.date(2026, 9, 30))
        self.assertContains(self.client.get(reverse("g_creator", args=[c.pk])), "1ª LIVE combinada para 30/09")

    # ------------------------------------------------------------ trava da não-resposta
    def test_sem_resposta_e_sem_live_a_cadencia_entra_sozinha(self):
        c = self._novato(2)
        self._enviei(c, "ONB-D1-01", dt.date(2026, 9, 27))
        passos = self._passo(c)
        self.assertEqual([(i.code, i.template) for i in passos if i.code == "cadencia"], [("cadencia", "NR-24H")])
        self._enviei(c, "NR-24H", dt.date(2026, 9, 28))
        self.assertEqual([i.template for i in self._passo(c) if i.code == "cadencia"], ["NR-2D"])  # etapa seguinte
        # "Respondeu" encerra a cadência e libera o passo seguinte (convite para o app)
        self.client.force_login(self.g)
        self.client.post(reverse("g_creator_action", args=[c.pk]), {"a": "responded"})
        codigos = [i.code for i in self._passo(c)]
        self.assertNotIn("cadencia", codigos)

    def test_live_depois_da_mensagem_tambem_encerra_a_cadencia(self):
        c = self._novato(4)
        self._enviei(c, "DES-D1-01", dt.date(2026, 9, 26))
        self.assertIn("cadencia", [i.code for i in self._passo(c)])
        self._com_live(c, dt.date(2026, 9, 27), 1, 2)  # o dado confirma: houve LIVE depois da mensagem
        self.assertNotIn("cadencia", [i.code for i in self._passo(c)])

    # ------------------------------------------------------------ quem já abriu LIVE
    def test_conferencias_de_quem_ja_abriu_live(self):
        d3 = self._novato(3)
        self._com_live(d3, dt.date(2026, 9, 27), 1, 2)
        passo = self._passo(d3)[0]
        self.assertEqual((passo.code, passo.template), ("onboarding_conf3", ""))
        self.assertIn("1 de 5 dias válidos e 2 de 15h", passo.detail)
        fechou = self._novato(9)
        self._com_live(fechou, dt.date(2026, 9, 27), 5, 16)
        self.assertEqual([(i.code, i.template) for i in self._passo(fechou)], [("onboarding_fechou", "META-D14")])
        d15 = self._novato(15)
        self._com_live(d15, dt.date(2026, 9, 27), 5, 16)
        self._enviei(d15, "META-D14", dt.date(2026, 9, 25))
        with system_context():
            Reply.objects.create(creator=d15, kind="respondeu")
        self.assertEqual([(i.code, i.template) for i in self._passo(d15)], [("onboarding_d15", "TIER-D15")])
        risco = self._novato(11)
        self._com_live(risco, dt.date(2026, 9, 27), 2, 4)
        self.assertEqual([(i.code, i.template) for i in self._passo(risco)], [("onboarding_risco", "META-D10-RISCO")])

    def test_d10_ao_d15_seguem_o_playbook(self):
        """D10: no caminho com 3 dias válidos ou mais; "uma ajudinha" com 0 a 2. D12: reforço, ou transparência com 0 a 2 dias
        e sem LIVE desde o D10. D14 sem fechar: acolhimento. D15 sem fechar: encerramento com as sócias."""
        casos = [
            (10, dt.date(2026, 9, 27), 3, 8, ("onboarding_d10", "META-D10")),
            (10, dt.date(2026, 9, 27), 2, 4, ("onboarding_risco", "META-D10-RISCO")),
            (12, dt.date(2026, 9, 27), 3, 8, ("onboarding_risco", "META-D12")),
            (12, dt.date(2026, 9, 20), 1, 2, ("onboarding_risco", "META-D12-TRANSP")),  # última LIVE antes do D10
            (12, dt.date(2026, 9, 27), 1, 2, ("onboarding_risco", "META-D12")),          # fez LIVE depois do D10: reforço
            (14, dt.date(2026, 9, 27), 3, 8, ("onboarding_acolher", "META-D14-NAO")),
            (15, dt.date(2026, 9, 27), 3, 8, ("onboarding_encerrar15", "ONB-D15-ENC")),
        ]
        for dia, ultima_live, dias_validos, horas, esperado in casos:
            c = self._novato(dia)
            self._com_live(c, ultima_live, dias_validos, horas)
            if ultima_live < dt.date(2026, 9, 27):  # leitura mais recente, sem LIVE nova
                self._com_live(c, dt.date(2026, 9, 27), dias_validos, horas)
            passos = [(i.code, i.template) for i in self._passo(c)]
            self.assertEqual(passos, [esperado], (dia, dias_validos))
        encerrar = next(i for i in self._passo(c))
        self.assertIn("aprovação das sócias", encerrar.detail)

    def test_quadro_mostra_o_proximo_passo(self):
        agora = timezone.now()
        c = self._novato(1)
        with system_context():
            Creator.objects.filter(pk=c.pk).update(joined_at=agora - dt.timedelta(days=6), username="quadro.demo")
        self.client.force_login(self.g)
        tela = self.client.get("/gestao/onboarding/")
        self.assertContains(tela, "Próximo passo")
        self.assertContains(tela, "sem LIVE: transparência sobre a contagem do TikTok")
        self.assertContains(tela, "sem LIVE")
