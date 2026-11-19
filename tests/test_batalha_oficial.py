"""Batalha oficial (etapa 3, passo 3.3): pedido pelo modelo oficial com 7 dias de antecedência, confirmação pela gestão
com o texto pronto da BAT-CONF, batalha confirmada e checklist no app, histórico. Isolamento entre criadores e carteiras."""
import datetime as dt
import re
from types import SimpleNamespace as NS

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.models import AgencySettings
from core.rls import set_context, system_context
from engage import battles as B
from engage.models import BattleRequest, Notification
from engage.tom import verificar_tom

from . import factories as F


def _texto(resposta):
    html = resposta.content.decode()
    html = re.sub(r"<head>.*?</head>|<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _dia(n):
    return (timezone.localdate() + dt.timedelta(days=n)).isoformat()


class TextoDaConfirmacaoTests(SimpleTestCase):
    def test_preenche_os_colchetes_da_bat_conf(self):
        corpo = "📆 Data: [dd/mm] · ⏰ [hora] (Brasília)\n🥊 Rounds: [1 ou 3]\n💎 Diamantes esperados para você: [faixa]\n👤 @[criador] 🆚 @[oponente]"
        b = NS(date=dt.date(2026, 12, 5), time=dt.time(20, 30), rounds=3, expected_range="30 a 50 mil 💎",
               creator=NS(username="bia.demo"), opponent_text="rival.demo · Agência X")
        self.assertEqual(B.fill_confirmation(corpo, b), "📆 Data: 05/12 · ⏰ 20:30 (Brasília)\n🥊 Rounds: 3\n💎 Diamantes esperados para você: "
                                                       "30 a 50 mil 💎\n👤 @bia.demo 🆚 @rival.demo · Agência X")

    def test_checklist_do_roteiro(self):
        cl = B.checklist(NS(checklist_done=["testar", "inventado"]))
        self.assertEqual([g for g, _ in cl["groups"]], ["Antes", "No dia"])
        self.assertEqual((cl["n_done"], cl["n_total"]), (1, 6))
        for _g, itens in cl["groups"]:
            for it in itens:
                self.assertEqual(verificar_tom(it["text"]), [], it["text"])


class BatalhaOficialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.ua, cls.ub = F.user(), F.user()
        cls.a = F.creator(cls.ag, username="streamer.a", streamer_user=cls.ua)
        cls.b = F.creator(cls.ag, username="streamer.b", streamer_user=cls.ub)
        cls.gx = F.user(role="gestora", ag=cls.ag)
        cls.gy = F.user(role="gestora", ag=cls.ag)
        assign_manager(cls.a, cls.gx)
        assign_manager(cls.b, cls.gy)
        set_context()

    def tearDown(self):
        set_context()

    def _pedir(self, **kw):
        dados = {"date": _dia(8), "date2": _dia(10), "time": "20:30", "rounds": "0", "other_agency": "nao", "banner": "sim",
                 "goal_diamonds": "", "notes": "Tema de Natal"}
        dados.update(kw)
        return self.client.post(reverse("battle_new"), dados)

    def _pedidos(self, creator):
        with system_context():
            return list(BattleRequest.objects.filter(creator=creator).order_by("pk"))

    def test_pedido_pelo_modelo_oficial_com_7_dias(self):
        self.client.force_login(self.ua)
        form = self.client.get(reverse("battle_new"))
        primeiro = timezone.localdate() + dt.timedelta(days=7)
        self.assertContains(form, f"as datas começam em {primeiro:%d/%m}")
        self.assertContains(form, f'min="{primeiro:%Y-%m-%d}"')
        self.assertEqual(verificar_tom(_texto(form)), [])
        # antes dos 7 dias, datas iguais ou rounds inválido: não grava e explica (a pergunta da outra agência saiu em 19/11)
        for kw, msg in [({"date": _dia(6)}, "As datas começam em"), ({"date2": _dia(8)}, "duas datas diferentes"),
                        ({"rounds": "2"}, "quantos rounds"), ({"time": ""}, "a hora"),
                        ({"goal_diamonds": "muitos"}, "só com números")]:
            r = self._pedir(**kw)
            self.assertEqual(r.status_code, 200, kw)
            self.assertContains(r, msg)
            self.assertEqual(verificar_tom(_texto(r)), [], kw)
        self.assertEqual(self._pedidos(self.a), [])
        # 7 dias certinhos já vale; "tanto faz" nos rounds e diamantes em branco (a Hera sugere pelo histórico)
        r = self._pedir(date=_dia(7))
        self.assertRedirects(r, reverse("battles"), fetch_redirect_response=False)
        (b,) = self._pedidos(self.a)
        self.assertEqual((b.date.isoformat(), b.other_options, b.rounds), (_dia(7), [{"date": _dia(10), "time": "20:30"}], 0))
        # o campo "outra agência" fica vazio mesmo que chegue no envio (o app não pergunta mais)
        self.assertEqual((b.goal_diamonds, b.other_agency_ok, b.banner_help, b.status), (None, None, True, "pendente"))
        with system_context():
            self.assertTrue(Notification.objects.filter(user=self.gx, title__contains="pediu uma batalha oficial").exists())
            self.assertFalse(Notification.objects.filter(user=self.gy).exists())
        self.assertContains(self.client.get(reverse("battles")), "Aguardando a Hera")
        # a datas chegam em qualquer ordem: a mais cedo vira a 1ª opção
        self._pedir(date=_dia(12), date2=_dia(9))
        self.assertEqual(self._pedidos(self.a)[1].date.isoformat(), _dia(9))

    def test_antecedencia_vem_das_configuracoes(self):
        with system_context():
            AgencySettings.objects.filter(agency=self.ag).update(battle_notice_days=3)
        self.client.force_login(self.ua)
        self.assertRedirects(self._pedir(date=_dia(3), date2=_dia(4)), reverse("battles"), fetch_redirect_response=False)

    def test_gestao_confirma_e_o_criador_ve_a_batalha_e_o_checklist(self):
        self.client.force_login(self.ua)
        self._pedir()
        (b,) = self._pedidos(self.a)
        self.client.force_login(self.gx)
        tela = self.client.get(reverse("g_battles"))
        for trecho in ["@streamer.a", "Tanto faz", "quer ajuda com o banner", "Tema de Natal",
                       "diamantes: sugerir pelo histórico", "Confirmar batalha"]:
            self.assertContains(tela, trecho)
        self.assertNotContains(tela, "outra agência:")  # o criador não escolhe mais (decisão de 19/11)
        # status "aprovada" sem oponente não vale; confirmar exige oponente e 1 ou 3 rounds
        self.client.post(reverse("g_battles"), {"id": b.pk, "status": "aprovada"})
        self.client.post(reverse("g_battles"), {"id": b.pk, "a": "confirm", "choice": "1", "final_rounds": "0", "opponent": "@rival.demo"})
        self.client.post(reverse("g_battles"), {"id": b.pk, "a": "confirm", "choice": "1", "final_rounds": "3", "opponent": " "})
        self.assertEqual(self._pedidos(self.a)[0].status, "pendente")
        # confirma na 2ª opção do criador: ela vira a data da batalha e a 1ª fica guardada
        self.client.post(reverse("g_battles"), {"id": b.pk, "a": "confirm", "choice": "1", "final_rounds": "3",
                                                "opponent": "rival.demo · Agência X", "expected_range": "30 a 50 mil 💎", "reply": "Bora!"})
        (b,) = self._pedidos(self.a)
        self.assertEqual((b.status, b.date.isoformat(), b.rounds), ("aprovada", _dia(10), 3))
        self.assertEqual(b.other_options, [{"date": _dia(8), "time": "20:30"}])
        self.assertIsNotNone(b.confirmed_at)
        with system_context():
            self.assertTrue(Notification.objects.filter(user=self.ua, title__startswith="Sua batalha oficial está confirmada").exists())
        tela = self.client.get(reverse("g_battles"))
        for trecho in ["BATALHA OFICIAL CONFIRMADA", f"{b.date:%d/%m} · ⏰ 20:30", "@streamer.a 🆚 @rival.demo · Agência X", "30 a 50 mil 💎",
                       "Copiar confirmação", "checklist do criador: 0 de 6"]:
            self.assertContains(tela, trecho)
        # o criador vê a batalha confirmada e o checklist, sem palavra vetada
        self.client.force_login(self.ua)
        minhas = self.client.get(reverse("battles"))
        for trecho in ["Batalha oficial confirmada", "Em 10 dias", "20:30 (Brasília)", "@streamer.a 🆚 @rival.demo · Agência X", "30 a 50 mil 💎",
                       "Hera: Bora!", "Checklist da batalha", "0 de 6", "Testar luz, áudio e internet", "Abrir a LIVE 30 min antes"]:
            self.assertContains(minhas, trecho)
        self.assertEqual(verificar_tom(_texto(minhas)), [])
        self.assertContains(self.client.get("/"), f"Sua batalha oficial: {b.date:%d/%m} às 20:30")
        # marcar um item (HTMX devolve só o checklist) e desmarcar
        r = self.client.post(reverse("battle_check", args=[b.pk]), {"item": "testar"}, HTTP_HX_REQUEST="true")
        self.assertContains(r, "1 de 6")
        self.assertNotContains(r, "Minhas batalhas")
        self.assertEqual(self._pedidos(self.a)[0].checklist_done, ["testar"])
        self.client.post(reverse("battle_check", args=[b.pk]), {"item": "testar"})
        self.assertEqual(self._pedidos(self.a)[0].checklist_done, [])
        self.assertEqual(self.client.post(reverse("battle_check", args=[b.pk]), {"item": "inventado"}).status_code, 404)
        # mudança depois de confirmada: o criador recebe "mudou"
        self.client.force_login(self.gx)
        self.client.post(reverse("g_battles"), {"id": b.pk, "a": "confirm", "choice": "outra", "other_date": _dia(11), "other_time": "21:00",
                                                "final_rounds": "1", "opponent": "@rival.demo"})
        (b,) = self._pedidos(self.a)
        self.assertEqual((b.date.isoformat(), b.time, b.rounds), (_dia(11), dt.time(21, 0), 1))
        with system_context():
            self.assertTrue(Notification.objects.filter(user=self.ua, title__startswith="Sua batalha oficial mudou").exists())

    def test_historico_sem_resultado_nem_diamantes(self):
        with system_context():
            BattleRequest.objects.create(creator=self.a, kind="oficial", date=timezone.localdate() - dt.timedelta(days=5), time=dt.time(20, 0),
                                         rounds=3, status="realizada", opponent_text="@antigo.demo")
        self.client.force_login(self.ua)
        minhas = self.client.get(reverse("battles"))
        self.assertContains(minhas, "Histórico")
        self.assertContains(minhas, "🆚 @antigo.demo")
        self.assertContains(minhas, "Nenhuma batalha marcada agora.")
        self.assertNotContains(minhas, "Venceu")
        self.assertEqual(verificar_tom(_texto(minhas)), [])

    def test_isolamento_entre_criadores_e_carteiras(self):
        self.client.force_login(self.ua)
        self._pedir()
        (b,) = self._pedidos(self.a)
        # gestora de outra carteira não vê nem confirma
        self.client.force_login(self.gy)
        self.assertNotContains(self.client.get(reverse("g_battles")), "@streamer.a")
        r = self.client.post(reverse("g_battles"), {"id": b.pk, "a": "confirm", "choice": "0", "final_rounds": "3", "opponent": "@x"})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self._pedidos(self.a)[0].status, "pendente")
        self.client.force_login(self.gx)
        self.client.post(reverse("g_battles"), {"id": b.pk, "a": "confirm", "choice": "0", "final_rounds": "3", "opponent": "@rival.demo"})
        # outro criador não marca o checklist nem vê a batalha
        self.client.force_login(self.ub)
        self.assertEqual(self.client.post(reverse("battle_check", args=[b.pk]), {"item": "testar"}).status_code, 404)
        self.assertNotContains(self.client.get(reverse("battles")), "@rival.demo")
        self.assertEqual(self._pedidos(self.a)[0].checklist_done, [])
