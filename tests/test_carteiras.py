"""Carteiras e ausência da gestora (passo 2.7): divisão dos criadores entre as gestoras, com o histórico indo junto,
e o botão "Hoje não trabalho", com cobertura por uma sócia ou uma recrutadora só no dia e só para registrar o contato."""
import datetime as dt
from unittest import mock

from django.db import transaction
from django.db.utils import DatabaseError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.models import AuditLog, Membership
from core.rls import as_user, set_context, system_context
from crm import absence
from crm.models import Absence, AccessCode, AccountCase, Contact, Creator, Note, Reminder, Reply
from engage.models import BattleRequest, Notification, SupportTicket
from web import services as S

from . import factories as F

HOJE = dt.date(2026, 9, 30)  # quarta-feira; as fábricas contam a entrada a partir de 28/09 (joined_days_ago=d → dia d+3)


def _novato(ag, dia, **kw):
    return F.creator(ag, joined_days_ago=dia - 3, **kw)


class CarteirasBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.admin = F.user(role="admin", ag=cls.ag, first_name="Mariana")
        cls.anna = F.user(role="gestora", ag=cls.ag, first_name="Anna")
        cls.bia = F.user(role="gestora", ag=cls.ag, first_name="Bia")
        cls.rec = F.user(role="recrutadora", ag=cls.ag, first_name="Fernanda")
        cls.a1 = F.creator(cls.ag, username="anna.um")
        cls.a2 = F.creator(cls.ag, username="anna.dois")
        cls.novato = _novato(cls.ag, 12, username="novato.demo")  # D12 e nunca abriu LIVE: encerramento até o D14
        cls.b1 = F.creator(cls.ag, username="bia.um")
        cls.livre = F.creator(cls.ag, username="sem.gestora")
        for c in (cls.a1, cls.a2, cls.novato):
            assign_manager(c, cls.anna)
        assign_manager(cls.b1, cls.bia)
        Note.objects.create(creator=cls.a1, author=cls.anna, body="nota da Anna sobre o criador")
        Contact.objects.create(creator=cls.a1, user=cls.anna, template_code="ROD-PERG", body="Oi! Como estão as LIVEs?",
                               sent_at=timezone.now() - dt.timedelta(days=3))
        set_context()

    def setUp(self):
        patcher = mock.patch("data.engine.tiktok_today", return_value=HOJE)  # a fila não depende do dia em que o teste roda
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        set_context()

    def _gestora_de(self, c):
        with system_context():
            m = Creator.objects.get(pk=c.pk).current_manager()
            return m.pk if m else None

    def _avisos(self, user, kind):
        with system_context():
            return list(Notification.objects.filter(user=user, kind=kind).values_list("title", flat=True))


