"""Indique e ganhe (etapa 4, passo 4.7, parte 1; regulamento de novembro de 2026; decisões da Mariana de 22/11/2026).

Registro pela ficha, conferência automática, validação das sócias, cálculo do bônus nos meses fechados, tela do criador
(sem os números da pessoa indicada), tela da gestão e isolamento no banco. Dados inventados (sufixo .demo)."""
import datetime as dt
import re
from decimal import Decimal

from django.db import DatabaseError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.models import PartnerGroup
from core.rls import as_user, set_context, system_context
from crm import referrals as R
from crm.models import CreatorPrivate, ExitRecord, Referral, ReferralBonus
from data.models import MonthlyResult
from engage.tom import verificar_tom

from . import factories as F

DEZ = dt.date(2026, 12, 5)  # setembro, outubro e novembro já fecharam


def _mes(c, m, horas, dias, diamantes=0):
    MonthlyResult.objects.update_or_create(creator=c, month=m, defaults={
        "live_seconds": horas * 3600, "valid_days": dias, "diamonds": diamantes, "source": "backstage"})


def _texto(r):
    html = re.sub(r"<head>.*?</head>|<script.*?</script>|<style.*?</style>", " ", r.content.decode(), flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


class IndiqueEGanheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.u_quem, cls.u_indicada, cls.u_outro = F.user(), F.user(), F.user()
        cls.quem = F.creator(cls.ag, username="quem.indica.demo", streamer_user=cls.u_quem)
        cls.indicada = F.creator(cls.ag, username="indicada.demo", streamer_user=cls.u_indicada)
        cls.outro = F.creator(cls.ag, username="outro.demo", streamer_user=cls.u_outro)
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        cls.admin = F.user(role="admin", ag=cls.ag)
        cls.fin = F.user(role="financeiro", ag=cls.ag)
        assign_manager(cls.indicada, cls.gx)
        assign_manager(cls.quem, cls.gy)
        assign_manager(cls.outro, cls.gy)
        type(cls.indicada).objects.filter(pk=cls.indicada.pk).update(joined_at=timezone.now() - dt.timedelta(days=2))
        cls.indicada.refresh_from_db()
        set_context()

    def tearDown(self):
        set_context()

    def _registrar(self, user=None, handle="@quem.indica.demo"):
        self.client.force_login(user or self.gx)
        return self.client.post(reverse("g_creator_action", args=[self.indicada.pk]), {"a": "profile", "referred_by": handle})

    def _ref(self):
        with system_context():
            return Referral.objects.filter(referred=self.indicada).first()

    def _entrada(self, d):
        with system_context():
            type(self.indicada).objects.filter(pk=self.indicada.pk).update(joined_at=timezone.make_aware(dt.datetime(d.year, d.month, d.day, 12)))
            self.indicada.refresh_from_db()

    # ------------------------------------------------------------ registro e conferência
    def test_ficha_registra_a_indicacao_e_o_app_confere_o_que_da(self):
        self._registrar()
        r = self._ref()
        self.assertEqual((r.referrer_id, r.status, r.late, r.auto_issue, r.registered_by_id), (self.quem.pk, "", False, "", self.gx.pk))
        # apagar o "indicado por" apaga a indicação; voltar recria
        self._registrar(handle="")
        self.assertIsNone(self._ref())
        # quem já fez parte da Hera: não validada pelo app, com o motivo
        with system_context():
            ExitRecord.objects.create(creator=self.indicada, requested_at=timezone.localdate() - dt.timedelta(days=200))
        self._registrar()
        r = self._ref()
        self.assertEqual(r.status, "nao_validada")
        self.assertIn("Já fez parte da Hera", r.reason)

    def test_registro_tardio_e_grupo_parceiro(self):
        self._entrada(timezone.localdate() - dt.timedelta(days=40))
        self._registrar()
        self.assertTrue(self._ref().late)
        with system_context():
            pg = PartnerGroup.objects.create(agency=self.ag, name="Parceira Demo", is_direct=False)
            type(self.quem).objects.filter(pk=self.quem.pk).update(partner_group=pg)
        self._registrar(handle="")
        self._registrar()
        self.assertIn("grupo parceiro", self._ref().reason)

    def test_bonus_pago_trava_a_troca_do_indicado_por(self):
        self._registrar()
        with system_context():
            ReferralBonus.objects.create(referral=self._ref(), kind="m1", month=dt.date(2026, 9, 1), amount=20, paid_at=dt.date(2026, 10, 15))
        self._registrar(handle="@outro.demo")
        self.assertEqual(self._ref().referrer_id, self.quem.pk)

    # ------------------------------------------------------------ cálculo
    def test_calculo_dos_meses_faixas_minimo_de_quem_indicou_e_graduacao(self):
        self._entrada(dt.date(2026, 9, 10))  # Mês 1 = setembro
        self._registrar()
        with system_context():
            _mes(self.indicada, dt.date(2026, 9, 1), 45, 15)            # 40h e 14 dias: R$ 30 (não soma a de 25h)
            _mes(self.indicada, dt.date(2026, 10, 1), 65, 18, 9_000)    # faixa de 60h, mas menos de 10 mil diamantes
            _mes(self.indicada, dt.date(2026, 11, 1), 82, 21, 90_000)   # R$ 15 e graduou (dentro dos 90 dias)
            _mes(self.quem, dt.date(2026, 9, 1), 30, 9)
            _mes(self.quem, dt.date(2026, 10, 1), 30, 9)
            _mes(self.quem, dt.date(2026, 11, 1), 30, 9)
            R.compute(self.ag, today=DEZ)
            b = {x.kind: x for x in ReferralBonus.objects.filter(referral__referred=self.indicada)}
        self.assertEqual({k: v.amount for k, v in b.items()}, {"m1": 30, "m2": 0, "m3": 15, "grad": 50})
        self.assertEqual(b["m2"].reason, "A pessoa indicada não chegou à primeira faixa deste mês.")
        self.assertEqual(b["grad"].month, dt.date(2026, 11, 1))
        # quem indicou abaixo de 25h e 8 dias no mês: sem bônus naquele mês; mês pago não muda
        with system_context():
            ReferralBonus.objects.filter(referral__referred=self.indicada, kind="m1").update(paid_at=dt.date(2026, 10, 15))
            _mes(self.quem, dt.date(2026, 9, 1), 10, 3)
            _mes(self.quem, dt.date(2026, 11, 1), 24, 8)
            R.compute(self.ag, today=DEZ)
            b = {x.kind: x for x in ReferralBonus.objects.filter(referral__referred=self.indicada)}
        self.assertEqual((b["m1"].amount, b["m3"].amount), (30, 0))
        self.assertIn("Você não chegou ao mínimo do programa", b["m3"].reason)

    def test_entrada_depois_do_dia_15_mes_aberto_e_saida(self):
        self._entrada(dt.date(2026, 9, 20))  # Mês 1 = outubro
        self._registrar()
        with system_context():
            st = self.ag.settings
            self.assertEqual(R.program_months(self.indicada, st), [dt.date(2026, 10, 1), dt.date(2026, 11, 1), dt.date(2026, 12, 1)])
            for m in (dt.date(2026, 10, 1), dt.date(2026, 11, 1)):
                _mes(self.indicada, m, 100, 22, 30_000)
                _mes(self.quem, m, 30, 9)
            R.compute(self.ag, today=DEZ)
            self.assertEqual(set(ReferralBonus.objects.values_list("kind", flat=True)), {"m1", "m2"})  # dezembro não fechou
            # a pessoa indicada saiu em 10/11: outubro continua devido, novembro não
            type(self.indicada).objects.filter(pk=self.indicada.pk).update(status="saiu")
            ExitRecord.objects.create(creator=self.indicada, requested_at=dt.date(2026, 11, 10))
            R.compute(self.ag, today=DEZ)
            b = {x.kind: x for x in ReferralBonus.objects.all()}
        self.assertEqual((b["m1"].amount, b["m2"].amount), (65, 0))
        self.assertEqual(b["m2"].reason, "Saída da Hera antes do fim do mês.")

    # ------------------------------------------------------------ telas
    def test_tela_do_criador_link_situacao_e_sem_numeros_da_indicada(self):
        self._entrada(dt.date(2026, 9, 10))
        self._registrar()
        with system_context():
            _mes(self.indicada, dt.date(2026, 9, 1), 45, 15, 12_345)
            _mes(self.quem, dt.date(2026, 9, 1), 30, 9)
            R.compute(self.ag, today=DEZ)
        self.client.force_login(self.u_quem)
        self.assertContains(self.client.get("/"), "Indique e ganhe")
        r = self.client.post(reverse("referral"), {"link": "https://outro-site.com/x"}, follow=True)
        self.assertContains(r, "Cole o link de indicação do app do TikTok")
        self.client.post(reverse("referral"), {"link": "https://www.tiktok.com/t/Indica01/"})
        with system_context():
            self.assertEqual(CreatorPrivate.objects.get(creator=self.quem).referral_link, "https://www.tiktok.com/t/Indica01/")
        tela = self.client.get(reverse("referral"))
        for trecho in ["https://www.tiktok.com/t/Indica01/", "@indicada.demo", "Em andamento", "R$ 30 quando a indicação for validada",
                       "Regras do programa", "regra do programa"]:
            self.assertContains(tela, trecho)
        texto = _texto(tela)
        self.assertEqual(verificar_tom(texto), [])
        self.assertNotIn("12.345", texto)  # números da pessoa indicada nunca aparecem
        self.assertNotIn("45h", texto)
        # as sócias validam: o bônus passa para "a receber"
        self.client.force_login(self.admin)
        self.client.post(reverse("g_referrals"), {"referral": self._ref().pk, "status": "valida"})
        self.client.force_login(self.u_quem)
        tela = self.client.get(reverse("referral"))
        self.assertContains(tela, "a receber")
        self.assertRegex(_texto(tela), r"A receber R\$ 30")
        # a pessoa indicada não vê a indicação de quem indicou
        self.client.force_login(self.u_indicada)
        self.assertNotContains(self.client.get(reverse("referral")), "@quem.indica.demo")

    def test_tela_da_gestao_validacao_e_valores_so_para_socias_e_financeiro(self):
        self._entrada(dt.date(2026, 9, 10))
        self._registrar()
        self.client.force_login(self.gx)
        tela = self.client.get(reverse("g_referrals"))
        self.assertContains(tela, "@indicada.demo")
        self.assertNotContains(tela, "Bônus a pagar")
        self.assertEqual(self.client.post(reverse("g_referrals"), {"referral": self._ref().pk, "status": "valida"}).status_code, 403)
        self.client.force_login(self.admin)
        r = self.client.post(reverse("g_referrals"), {"referral": self._ref().pk, "status": "nao_validada", "reason": ""}, follow=True)
        self.assertContains(r, "Escreva o motivo")
        self.client.post(reverse("g_referrals"), {"referral": self._ref().pk, "status": "valida"})
        self.assertEqual(self._ref().status, "valida")
        with system_context():
            ReferralBonus.objects.create(referral=self._ref(), kind="m1", month=dt.date(2026, 9, 1), amount=Decimal("30"))
        from data import engine as E

        with system_context():
            ReferralBonus.objects.filter(referral=self._ref()).update(month=E.prev_month(E.tiktok_today()))
        self.client.force_login(self.fin)
        tela = self.client.get(reverse("g_referrals"))
        self.assertContains(tela, "Bônus a pagar")
        self.assertContains(tela, "@quem.indica.demo")
        self.assertContains(tela, "R$ 30")
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("g_panel")), "Indique e ganhe:")

    # ------------------------------------------------------------ parte 2: Pix, pagamento e recibo
    CPF = "52998224725"  # CPF de exemplo, válido só no cálculo (gerador de testes)

    def test_cpf_e_cadastro_do_pix_pelo_criador(self):
        self.assertTrue(R.valid_cpf(self.CPF))
        self.assertFalse(R.valid_cpf("52998224724"))
        self.assertFalse(R.valid_cpf("11111111111"))
        self.client.force_login(self.u_quem)
        url = reverse("referral")
        r = self.client.post(url, {"a": "pix", "full_name": "Quem Indica Demo", "cpf": "529.982.247-24", "key_type": "cpf"}, follow=True)
        self.assertContains(r, "Confira o CPF")
        r = self.client.post(url, {"a": "pix", "full_name": "Quem", "cpf": self.CPF, "key_type": "cpf"}, follow=True)
        self.assertContains(r, "nome completo")
        self.client.post(url, {"a": "pix", "full_name": "Quem Indica Demo", "cpf": "529.982.247-25", "key_type": "email", "key": "quem@teste.demo"})
        tela = self.client.get(url)
        self.assertContains(tela, "***.982.***-25")  # parcialmente escondido
        self.assertContains(tela, "qu***@teste.demo")
        self.assertNotContains(tela, "529.982.247-25")
        self.assertEqual(verificar_tom(_texto(tela)), [])

    def _pagavel(self):
        from data import engine as E
        from crm.models import PixInfo

        self._registrar()
        mes = E.prev_month(E.tiktok_today())
        with system_context():
            r = self._ref()
            r.status = "valida"
            r.save()
            ReferralBonus.objects.create(referral=r, kind="m1", month=mes, amount=Decimal("30"))
            PixInfo.objects.create(creator=self.quem, full_name="Quem Indica Demo", cpf=self.CPF, key_type="cpf", key=self.CPF)
        return mes

    def test_financeiro_marca_pago_recibo_e_o_criador_e_avisado(self):
        mes = self._pagavel()
        url = reverse("g_referrals")
        self.client.force_login(self.fin)
        tela = self.client.get(url)
        self.assertContains(tela, "529.982.247-25")  # o financeiro vê o Pix completo
        r = self.client.post(url, {"a": "receipt", "referrer": self.quem.pk, "month": f"{mes:%Y-%m}"}, follow=True)
        self.assertContains(r, "Marque o pagamento antes do recibo")
        self.client.post(url, {"a": "paid", "referrer": self.quem.pk, "month": f"{mes:%Y-%m}", "on": "2026-12-15"})
        recibo = self.client.get(reverse("g_referral_receipt", args=[self.quem.pk, f"{mes:%Y-%m}"]))
        for trecho in ["Quem Indica Demo", "529.982.247-25", "@quem.indica.demo", "@indicada.demo", "Mês 1", "15/12/2026"]:
            self.assertContains(recibo, trecho)
        self.client.post(url, {"a": "receipt", "referrer": self.quem.pk, "month": f"{mes:%Y-%m}", "on": "2026-12-18"})
        with system_context():
            from engage.models import Notification

            b = ReferralBonus.objects.get(referral__referred=self.indicada)
            self.assertEqual((b.paid_at, b.paid_by_id, b.receipt_at), (dt.date(2026, 12, 15), self.fin.pk, dt.date(2026, 12, 18)))
            self.assertTrue(Notification.objects.filter(user=self.u_quem, title="Bônus do Indique e ganhe pago 💜").exists())
        self.client.force_login(self.u_quem)
        tela = self.client.get(reverse("referral"))
        self.assertContains(tela, "pago em 15/12")
        self.assertRegex(_texto(tela), r"Já recebi R\$ 30")
        # a gestora não marca pagamento nem abre o recibo
        self.client.force_login(self.gx)
        self.assertEqual(self.client.post(url, {"a": "paid", "referrer": self.quem.pk, "month": f"{mes:%Y-%m}"}).status_code, 403)
        self.assertEqual(self.client.get(reverse("g_referral_receipt", args=[self.quem.pk, f"{mes:%Y-%m}"])).status_code, 403)

    def test_banco_isola_o_pix(self):
        from crm.models import PixInfo

        self._pagavel()
        with as_user(self.u_quem):
            self.assertEqual(PixInfo.objects.count(), 1)
        for u in (self.gx, self.gy, self.u_outro, self.u_indicada):
            with as_user(u):
                self.assertEqual(PixInfo.objects.count(), 0)
        with as_user(self.fin):
            self.assertEqual(PixInfo.objects.count(), 1)
            self.assertEqual(PixInfo.objects.update(key="outra"), 0)  # o financeiro lê, não troca
        with as_user(self.admin):
            self.assertEqual(PixInfo.objects.count(), 1)
        with as_user(self.u_outro), self.assertRaises(DatabaseError), transaction.atomic():
            PixInfo.objects.create(creator=self.indicada, full_name="X Y", cpf=self.CPF, key_type="cpf", key=self.CPF)

    # ------------------------------------------------------------ isolamento no banco
    def test_banco_isola_indicacao_e_valores(self):
        self._registrar()
        with system_context():
            ReferralBonus.objects.create(referral=self._ref(), kind="m1", month=dt.date(2026, 9, 1), amount=20)
        with as_user(self.u_quem):  # quem indicou: a indicação e o bônus dele
            self.assertEqual((Referral.objects.count(), ReferralBonus.objects.count()), (1, 1))
            self.assertEqual(Referral.objects.filter(pk=self._ref().pk).update(status="valida"), 0)  # não se valida sozinho
        with as_user(self.u_indicada):  # a pessoa indicada não lê
            self.assertEqual((Referral.objects.count(), ReferralBonus.objects.count()), (0, 0))
        with as_user(self.u_outro):
            self.assertEqual(Referral.objects.count(), 0)
        with as_user(self.gx):  # a gestora vê a situação, nunca os valores, e não valida
            self.assertEqual((Referral.objects.count(), ReferralBonus.objects.count()), (1, 0))
            self.assertEqual(Referral.objects.update(status="valida"), 0)
            with self.assertRaises(DatabaseError), transaction.atomic():
                Referral.objects.create(agency=self.ag, referred=self.outro, referrer=self.quem)
        with as_user(self.fin):
            self.assertEqual(ReferralBonus.objects.count(), 1)
        with as_user(self.u_quem):  # o próprio link fica no cadastro privado dele
            p, _ = CreatorPrivate.objects.get_or_create(creator=self.quem)
            p.referral_link = "https://www.tiktok.com/t/x/"
            p.save()
