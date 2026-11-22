"""Fila de ação: graduação pela regra do TikTok e item que sai da fila depois do "Enviei" (correções de 14/11/2026)."""
import datetime as dt

from django.test import TestCase
from django.urls import reverse

from core.access import assign_manager
from core.models import AgencySettings
from core.rls import set_context, system_context
from crm.models import Creator
from web import services as S

from . import factories as F

# As fábricas contam a entrada a partir de 28/09/2026; a fila é calculada nessa mesma data.
HOJE = dt.date(2026, 9, 28)


def _fila(ag, *creators, today=HOJE):
    with system_context():
        return S.action_queue(Creator.objects.filter(pk__in=[c.pk for c in creators]), ag, today=today)


def _codigos(itens, creator):
    return {i.code for i in itens if i.creator.pk == creator.pk}


class GraduacaoNaFilaTests(TestCase):
    """Graduação = 80 mil diamantes em UM mês, dentro dos 3 primeiros meses de casa. Nunca a soma desde a entrada."""

    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        setembro = (dt.date(2026, 9, 1), dt.date(2026, 9, 27))
        # na janela (41 dias de casa) e perto: 70 mil em setembro
        cls.perto = F.creator(cls.ag, username="perto.demo", joined_days_ago=40)
        F.snapshot(cls.perto, *setembro, diamonds=70_000, hours=30, valid_days=12, streams=14)
        # na janela, mas o mês está longe: 40 mil em agosto + 35 mil em setembro (a soma antiga dava 75 mil e acendia o alerta)
        cls.soma = F.creator(cls.ag, username="soma.demo", joined_days_ago=40)
        F.snapshot(cls.soma, dt.date(2026, 8, 19), dt.date(2026, 8, 31), diamonds=40_000, hours=20, valid_days=8, streams=9)
        F.snapshot(cls.soma, *setembro, diamonds=35_000, hours=20, valid_days=9, streams=10)
        # já graduou neste mês
        cls.graduou = F.creator(cls.ag, username="graduou.demo", joined_days_ago=40)
        F.snapshot(cls.graduou, *setembro, diamonds=85_000, hours=40, valid_days=15, streams=18)
        # fora da janela (200 dias de casa)
        cls.veterano = F.creator(cls.ag, username="veterano.demo", joined_days_ago=200)
        F.snapshot(cls.veterano, *setembro, diamonds=70_000, hours=30, valid_days=12, streams=14)
        set_context()

    def tearDown(self):
        set_context()

    # 28/09 é a última semana do mês: o aviso "perto de graduar" vira o item "Quase lá", com mensagem (passo 4.3)
    def test_conta_os_diamantes_do_mes_dentro_da_janela(self):
        fila = _fila(self.ag, self.perto, self.soma, self.graduou, self.veterano)
        self.assertIn("quase_la", _codigos(fila, self.perto))
        self.assertNotIn("perto_graduar", _codigos(fila, self.perto))
        for c in (self.soma, self.graduou, self.veterano):  # ninguém deles está perto de graduar no mês
            self.assertFalse([i for i in fila if i.creator.pk == c.pk and (i.code == "perto_graduar" or i.template == "QUASE-GRAD")], c.username)
        # soma.demo tem 35 mil de 40 mil do próximo Tier: "Quase lá" do nível, não da graduação
        self.assertEqual([i.template for i in fila if i.creator.pk == self.soma.pk and i.code == "quase_la"], ["QUASE-NIVEL"])
        item = next(i for i in fila if i.creator.pk == self.perto.pk and i.code == "quase_la")
        self.assertEqual(item.template, "QUASE-GRAD")
        self.assertIn("70.000 de 80.000 diamantes neste mês", item.detail)
        self.assertIn("faltam 10.000", item.detail)

    def test_fora_da_ultima_semana_continua_o_aviso_perto_de_graduar(self):
        fila = _fila(self.ag, self.perto, today=dt.date(2026, 9, 23))
        self.assertIn("perto_graduar", _codigos(fila, self.perto))
        self.assertNotIn("quase_la", _codigos(fila, self.perto))

    def test_valores_vem_da_configuracao(self):
        with system_context():
            AgencySettings.objects.filter(agency=self.ag).update(graduation_window_days=30)
        self.assertNotIn("quase_la", _codigos(_fila(self.ag, self.perto), self.perto))
        with system_context():
            AgencySettings.objects.filter(agency=self.ag).update(graduation_window_days=90, graduation_diamonds=40_000)
        fila = _fila(self.ag, self.soma)
        self.assertIn("QUASE-GRAD", [i.template for i in fila if i.code == "quase_la"])  # 35 mil é 87% de 40 mil


class EnvieiTiraDaFilaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        cls.c = F.creator(cls.ag, username="parado.demo")
        assign_manager(cls.c, cls.gestora)
        # fez LIVE até 03/09 e parou: 11 dias sem LIVE na leitura de 14/09
        F.snapshot(cls.c, dt.date(2026, 9, 1), dt.date(2026, 9, 3), diamonds=2_000, hours=5, valid_days=2, streams=2)
        F.snapshot(cls.c, dt.date(2026, 9, 1), dt.date(2026, 9, 14), diamonds=2_000, hours=5, valid_days=2, streams=2)
        set_context()

    def tearDown(self):
        set_context()

    def test_item_sai_da_fila_so_depois_do_enviei(self):
        hoje = dt.date(2026, 9, 14)
        item = next(i for i in _fila(self.ag, self.c, today=hoje) if i.code == "regua_4")
        self.assertEqual(item.template, "REG-04")
        self.client.force_login(self.gestora)
        self.client.get(reverse("g_open", args=[self.c.pk, "REG-04"]))
        self.assertIn("regua_4", _codigos(_fila(self.ag, self.c, today=hoje), self.c))  # abrir não tira da fila
        self.client.post(reverse("g_sent", args=[self.c.pk, "REG-04"]))
        self.assertNotIn("regua_4", _codigos(_fila(self.ag, self.c, today=hoje), self.c))

    def test_fila_mostra_mensagem_pronta_e_botoes(self):
        with system_context():
            itens = _fila(self.ag, self.c, today=dt.date(2026, 9, 14))
            S.fill_queue_messages(itens, self.ag)
        item = next(i for i in itens if i.code == "regua_4")
        self.assertTrue(item.text)
        self.assertEqual(item.group_url, "")

    def test_enviar_no_whatsapp_com_numero_abre_a_conversa_com_a_mensagem(self):
        """Card novo de 19/11: com o número do criador, o botão abre wa.me com a mensagem escrita; sem número, o caminho
        de antes (g_open: grupo individual ou WhatsApp sem número). Abrir não registra contato."""
        from urllib.parse import quote

        from crm.models import CreatorPrivate

        with system_context():
            itens = _fila(self.ag, self.c, today=dt.date(2026, 9, 14))
            S.fill_queue_messages(itens, self.ag)
        sem = next(i for i in itens if i.code == "regua_4")
        self.assertEqual(getattr(sem, "wa_url", ""), "")
        with system_context():
            CreatorPrivate.objects.update_or_create(creator=self.c, defaults={"whatsapp": "(11) 98888-7777"})
            itens = _fila(self.ag, self.c, today=dt.date(2026, 9, 14))
            S.fill_queue_messages(itens, self.ag)
        com = next(i for i in itens if i.code == "regua_4")
        self.assertTrue(com.wa_url.startswith("https://wa.me/5511988887777?text="))
        self.assertIn(quote(com.text), com.wa_url)
        # o card do Dashboard (montado direto, para não depender do dia da semana: domingo a fila não traz envios)
        from django.template.loader import render_to_string

        html = render_to_string("gestao/_queue_row.html", {"i": com, "p": "q", "n": 1, "can_defer": True})
        for texto in ['class="qmsg"', 'aria-label="Copiar mensagem"', 'aria-label="Ficha"', 'aria-label="Adiar"',
                      "Marcar como enviada", "Enviar no WhatsApp", 'href="https://wa.me/5511988887777?text=']:
            self.assertIn(texto, html)
        self.assertNotIn("ver mensagem", html)
        self.assertNotIn("{#", html)  # nenhuma anotação interna aparece como texto
        sem_html = render_to_string("gestao/_queue_row.html", {"i": sem, "p": "q", "n": 2, "can_defer": True})
        self.assertIn(reverse("g_open", args=[self.c.pk, "REG-04"]), sem_html)  # sem número: o caminho de antes
        # decisão de 22/11: com o link do grupo cadastrado, o grupo vem primeiro, mesmo havendo número
        with system_context():
            CreatorPrivate.objects.filter(creator=self.c).update(whatsapp_group_url="https://chat.whatsapp.com/grupo-demo")
            itens = _fila(self.ag, self.c, today=dt.date(2026, 9, 14))
            S.fill_queue_messages(itens, self.ag)
        grupo = next(i for i in itens if i.code == "regua_4")
        self.assertEqual(grupo.wa_url, "")
        grupo_html = render_to_string("gestao/_queue_row.html", {"i": grupo, "p": "q", "n": 3, "can_defer": True})
        self.assertIn(reverse("g_open", args=[self.c.pk, "REG-04"]), grupo_html)  # g_open leva ao grupo individual
        self.assertNotIn("wa.me/5511988887777", grupo_html)
