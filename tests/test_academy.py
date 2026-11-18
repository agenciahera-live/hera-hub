"""Hera Academy (etapa 3, passo 3.2): módulos que abrem por nível e por marco, liberação pela gestão e aula recomendada.

Regras da visão ("Página educacional"): o que decide a abertura é o nível e o marco, não o tempo de casa; quem chega
ao Nível 3 abre tudo; a gestão libera qualquer módulo antes da hora; o que não abriu diz quando abre; sem "obrigatória";
a escolha da gestora vence a sugestão automática."""
import datetime as dt
import re

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.rls import set_context, system_context
from crm.models import Note
from data import engine as E
from data.models import MonthlyResult
from engage import academy as A
from engage.models import Course, Lesson, LessonPick, ModuleRelease, Notification
from engage.tom import verificar_tom

from . import factories as F


def _texto(resposta):
    html = resposta.content.decode()
    html = re.sub(r"<head>.*?</head>|<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


class HeraAcademyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        cls.outra = F.user(role="gestora", ag=cls.ag)
        cls.admin = F.user(role="admin", ag=cls.ag)
        cls.u_novo, cls.u_vet = F.user(), F.user()
        cls.novo = F.creator(cls.ag, username="novo.demo", streamer_user=cls.u_novo)
        cls.novo.joined_at = timezone.now() - dt.timedelta(days=3)
        cls.novo.save()
        cls.vet = F.creator(cls.ag, username="vet.demo", streamer_user=cls.u_vet)
        for c in (cls.novo, cls.vet):
            assign_manager(c, cls.gestora)
        today = E.tiktok_today()
        cls.m0 = E.month_start(today)
        cls.today = today
        F.snapshot(cls.vet, cls.m0, today, diamonds=3000, hours=4, valid_days=2, streams=3)

        def mod(order, title, opens_on, level=None, lessons=()):
            co = Course.objects.create(agency=cls.ag, title=title, order=order, opens_on=opens_on, opens_level=level)
            out = [Lesson.objects.create(course=co, title=t, video_url="https://example.com/v", order=i, topic=topic,
                                         about_battles=battle) for i, (t, topic, battle) in enumerate(lessons)]
            return co, out

        cls.comecar, cls.l_comecar = mod(0, "1. Começar", "acesso", lessons=[("Abrir a LIVE", "", False)])
        cls.batalhas, cls.l_batalhas = mod(3, "4. Batalhas", "primeira_live", lessons=[("Primeira batalha", "batalhas", True)])
        cls.rotina, cls.l_rotina = mod(4, "5. Rotina e crescimento", "dia15", lessons=[("Rotina fixa", "rotina", False)])
        cls.avancado, cls.l_avancado = mod(6, "7. Estratégia avançada", "nivel", 3, lessons=[("Planejamento", "", False)])
        cls.extra, cls.l_extra = mod(7, "Curso extra", "gestao", lessons=[("Finanças", "", False)])
        set_context()

    def tearDown(self):
        set_context()

    def _mods(self, c):
        with system_context():
            return {m.course.pk: m for m in A.modules(c, include_hidden=True)}

    # ------------------------------------------------------------ regras de abertura
    def test_novato_sem_live_abre_so_o_primeiro_acesso_e_cada_fechado_diz_quando_abre(self):
        m = self._mods(self.novo)
        self.assertTrue(m[self.comecar.pk].open)
        self.assertFalse(m[self.batalhas.pk].open)
        self.assertEqual(m[self.batalhas.pk].hint, "Abre depois da sua 1ª LIVE.")
        self.assertEqual(m[self.rotina.pk].hint, "Abre quando os seus primeiros 14 dias terminarem.")
        self.assertEqual(m[self.avancado.pk].hint, "Abre no Nível 3.")
        for mod in m.values():
            self.assertEqual(verificar_tom(mod.hint), [], mod.hint)

    def test_primeira_live_abre_o_modulo_de_batalhas(self):
        F.snapshot(self.novo, self.m0, self.today, hours=1, valid_days=1)
        self.assertTrue(self._mods(self.novo)[self.batalhas.pk].open)
        self.assertFalse(self._mods(self.novo)[self.rotina.pk].open)  # os 14 dias ainda não terminaram

    def test_depois_do_d14_abre_rotina_e_monetizacao(self):
        m = self._mods(self.vet)  # entrou há mais de 14 dias e já fez LIVE
        self.assertTrue(m[self.batalhas.pk].open)
        self.assertTrue(m[self.rotina.pk].open)
        self.assertFalse(m[self.avancado.pk].open)

    def test_quem_chega_ao_nivel_3_abre_tudo_menos_curso_extra(self):
        with system_context():
            tier3 = next(r for r in E.tier_rules(self.ag) if r.tier == 3)
        F.snapshot(self.novo, self.m0, self.today, diamonds=tier3.min_diamonds, hours=2, valid_days=1)
        m = self._mods(self.novo)  # D3, mas no Nível 3 pelo mês: vem de outra agência
        self.assertTrue(all(m[c.pk].open for c in (self.comecar, self.batalhas, self.rotina, self.avancado)))
        self.assertFalse(m[self.extra.pk].open)

    def test_nivel_do_mes_fechado_tambem_abre(self):
        with system_context():
            MonthlyResult.objects.create(creator=self.vet, month=E.prev_month(self.today), diamonds=90_000, source="task", tier=3)
        self.assertTrue(self._mods(self.vet)[self.avancado.pk].open)

    def test_curso_extra_nao_aparece_para_o_criador_sem_liberacao(self):
        self.client.force_login(self.u_vet)
        r = self.client.get(reverse("academy"))
        self.assertNotContains(r, "Curso extra")
        self.assertEqual(self.client.get(reverse("lesson", args=[self.l_extra[0].pk])).status_code, 404)

    # ------------------------------------------------------------ telas do criador
    def test_aula_fechada_leva_de_volta_com_o_motivo(self):
        self.client.force_login(self.u_novo)
        r = self.client.get(reverse("lesson", args=[self.l_batalhas[0].pk]), follow=True)
        self.assertRedirects(r, reverse("academy"))
        self.assertContains(r, "Abre depois da sua 1ª LIVE.")
        r = self.client.post(reverse("lesson", args=[self.l_batalhas[0].pk]))  # nem marcar como assistida
        with system_context():
            self.assertFalse(self.novo.lesson_progress.exists())

    def test_pagina_da_hera_academy_sem_palavras_vetadas_e_sem_obrigatoria(self):
        for u in (self.u_novo, self.u_vet):
            self.client.force_login(u)
            r = self.client.get(reverse("academy"))
            self.assertEqual(r.status_code, 200)
            texto = _texto(r)
            self.assertIn("Hera Academy", texto)
            self.assertNotIn("brigatóri", texto)
            self.assertEqual(verificar_tom(texto), [])

    def test_botao_da_aula_de_batalha_so_aparece_quando_a_aula_abriu(self):
        self.client.force_login(self.u_novo)
        self.assertNotContains(self.client.get(reverse("battle_new")), "Entenda a batalha oficial")
        self.client.force_login(self.u_vet)
        self.assertContains(self.client.get(reverse("battle_new")), "Entenda a batalha oficial")

    # ------------------------------------------------------------ gestão
    def _acao(self, user, c, **data):
        self.client.force_login(user)
        return self.client.post(reverse("g_creator_action", args=[c.pk]), data)

    def test_gestora_libera_modulo_antes_da_hora(self):
        self._acao(self.gestora, self.novo, a="module_release", course=self.batalhas.pk)
        self.assertTrue(self._mods(self.novo)[self.batalhas.pk].open)
        with system_context():
            self.assertTrue(Note.objects.filter(creator=self.novo, body__contains="liberado antes da hora").exists())
            self.assertTrue(Notification.objects.filter(user=self.u_novo, kind="academy").exists())
        self.client.force_login(self.u_novo)
        self.assertEqual(self.client.get(reverse("lesson", args=[self.l_batalhas[0].pk])).status_code, 200)
        # desfazer: volta a abrir pela regra
        self._acao(self.gestora, self.novo, a="module_unrelease", course=self.batalhas.pk)
        self.assertFalse(self._mods(self.novo)[self.batalhas.pk].open)

    def test_curso_extra_liberado_aparece_para_o_criador(self):
        self._acao(self.gestora, self.vet, a="module_release", course=self.extra.pk)
        self.client.force_login(self.u_vet)
        r = self.client.get(reverse("academy"))
        self.assertContains(r, "Curso extra")
        self.assertContains(r, "liberado pela Hera")

    def test_gestora_de_outra_carteira_nao_libera(self):
        r = self._acao(self.outra, self.novo, a="module_release", course=self.batalhas.pk)
        self.assertEqual(r.status_code, 404)
        with system_context():
            self.assertFalse(ModuleRelease.objects.filter(creator=self.novo).exists())

    def test_escolha_da_gestora_vence_a_sugestao_automatica(self):
        with system_context():
            auto = A.recommended(self.vet)
        self.assertNotEqual(auto["by"], "gestao")
        self._acao(self.gestora, self.vet, a="lesson_pick", lesson=self.l_rotina[0].pk)
        with system_context():
            rec = A.recommended(self.vet)
        self.assertEqual((rec["lesson"], rec["by"]), (self.l_rotina[0], "gestao"))
        self.client.force_login(self.u_vet)
        self.assertContains(self.client.get("/"), "Rotina fixa")
        # vazio volta para a sugestão automática
        self._acao(self.gestora, self.vet, a="lesson_pick", lesson="")
        with system_context():
            self.assertFalse(LessonPick.objects.filter(creator=self.vet).exists())

    def test_nao_escolhe_aula_que_ainda_nao_abriu(self):
        self._acao(self.gestora, self.novo, a="lesson_pick", lesson=self.l_avancado[0].pk)
        with system_context():
            self.assertFalse(LessonPick.objects.filter(creator=self.novo).exists())

    def test_ficha_mostra_os_modulos_e_o_botao_liberar(self):
        self.client.force_login(self.gestora)
        r = self.client.get(reverse("g_creator", args=[self.novo.pk]))
        self.assertContains(r, "Hera Academy")
        self.assertContains(r, "Liberar agora")
        self.assertContains(r, "Abre depois da sua 1ª LIVE.")

    # ------------------------------------------------------------ aula recomendada pelo ponto mais fraco
    def test_ponto_mais_fraco_rotina(self):
        with system_context():
            MonthlyResult.objects.create(creator=self.vet, month=E.prev_month(self.today), diamonds=3000,
                                         live_seconds=200 * 3600, valid_days=28, battles=0, source="task", tier=1)
            snap = E.latest_in_month(self.vet, self.m0)
            if (snap.period_end - self.m0).days < 2:
                self.skipTest("começo do mês: a comparação com o mês passado ainda não vale")
            rec = A.recommended(self.vet)
        self.assertEqual((rec["by"], rec["lesson"]), ("ponto", self.l_rotina[0]))
        self.assertEqual(verificar_tom(rec["why"]), [])


class IsolamentoHeraAcademyTests(TestCase):
    """O criador só lê as próprias liberações e a própria aula escolhida (RLS)."""

    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.u1, cls.u2 = F.user(), F.user()
        cls.c1 = F.creator(cls.ag, streamer_user=cls.u1)
        cls.c2 = F.creator(cls.ag, streamer_user=cls.u2)
        co = Course.objects.create(agency=cls.ag, title="Extra", opens_on="gestao")
        ls = Lesson.objects.create(course=co, title="Aula", video_url="https://example.com/v")
        ModuleRelease.objects.create(creator=cls.c2, course=co)
        LessonPick.objects.create(creator=cls.c2, lesson=ls)
        set_context()

    def tearDown(self):
        set_context()

    def test_streamer_nao_le_liberacao_nem_escolha_de_outro(self):
        set_context(user_id=self.u1.pk)
        self.assertEqual(ModuleRelease.objects.count(), 0)
        self.assertEqual(LessonPick.objects.count(), 0)
        set_context(user_id=self.u2.pk)
        self.assertEqual(ModuleRelease.objects.count(), 1)
        self.assertEqual(LessonPick.objects.count(), 1)

    def test_streamer_nao_se_libera_sozinho(self):
        from django.db import DatabaseError, transaction

        set_context(user_id=self.u1.pk)
        co = Course.objects.get(title="Extra")
        with self.assertRaises(DatabaseError), transaction.atomic():
            ModuleRelease.objects.create(creator=self.c1, course=co)
