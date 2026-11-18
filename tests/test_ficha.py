"""Ficha do criador (passo 2.2): cadastro, linha do tempo, lembretes, motivo de quem parou, batalhas e saída com motivo."""
import datetime as dt

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import as_user, set_context, system_context
from crm.models import BattleRecord, Contact, Creator, ExitRecord, Note, Reminder, Reply, StopReason
from engage.models import BattleRequest
from web import services as S

from . import factories as F


class FichaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gx = F.user(role="gestora", ag=cls.ag, first_name="Ana")
        cls.gy = F.user(role="gestora", ag=cls.ag)
        cls.fernanda = F.user(role="recrutadora", ag=cls.ag, first_name="Fernanda")
        cls.adrielly = F.user(role="recrutadora", ag=cls.ag, first_name="Adrielly")
        cls.ua = F.user()
        cls.a = F.creator(cls.ag, username="ficha.demo", streamer_user=cls.ua)
        cls.b = F.creator(cls.ag, username="indicou.demo")  # de outra carteira
        assign_manager(cls.a, cls.gx)
        assign_manager(cls.b, cls.gy)
        set_context()

    def setUp(self):
        self.client.force_login(self.gx)
        self.acao = reverse("g_creator_action", args=[self.a.pk])
        self.ficha = reverse("g_creator", args=[self.a.pk])

    def tearDown(self):
        set_context()

    def _a(self):
        with system_context():
            return Creator.objects.select_related("private", "recruited_by").get(pk=self.a.pk)

    # ------------------------------------------------------------ cadastro
    def test_cadastro_trilha_nicho_recrutadora_indicacao_e_aniversario(self):
        tela = self.client.get(self.ficha)
        self.assertContains(tela, "Fernanda")
        self.assertContains(tela, "Adrielly")
        r = self.client.post(self.acao, {"a": "profile", "track": "outra_agencia", "niche": "musica", "does_battles": "nao", "recruited_by": self.fernanda.pk,
                                         "referred_by": "@Indicou.Demo", "birth_day": "7", "birth_month": "3"})
        self.assertRedirects(r, self.ficha, fetch_redirect_response=False)
        c = self._a()
        self.assertEqual((c.track, c.niche, c.recruited_by_id, c.referred_by_id), ("outra_agencia", "musica", self.fernanda.pk, self.b.pk))
        self.assertEqual((c.private.birth_day, c.private.birth_month), (7, 3))
        tela = self.client.get(self.ficha)
        self.assertContains(tela, 'value="@indicou.demo"')  # mostra o @ de quem indicou, mesmo sendo de outra carteira
        self.assertEqual(self.client.get(reverse("g_creator", args=[self.b.pk])).status_code, 404)  # mas a ficha dele continua fechada
        # a troca de recrutadora fica registrada na linha do tempo
        self.client.post(self.acao, {"a": "profile", "track": "outra_agencia", "niche": "musica", "does_battles": "nao", "recruited_by": self.adrielly.pk,
                                     "referred_by": "@indicou.demo", "birth_day": "7", "birth_month": "3"})
        self.assertEqual(self._a().recruited_by_id, self.adrielly.pk)
        self.assertContains(self.client.get(self.ficha), "Recrutadora: Fernanda → Adrielly")
        # quem foi indicado aparece na ficha de quem indicou
        self.client.force_login(self.gy)
        self.assertContains(self.client.get(reverse("g_creator", args=[self.b.pk])), "Indicou: @ficha.demo")

    def test_cadastro_recusa_arroba_inexistente_e_gestora_que_nao_e_recrutadora(self):
        self.client.post(self.acao, {"a": "profile", "referred_by": "@nao.existe"})
        self.assertIsNone(self._a().referred_by_id)
        self.client.post(self.acao, {"a": "profile", "recruited_by": self.gy.pk})
        self.assertIsNone(self._a().recruited_by_id)
        self.client.post(self.acao, {"a": "profile", "referred_by": "@ficha.demo"})  # não pode indicar a si
        self.assertIsNone(self._a().referred_by_id)

    def test_primeiro_acesso_pergunta_experiencia_e_aniversario(self):
        self.client.force_login(self.ua)
        tela = self.client.get("/boas-vindas/?s=c")
        self.assertContains(tela, "Você já fez LIVE no TikTok?")
        self.assertContains(tela, "O ano não é pedido")
        r = self.client.post("/boas-vindas/", {"action": "cadastro", "experience": "nivel_publico", "birth_day": "21", "birth_month": "12"})
        self.assertRedirects(r, "/boas-vindas/?s=3", fetch_redirect_response=False)
        c = self._a()
        self.assertEqual((c.track_suggested, c.track), ("nivel_publico", ""))  # só sugere: quem define é a gestão
        self.assertEqual((c.private.birth_day, c.private.birth_month), (21, 12))
        self.client.force_login(self.gx)
        self.assertContains(self.client.get(self.ficha), "o cadastro sugere: Já tem nível e público")

    # ------------------------------------------------------------ linha do tempo
    def test_respondeu_e_escreveu_viram_linhas_novas(self):
        with system_context():
            Contact.objects.create(creator=self.a, user=self.gx, template_code="APO-03", body="Oi!")
        self.client.post(self.acao, {"a": "responded", "note": "Disse que volta amanhã"})
        self.client.post(self.acao, {"a": "responded", "note": "Confirmou a LIVE"})
        self.client.post(self.acao, {"a": "wrote", "note": "Perguntou do saque"})
        self.client.post(self.acao, {"a": "note", "body": "Prefere LIVE à noite"})
        with system_context():
            self.assertEqual(Reply.objects.filter(creator=self.a, kind="respondeu").count(), 2)  # nada por cima
            self.assertEqual(Reply.objects.filter(creator=self.a, kind="escreveu").count(), 1)
            primeira = Reply.objects.filter(kind="respondeu").order_by("created_at").first().created_at
            self.assertEqual(Contact.objects.get(creator=self.a).responded_at, primeira)  # a 2ª resposta não troca a data da 1ª
        tela = self.client.get(self.ficha)
        for texto in ["Linha do tempo", "Enviei: APO-03", "Disse que volta amanhã", "Confirmou a LIVE", "O criador escreveu",
                      "Perguntou do saque", "Prefere LIVE à noite", "Ana"]:
            self.assertContains(tela, texto)

    def test_lembrete_entra_na_fila_no_dia_e_sai_quando_feito(self):
        hoje = timezone.localdate()
        self.client.post(self.acao, {"a": "reminder_add", "text": "Retorno prometido", "due_date": (hoje + dt.timedelta(days=3)).isoformat()})
        self.client.post(self.acao, {"a": "reminder_add", "text": "Cobrar print do setup", "due_date": hoje.isoformat()})
        self.client.post(self.acao, {"a": "reminder_add", "text": "", "due_date": hoje.isoformat()})  # sem texto não cria
        with system_context():
            self.assertEqual(Reminder.objects.filter(creator=self.a).count(), 2)
            fila = [i for i in S.action_queue(Creator.objects.filter(pk=self.a.pk), self.ag) if i.code == "lembrete"]
        self.assertEqual(len(fila), 1)  # só o de hoje
        self.assertIn("Cobrar print do setup", fila[0].detail)
        self.assertContains(self.client.get("/gestao/"), "Cobrar print do setup")
        with system_context():
            lembrete = Reminder.objects.get(creator=self.a, due_date=hoje)
        self.client.post(self.acao, {"a": "reminder_done", "reminder": lembrete.pk})
        self.assertNotContains(self.client.get("/gestao/"), "Cobrar print do setup")
        self.assertContains(self.client.get(self.ficha), "Lembrete concluído")

    def test_motivo_de_quem_parou(self):
        volta = (timezone.localdate() + dt.timedelta(days=10)).isoformat()
        self.client.post(self.acao, {"a": "stop_reason", "reason": "desmotivou", "detail": "pouco_publico", "note": "Vai tentar outro formato"})
        self.client.post(self.acao, {"a": "stop_reason", "reason": "viagem", "detail": "vergonha", "return_date": volta})
        self.client.post(self.acao, {"a": "stop_reason", "reason": "inventado"})
        with system_context():
            motivos = list(StopReason.objects.filter(creator=self.a).order_by("created_at").values_list("reason", "detail"))
            self.assertEqual(motivos, [("desmotivou", "pouco_publico"), ("viagem", "")])  # o "porquê" só vale para desmotivou
            self.assertEqual(StopReason.objects.get(reason="viagem").return_date.isoformat(), volta)
        tela = self.client.get(self.ficha)
        self.assertContains(tela, "Motivo de quem parou: Desmotivou (Pouco público)")
        self.assertContains(tela, "Viagem")

    # ------------------------------------------------------------ batalhas
    def test_registro_de_batalha_com_resultado(self):
        with system_context():
            pedido = BattleRequest.objects.create(creator=self.a, kind="oficial", date=timezone.localdate(), time=dt.time(20, 0), status="aprovada")
        url = self.ficha + "?tab=batalhas"
        self.assertContains(self.client.get(url), "Registrar batalha")
        r = self.client.post(self.acao, {"a": "battle_record", "next": "?tab=batalhas", "request": pedido.pk, "date": timezone.localdate().isoformat(),
                                         "opponent": "@rival.demo · Agência X", "rounds": "3", "result": "venceu", "diamonds": "12000",
                                         "opponent_diamonds": "9000", "note": "Oponente do mesmo nível, funcionou"})
        self.assertRedirects(r, url, fetch_redirect_response=False)
        self.client.post(self.acao, {"a": "battle_record", "date": timezone.localdate().isoformat(), "result": "perdeu"})
        self.client.post(self.acao, {"a": "battle_record", "date": "", "result": "venceu"})  # sem data não grava
        with system_context():
            self.assertEqual(BattleRecord.objects.filter(creator=self.a).count(), 2)
            self.assertEqual(BattleRequest.objects.get(pk=pedido.pk).status, "realizada")
        tela = self.client.get(url)
        for texto in ["2 batalhas: 1 vitória, 1 derrota, 0 empates", "@rival.demo · Agência X", "12.000 x 9.000", "3 rounds",
                      "Oponente do mesmo nível, funcionou"]:
            self.assertContains(tela, texto)
        self.assertContains(self.client.get(self.ficha), "Batalha de")  # também na linha do tempo

    # ------------------------------------------------------------ saída
    def test_saida_exige_motivo_da_lista(self):
        self.client.post(self.acao, {"a": "exit", "reason": "texto solto"})
        with system_context():
            self.assertEqual(ExitRecord.objects.filter(creator=self.a).count(), 0)
            self.assertEqual(Creator.objects.get(pk=self.a.pk).status, "ativo")
        self.client.post(self.acao, {"a": "exit", "reason_code": "outra_agencia", "reason": "Recebeu proposta"})
        with system_context():
            self.assertEqual(ExitRecord.objects.get(creator=self.a).reason_code, "outra_agencia")
        self.assertContains(self.client.get(self.ficha + "?tab=saida"), "Outra agência")

    # ------------------------------------------------------------ isolamento
    def test_registros_internos_nunca_chegam_ao_criador_nem_a_outra_carteira(self):
        self.client.post(self.acao, {"a": "wrote", "note": "x"})
        self.client.post(self.acao, {"a": "reminder_add", "text": "y", "due_date": timezone.localdate().isoformat()})
        self.client.post(self.acao, {"a": "stop_reason", "reason": "saude"})
        self.client.post(self.acao, {"a": "battle_record", "date": timezone.localdate().isoformat(), "result": "empate"})
        modelos = [Reply, Reminder, StopReason, BattleRecord]
        for quem in (self.ua, self.gy, self.fernanda):
            with as_user(quem):
                for m in modelos:
                    self.assertEqual(m.objects.count(), 0, (quem, m.__name__))
        with as_user(self.gx):
            for m in modelos:
                self.assertEqual(m.objects.count(), 1, m.__name__)
        # gestora de outra carteira não grava na ficha
        self.client.force_login(self.gy)
        for dados in [{"a": "profile", "niche": "x"}, {"a": "wrote"}, {"a": "battle_record", "date": "2026-11-01", "result": "venceu"}]:
            self.assertEqual(self.client.post(self.acao, dados).status_code, 404)
        # o criador não vê nada disso no app
        self.client.force_login(self.ua)
        for url in ["/", "/perfil/", "/batalhas/"]:
            self.assertNotContains(self.client.get(url), "Linha do tempo")
        with system_context():
            self.assertEqual(Note.objects.filter(creator=self.a).count(), 0)