class TelaCarteirasTests(CarteirasBase):
    def test_so_as_socias_abrem_a_tela(self):
        for quem in (self.anna, self.rec):
            self.client.force_login(quem)
            self.assertEqual(self.client.get(reverse("g_portfolios")).status_code, 403)
            self.assertEqual(self.client.post(reverse("g_portfolios"), {"a": "move", "creator": self.b1.pk, "target": self.anna.pk}).status_code, 403)
            self.assertNotContains(self.client.get("/gestao/"), "🗂️ Carteiras")
        self.assertEqual(self._gestora_de(self.b1), self.bia.pk)
        self.client.force_login(self.admin)
        tela = self.client.get(reverse("g_portfolios"))
        for texto in ["Carteiras", "Anna", "Bia", "<b class=\"num\">3</b> criadores", "1 em onboarding (até o D15)", "Sem gestora",
                      "A troca de carteira leva o histórico junto", "@sem.gestora", "As sócias", "Fernanda", "trabalhando"]:
            self.assertContains(tela, texto)
        so_da_anna = self.client.get(reverse("g_portfolios") + f"?gestora={self.anna.pk}")
        self.assertContains(so_da_anna, "@anna.um")
        self.assertNotContains(so_da_anna, "@bia.um")
        sem = self.client.get(reverse("g_portfolios") + "?gestora=sem")
        self.assertContains(sem, "@sem.gestora")
        self.assertNotContains(sem, "@anna.um")

    def test_troca_de_carteira_leva_o_historico_junto(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("g_portfolios"), {"a": "move", "creator": [self.a1.pk, self.livre.pk], "target": self.bia.pk}, follow=True)
        self.assertContains(r, "2 criadores passaram para a carteira de Bia. O histórico foi junto.")
        self.assertContains(r, "2 criador(es) → Bia")  # últimas trocas
        self.assertContains(r, "1 de Anna")
        self.assertEqual((self._gestora_de(self.a1), self._gestora_de(self.livre), self._gestora_de(self.a2)), (self.bia.pk, self.bia.pk, self.anna.pk))
        with system_context():
            antigas = list(self.a1.assignments.order_by("valid_from"))
            self.assertEqual([(x.manager_id, x.valid_to is None) for x in antigas], [(self.anna.pk, False), (self.bia.pk, True)])  # nada apagado
            self.assertEqual(antigas[1].assigned_by_id, self.admin.pk)
            self.assertTrue(AuditLog.objects.filter(agency=self.ag, action="carteira_troca", actor=self.admin).exists())
        # no banco: a nova gestora lê tudo o que já existia; a anterior deixa de ler
        with as_user(self.bia):
            self.assertEqual(Note.objects.filter(creator=self.a1).count(), 1)
            self.assertEqual(Contact.objects.filter(creator=self.a1).count(), 1)
        with as_user(self.anna):
            self.assertFalse(Creator.objects.filter(pk=self.a1.pk).exists())
            self.assertEqual(Note.objects.filter(creator=self.a1).count(), 0)
        self.assertEqual(self._avisos(self.bia, "carteira"), ["2 criadores entraram na sua carteira"])
        self.assertEqual(self._avisos(self.anna, "carteira"), ["1 criador saiu da sua carteira"])
        # na tela: a ficha abre para a Bia com o histórico e a troca na linha do tempo; para a Anna, não abre mais
        self.client.force_login(self.bia)
        ficha = self.client.get(reverse("g_creator", args=[self.a1.pk]))
        for texto in ["nota da Anna sobre o criador", "Enviei: ROD-PERG", "Carteira: Bia", "Antes: Anna.", "por Mariana"]:
            self.assertContains(ficha, texto)
        self.client.force_login(self.anna)
        self.assertEqual(self.client.get(reverse("g_creator", args=[self.a1.pk])).status_code, 404)

    def test_sem_gestora_destino_invalido_e_outra_agencia(self):
        with system_context():
            outra = F.agency(slug="outra")
            de_fora = F.creator(outra, username="de.fora")
            gestora_de_fora = F.user(role="gestora", ag=outra)
        self.client.force_login(self.admin)
        url = reverse("g_portfolios")
        r = self.client.post(url, {"a": "move", "creator": [self.a2.pk], "target": "none"}, follow=True)
        self.assertContains(r, "1 criador passou para a lista “sem gestora”")
        self.assertIsNone(self._gestora_de(self.a2))
        with system_context():
            self.assertEqual(self.a2.assignments.count(), 1)  # o registro da carteira antiga continua lá, encerrado
        self.assertContains(self.client.get(reverse("g_creator", args=[self.a2.pk])), "Carteira: sem gestora")
        # destino que não é gestora desta agência, e criador de outra agência: nada muda
        for destino in (self.rec.pk, gestora_de_fora.pk, ""):
            self.assertContains(self.client.post(url, {"a": "move", "creator": [self.b1.pk], "target": destino}, follow=True), "Escolha para qual carteira")
        self.assertContains(self.client.post(url, {"a": "move", "creator": [de_fora.pk], "target": self.anna.pk}, follow=True), "Nenhum criador mudou de carteira")
        self.assertEqual(self._gestora_de(self.b1), self.bia.pk)
        self.assertIsNone(self._gestora_de(de_fora))

    def test_gestora_sem_o_papel_aparece_para_redistribuir(self):
        with system_context():
            Membership.objects.filter(user=self.bia, role="gestora").update(active=False)
        self.client.force_login(self.admin)
        tela = self.client.get(reverse("g_portfolios"))
        self.assertContains(tela, "sem o papel Gestora")
        self.assertContains(tela, "Passe os criadores dela para outra carteira")
        # e não dá para mandar mais criadores para ela
        self.assertContains(self.client.post(reverse("g_portfolios"), {"a": "move", "creator": [self.a1.pk], "target": self.bia.pk}, follow=True),
                            "Escolha para qual carteira")


class AusenciaTests(CarteirasBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        set_context(system=True)
        AccountCase.objects.create(creator=cls.a1, kind="restricao", opened_on=timezone.localdate(), author=cls.anna)  # não pode esperar
        Reminder.objects.create(creator=cls.a2, text="Retorno prometido sobre a agenda", due_date=timezone.localdate(), author=cls.anna)  # pode
        SupportTicket.objects.create(creator=cls.a2, question="Como faço para sacar?")  # pode
        set_context()

    def _define_cobertura(self, cover):
        self.client.force_login(self.admin)
        return self.client.post(reverse("g_portfolios"), {"a": "cover", "manager": self.anna.pk, "cover": cover.pk if cover else ""}, follow=True)

    def _ausencia(self):
        with system_context():
            return Absence.objects.filter(manager=self.anna).order_by("-id").first()

    def test_itens_que_nao_podem_esperar(self):
        """D10, D12, D14, encerramento, batalha oficial e restrição. O resto passa para o dia seguinte."""
        with system_context():
            d5 = _novato(self.ag, 5, username="d5.demo")  # nunca abriu LIVE, D5: pode esperar
            d10 = _novato(self.ag, 10, username="d10.demo")  # nunca abriu LIVE, D10
            d12 = _novato(self.ag, 12, username="d12.demo")  # abriu LIVE, 3 dias válidos: reforço
            fechou9 = _novato(self.ag, 9, username="fechou9.demo")
            fechou14 = _novato(self.ag, 14, username="fechou14.demo")
            F.snapshot(d12, dt.date(2026, 9, 1), dt.date(2026, 9, 29), diamonds=500, hours=8, valid_days=3, streams=3)
            for c in (fechou9, fechou14):
                F.snapshot(c, dt.date(2026, 9, 1), dt.date(2026, 9, 29), diamonds=500, hours=16, valid_days=5, streams=5)
            BattleRequest.objects.create(creator=self.b1, kind="oficial", date=HOJE + dt.timedelta(days=2), time=dt.time(20, 0), status="aprovada")
            BattleRequest.objects.create(creator=self.b1, kind="oficial", date=HOJE + dt.timedelta(days=9), time=dt.time(20, 0), status="pendente")
            fila = S.action_queue(Creator.objects.filter(agency=self.ag), self.ag, today=HOJE, raw=True)
        urgente = {(i.creator.username, i.code): i.urgent for i in fila}
        esperado = {
            ("anna.um", "restricao"): True, ("bia.um", "batalha_proxima"): True, ("novato.demo", "onboarding_encerrar"): True,
            ("d10.demo", "onboarding_nl10"): True, ("d12.demo", "onboarding_risco"): True, ("fechou14.demo", "onboarding_fechou"): True,
            ("fechou9.demo", "onboarding_fechou"): False, ("d5.demo", "onboarding_nl5"): False, ("anna.dois", "lembrete"): False,
            ("anna.dois", "duvida"): False, ("bia.um", "batalha"): False,
        }
        for chave, valor in esperado.items():
            self.assertEqual(urgente.get(chave), valor, chave)

    def test_hoje_nao_trabalho_manda_o_que_nao_pode_esperar_para_quem_cobre(self):
        self.assertContains(self._define_cobertura(self.rec), "Quem cobre Anna: Fernanda.")
        ficha_novato = reverse("g_creator", args=[self.novato.pk])
        # antes do aviso, a recrutadora não enxerga nada da carteira da Anna
        self.client.force_login(self.rec)
        self.assertEqual(self.client.get(ficha_novato).status_code, 404)
        self.assertNotContains(self.client.get("/gestao/"), "Cobertura de hoje")
        # a gestora avisa
        self.client.force_login(self.anna)
        painel = self.client.get("/gestao/")
        self.assertContains(painel, "Confirmar: hoje não trabalho")
        self.assertContains(painel, "<b>2</b> não podem esperar e vão para <b>Fernanda</b>")
        r = self.client.post(reverse("g_absence"), {"a": "start"}, follow=True)
        self.assertContains(r, "O que não pode esperar foi para Fernanda.")
        self.assertContains(r, "Você avisou que hoje não trabalha")
        self.assertContains(r, "2 que não podem esperar estão com <b>Fernanda</b>")
        self.assertContains(r, "Voltei: vou trabalhar hoje")
        self.assertNotContains(r, "Adiar com motivo")  # a fila dela sai da tela: os itens voltam amanhã
        a = self._ausencia()
        self.assertEqual((a.cover_id, a.day, a.created_by_id, a.cancelled_at), (self.rec.pk, timezone.localdate(), self.anna.pk, None))
        self.assertEqual(self._avisos(self.rec, "cobertura"), ["Você cobre a carteira de Anna hoje"])
        self.assertEqual(self._avisos(self.admin, "cobertura"), ["Anna não trabalha hoje"])
        self.client.post(reverse("g_absence"), {"a": "start"})  # clicar de novo não cria outra
        with system_context():
            self.assertEqual(Absence.objects.filter(manager=self.anna).count(), 1)
        # quem cobre vê só o que não pode esperar
        self.client.force_login(self.rec)
        painel = self.client.get("/gestao/")
        for texto in ["Cobertura de hoje · carteira de Anna", "Você cobre.", "@anna.um", "Restrição na conta: dia 1", "@novato.demo",
                      "nunca abriu LIVE: encerramento até o D14", "Os outros 2 itens da carteira passam para amanhã", "Enviei"]:
            self.assertContains(painel, texto)
        for texto in ["Retorno prometido sobre a agenda", "Como faço para sacar?", "@bia.um", "Adiar com motivo"]:
            self.assertNotContains(painel, texto)
        # a ficha abre, com aviso, e só os registros de contato ficam disponíveis
        ficha = self.client.get(ficha_novato)
        self.assertContains(ficha, "Você está cobrindo esta carteira hoje")
        self.assertContains(ficha, "Salvar nota")
        self.assertNotContains(ficha, "Salvar cadastro")
        self.assertNotContains(ficha, "Gerar código de acesso")
        acao = reverse("g_creator_action", args=[self.novato.pk])
        self.client.post(reverse("g_sent", args=[self.novato.pk, "ONB-NL-ENC"]))
        self.client.post(acao, {"a": "responded", "note": "Vai pensar e responde amanhã"})
        self.client.post(acao, {"a": "note", "body": "Cobri a carteira hoje."})
        with system_context():
            contato = Contact.objects.get(creator=self.novato)
            self.assertEqual((contato.user_id, contato.template_code), (self.rec.pk, "ONB-NL-ENC"))
            self.assertIsNotNone(contato.responded_at)
            self.assertEqual(Reply.objects.get(creator=self.novato).author_id, self.rec.pk)
            self.assertEqual(Note.objects.get(creator=self.novato).author_id, self.rec.pk)
        self.assertNotContains(self.client.get("/gestao/"), "nunca abriu LIVE: encerramento")  # enviado: saiu da cobertura
        self.assertEqual(self.client.get(ficha_novato).status_code, 200)  # e ela ainda consegue registrar a resposta
        # o que quem cobre NÃO faz
        proibidos = [
            (acao, {"a": "profile", "track": "outra_agencia"}), (acao, {"a": "exit", "reason_code": "outro"}),
            (acao, {"a": "case_open", "kind": "banimento"}), (acao, {"a": "reminder_add", "text": "x", "due_date": "2026-12-01"}),
            (reverse("g_dismiss", args=[self.novato.pk, "onboarding_encerrar"]), {"reason": "depois"}),
            (reverse("g_access_code", args=[self.novato.pk]), {}), (reverse("g_1a1", args=[self.novato.pk]), {"b1": "x"}),
        ]
        for url, dados in proibidos:
            self.assertEqual(self.client.post(url, dados).status_code, 403, (url, dados))
        self.assertEqual(self.client.get(reverse("g_creator", args=[self.b1.pk])).status_code, 404)  # carteira de outra gestora
        self.assertEqual(self.client.post(reverse("g_sent", args=[self.b1.pk, "ROD-PERG"])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("g_creators")), "@anna.um")  # as listas dela não mudam
        # "Voltei": a cobertura termina na hora e o registro fica
        self.client.force_login(self.anna)
        r = self.client.post(reverse("g_absence"), {"a": "cancel"}, follow=True)
        self.assertContains(r, "Ausência desfeita")
        self.assertContains(r, "Adiar com motivo")
        self.assertIsNotNone(self._ausencia().cancelled_at)
        self.client.force_login(self.rec)
        self.assertEqual(self.client.get(ficha_novato).status_code, 404)
        self.assertEqual(self.client.post(acao, {"a": "note", "body": "depois"}).status_code, 404)
        self.assertNotContains(self.client.get("/gestao/"), "Cobertura de hoje")

    def test_sem_ninguem_definido_cobrem_as_socias(self):
        self.client.force_login(self.anna)
        self.assertContains(self.client.get("/gestao/"), "vão para <b>as sócias</b>")
        self.client.post(reverse("g_absence"), {"a": "start"})
        self.assertIsNone(self._ausencia().cover_id)
        self.assertEqual(self._avisos(self.admin, "cobertura"), ["Anna não trabalha hoje"])
        self.assertEqual(self._avisos(self.rec, "cobertura"), [])
        self.client.force_login(self.admin)
        painel = self.client.get("/gestao/")
        for texto in ["Cobertura de hoje · carteira de Anna", "Você cobre.", "Restrição na conta: dia 1", "nunca abriu LIVE: encerramento até o D14"]:
            self.assertContains(painel, texto)
        self.client.force_login(self.rec)
        self.assertNotContains(self.client.get("/gestao/"), "Cobertura de hoje")
        self.assertEqual(self.client.get(reverse("g_creator", args=[self.novato.pk])).status_code, 404)

    def test_socias_veem_a_cobertura_mesmo_quando_quem_cobre_e_a_recrutadora(self):
        self._define_cobertura(self.rec)
        self.client.force_login(self.anna)
        self.client.post(reverse("g_absence"), {"a": "start"})
        self.client.force_login(self.admin)
        painel = self.client.get("/gestao/")
        self.assertContains(painel, "Cobertura de hoje · carteira de Anna")
        self.assertContains(painel, "Cobre: <b>Fernanda</b>.")

    def test_socias_marcam_a_ausencia_trocam_quem_cobre_e_veem_os_dias_pulados(self):
        self.client.force_login(self.admin)
        url, hoje = reverse("g_portfolios"), timezone.localdate()
        r = self.client.post(url, {"a": "absence_start", "manager": self.anna.pk, "day": hoje.isoformat()}, follow=True)
        self.assertContains(r, f"Anna não trabalha em {hoje:%d/%m}. Cobre: as sócias.")
        self.assertContains(r, "não trabalha hoje")
        self.assertContains(r, "<b class=\"num\">1</b> dia<br>")  # dias sem trabalhar no mês
        # trocar quem cobre no próprio dia vale para a ausência já marcada
        self._define_cobertura(self.rec)
        self.assertEqual(self._ausencia().cover_id, self.rec.pk)
        self.assertContains(self.client.get(url), "Cobre: Fernanda")
        with as_user(self.rec):
            self.assertEqual(Creator.objects.count(), 3)
        # só sócia ou recrutadora cobre
        self.assertContains(self._define_cobertura(self.bia), "Quem cobre precisa ser uma sócia ou uma recrutadora ativa")
        self.assertEqual(self._ausencia().cover_id, self.rec.pk)
        # desfazer, e marcar um dia que ainda vai chegar
        self.client.post(url, {"a": "absence_cancel", "absence": self._ausencia().pk})
        tela = self.client.get(url)
        self.assertContains(tela, "trabalhando")
        self.assertContains(tela, "<small class=\"muted\">nenhum</small>")  # ausência desfeita não conta como dia pulado
        depois = hoje + dt.timedelta(days=3)
        self.assertContains(self.client.post(url, {"a": "absence_start", "manager": self.anna.pk, "day": depois.isoformat()}, follow=True),
                            f"Marcada: {depois:%d/%m}")
        with as_user(self.rec):
            self.assertEqual(Creator.objects.count(), 0)  # ausência futura ainda não dá acesso
        ontem = hoje - dt.timedelta(days=1)
        self.assertContains(self.client.post(url, {"a": "absence_start", "manager": self.anna.pk, "day": ontem.isoformat()}, follow=True),
                            "só pode ser marcada para hoje")
        # recrutadora não marca ausência de ninguém
        self.client.force_login(self.rec)
        self.assertEqual(self.client.post(reverse("g_absence"), {"a": "start"}).status_code, 403)


class CoberturaNoBancoTests(CarteirasBase):
    """Sem nenhum filtro da aplicação: só o RLS protege."""

    def _ausencia(self, day=None, cover="rec", **kw):
        with system_context():
            return Absence.objects.create(agency=self.ag, manager=self.anna, day=day or timezone.localdate(),
                                          cover=self.rec if cover == "rec" else cover, created_by=self.admin, **kw)

    def test_quem_cobre_enxerga_a_carteira_so_no_dia_e_so_registra_contato(self):
        with system_context():
            AccessCode.objects.create(creator=self.a1, code="ABCD2345", created_by=self.anna, expires_at=timezone.now() + dt.timedelta(days=7))
        with as_user(self.rec):
            self.assertEqual(Creator.objects.count(), 0)
        self._ausencia()
        with as_user(self.rec):
            self.assertEqual(set(Creator.objects.values_list("username", flat=True)), {"anna.um", "anna.dois", "novato.demo"})
            self.assertEqual(Note.objects.filter(creator=self.a1).count(), 1)  # lê o histórico para dar contexto
            self.assertEqual(AccessCode.objects.count(), 0)  # nunca lê o código de acesso ao app
            self.assertEqual(Absence.objects.count(), 1)
            Contact.objects.create(creator=self.a1, user=self.rec, template_code="NR-24H", body="x")
            Reply.objects.create(creator=self.a1, kind="respondeu", author=self.rec)
            Note.objects.create(creator=self.a1, author=self.rec, body="cobertura")
            self.assertEqual(Creator.objects.filter(pk=self.a1.pk).update(display_name="mudou"), 0)  # não edita o cadastro
            self.assertEqual(Note.objects.filter(creator=self.a1).delete()[0], 0)  # não apaga nada
            for proibido in (lambda: Reminder.objects.create(creator=self.a1, text="x", due_date=timezone.localdate()),
                             lambda: AccountCase.objects.create(creator=self.a1, kind="restricao"),
                             lambda: Contact.objects.create(creator=self.b1, user=self.rec, body="x"),
                             lambda: Absence.objects.create(agency=self.ag, manager=self.bia, day=timezone.localdate(), cover=self.rec)):
                with self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        proibido()
        with as_user(self.bia):  # outra gestora continua sem ver
            self.assertFalse(Creator.objects.filter(pk=self.a1.pk).exists())
            self.assertEqual(Absence.objects.count(), 0)

    def test_fora_do_dia_cancelada_ou_sem_o_papel_nao_ha_acesso(self):
        hoje = timezone.localdate()
        self._ausencia(day=hoje - dt.timedelta(days=1))
        self._ausencia(day=hoje + dt.timedelta(days=1))
        self._ausencia(cancelled_at=timezone.now())
        with as_user(self.rec):
            self.assertEqual(Creator.objects.count(), 0)
        self._ausencia()
        with as_user(self.rec):
            self.assertEqual(Creator.objects.count(), 3)
        with system_context():
            Membership.objects.filter(user=self.rec).update(active=False)  # deixou de ser recrutadora
        with as_user(self.rec):
            self.assertEqual(Creator.objects.count(), 0)
        with system_context():
            streamer = F.user()
            Absence.objects.filter(manager=self.anna, day=hoje, cancelled_at__isnull=True).update(cover=streamer)
        with as_user(streamer):  # quem não é sócia nem recrutadora nunca cobre, mesmo que o nome esteja na ausência
            self.assertEqual(Creator.objects.count(), 0)

    def test_gestora_nao_escolhe_quem_enxerga_a_carteira(self):
        hoje = timezone.localdate()

        def tenta(**campos):
            with transaction.atomic():
                return Absence.objects.create(agency=self.ag, **{"manager": self.anna, "day": hoje, "cover": None, **campos})

        with as_user(self.anna):
            for campos in ({"cover": self.rec},  # as sócias não definiram a Fernanda para cobri-la
                           {"manager": self.bia},  # ausência de outra gestora
                           {"day": hoje + dt.timedelta(days=1)}):  # a gestora só avisa o dia de hoje
                with self.assertRaises(DatabaseError):
                    tenta(**campos)
            a = tenta()  # a própria ausência de hoje, com as sócias cobrindo: pode
            with self.assertRaises(DatabaseError):  # depois, só pode cancelar
                with transaction.atomic():
                    Absence.objects.filter(pk=a.pk).update(cover=self.rec)
            self.assertEqual(Absence.objects.filter(pk=a.pk).update(cancelled_at=timezone.now()), 1)
        with system_context():
            absence.set_default_cover(self.ag, self.anna, self.rec)  # agora as sócias definiram
        with as_user(self.anna):
            self.assertEqual(tenta(cover=self.rec).cover_id, self.rec.pk)
        with as_user(self.rec):
            self.assertEqual(Creator.objects.count(), 3)
            with self.assertRaises(DatabaseError):  # quem cobre não mexe na ausência
                with transaction.atomic():
                    Absence.objects.create(agency=self.ag, manager=self.rec, day=hoje, cover=self.rec)
