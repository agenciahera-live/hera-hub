"""Estado da semana, segmento, prioridade e sinais (docs/regras-estado-prioridade.md) e as regras da fila do dia (passo 2.4)."""
import datetime as dt

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.access import assign_manager
from core.models import AgencySettings
from core.rls import set_context, system_context
from crm.models import Contact, Creator, CreatorPrivate, StopReason
from data import states
from data.models import MonthlyResult
from engage.models import BattleRequest, MessageTemplate, SupportTicket
from web import services as S

from . import factories as F

HOJE = dt.date(2026, 9, 28)  # segunda-feira; a semana analisada é 21/09 a 27/09
FINS = [dt.date(2026, 9, 6), dt.date(2026, 9, 13), dt.date(2026, 9, 20), dt.date(2026, 9, 27)]  # fim de w1, w2, w3, w4


def semanas(c, diamonds, hours=(8, 8, 8, 8), days=(5, 5, 5, 5), battles=(20, 20, 20, 20), fans=None):
    """Cria os snapshots acumulados de setembro para dar estes valores em w1, w2, w3 e w4."""
    tot = [0, 0, 0, 0, 0]
    for i, fim in enumerate(FINS):
        tot = [tot[0] + diamonds[i], tot[1] + hours[i], tot[2] + days[i], tot[3] + battles[i], tot[4] + (fans[i] if fans else 0)]
        F.snapshot(c, dt.date(2026, 9, 1), fim, diamonds=tot[0], hours=tot[1], valid_days=tot[2], streams=tot[2], battles=tot[3],
                   **({"new_fans": tot[4]} if fans else {}))


class EstadoDaSemanaTests(TestCase):
    def setUp(self):
        set_context(system=True)
        self.ag = F.agency()

    def tearDown(self):
        set_context()

    def _estado(self, c):
        c = Creator.objects.get(pk=c.pk)
        return states.week_state(c, list(c.snapshots.all()), HOJE)

    def _novo(self, **kw):
        return F.creator(self.ag, joined_days_ago=kw.pop("dias", 200), **kw)

    def test_os_oito_estados_na_ordem_do_script(self):
        casos = {
            "queda": dict(diamonds=(10000, 10000, 10000, 5000)),
            "subindo": dict(diamonds=(3000, 3000, 3000, 6000)),
            "sem_live": dict(diamonds=(5000, 5000, 0, 0), hours=(10, 10, 0, 0), days=(5, 5, 0, 0), battles=(0, 0, 0, 0)),
            "horas_sem_retorno": dict(diamonds=(1000, 1000, 1000, 1000), hours=(12, 12, 12, 12)),
            "irregular": dict(diamonds=(3000, 3000, 3000, 3000), hours=(4, 4, 4, 4), days=(2, 2, 2, 2)),
            "estavel": dict(diamonds=(3000, 3000, 3000, 3000)),
        }
        for esperado, dados in casos.items():
            c = self._novo()
            semanas(c, **dados)
            self.assertEqual(self._estado(c).state, esperado, esperado)
        novo = self._novo(dias=10)
        semanas(novo, diamonds=(0, 0, 1000, 1000), hours=(0, 0, 4, 4), days=(0, 0, 2, 2))
        e = self._estado(novo)
        self.assertEqual((e.state, e.priority, e.pct), ("novo", 2, None))  # normal zero: variação indefinida
        inativo = self._novo()
        F.snapshot(inativo, dt.date(2026, 8, 1), dt.date(2026, 8, 20), diamonds=9000, hours=20, valid_days=8, streams=8)
        F.snapshot(inativo, dt.date(2026, 9, 1), dt.date(2026, 9, 27))
        e = self._estado(inativo)
        self.assertEqual((e.state, e.since), ("inativo", 39))
        self.assertEqual(self._estado(self._novo()).since, states.NEVER)  # nunca fez LIVE

    def test_queda_vem_antes_de_irregular(self):
        c = self._novo()
        semanas(c, diamonds=(10000, 10000, 10000, 2000), hours=(8, 8, 8, 3), days=(5, 5, 5, 2))
        e = self._estado(c)
        self.assertEqual((e.state, e.pct, e.base, e.hours_dropped), ("queda", -80, 10000, True))

    def test_cortes_do_diagnostico_usam_media_e_dois_dias(self):
        """Horas: abaixo de 0,7 × a MÉDIA das 3 semanas anteriores. Dias: 2 a menos que a média. Basta um dos dois."""
        casos = [
            (dict(hours=(10, 10, 10, 7.5), days=(5, 5, 5, 5)), False),   # 7,5h não é menos que 7h
            (dict(hours=(10, 10, 10, 6.9), days=(5, 5, 5, 5)), True),    # horas caíram
            (dict(hours=(4, 4, 22, 9), days=(5, 5, 5, 5)), False),       # média 10h (a mediana seria 4h): 9h não caiu
            (dict(hours=(8, 8, 8, 8), days=(7, 7, 7, 5)), True),         # de 7 para 5 dias: -29%, mas são 2 dias a menos
            (dict(hours=(8, 8, 8, 8), days=(7, 7, 7, 6)), False),
        ]
        for dados, esperado in casos:
            c = self._novo()
            semanas(c, diamonds=(10000, 10000, 10000, 5000), **dados)
            self.assertEqual(self._estado(c).hours_dropped, esperado, dados)

    def test_segmento_nao_e_grupo_e_define_a_prioridade(self):
        top = self._novo()
        semanas(top, diamonds=(30000, 30000, 30000, 30000))  # 120 mil até 27/09 → projeção de 133 mil
        e = self._estado(top)
        self.assertEqual((e.segment, e.segment_label, e.state, e.priority), ("top", "Top", "estavel", 2))
        pelo_mes_anterior = self._novo()
        semanas(pelo_mes_anterior, diamonds=(3000, 3000, 3000, 3000))
        MonthlyResult.objects.create(creator=pelo_mes_anterior, month=dt.date(2026, 8, 1), diamonds=150_000, source="backstage", tier=4)
        self.assertEqual(self._estado(pelo_mes_anterior).segment, "top")  # vale o maior entre o mês anterior e a projeção
        dev = self._novo()
        semanas(dev, diamonds=(3000, 3000, 3000, 3000))
        e = self._estado(dev)
        self.assertEqual((e.segment, e.priority), ("desenvolvimento", 3))
        base = self._novo()
        semanas(base, diamonds=(300, 300, 300, 300))
        self.assertEqual(self._estado(base).segment, "base")
        # prioridade 1: Top ou Médio em queda; queda com normal de 5 mil ou mais; subindo forte
        queda_media = self._novo()
        semanas(queda_media, diamonds=(10000, 10000, 10000, 5000))
        e = self._estado(queda_media)
        self.assertEqual((e.segment, e.priority), ("medio", 1))
        queda_pequena = self._novo()
        semanas(queda_pequena, diamonds=(2500, 2500, 2500, 1000))
        e = self._estado(queda_pequena)
        self.assertEqual((e.state, e.segment, e.priority), ("queda", "desenvolvimento", 3))
        subindo_forte = self._novo()
        semanas(subindo_forte, diamonds=(3000, 3000, 3000, 60000))
        self.assertEqual(self._estado(subindo_forte).priority, 1)

    def test_sinais(self):
        c = self._novo()
        semanas(c, diamonds=(30000, 30000, 30000, 30000), hours=(12, 12, 12, 12), days=(4, 4, 4, 4), battles=(1, 1, 1, 1), fans=(3, 3, 3, 0))
        self.assertEqual(self._estado(c).signals, ["Quase sem batalhas", "Fã-clube parado", "4 dias válidos"])
        sem_coluna_de_fas = self._novo()
        semanas(sem_coluna_de_fas, diamonds=(30000, 30000, 30000, 30000))
        self.assertEqual(self._estado(sem_coluna_de_fas).signals, [])  # sem a coluna de fãs, não acusa fã-clube parado


class MensagensDaFilaTests(TestCase):
    def test_todo_modelo_que_a_fila_usa_existe_na_biblioteca(self):
        usados = ["REG-04", "REG-14", "REG-21", "REG-30", "REG-VOLTA", "QUEDA-01", "REC-01", "APO-03", "ANIV-DIA", "ANIV-30",
                  "ROD-APP", "ROD-AULA", "ROD-CAMP", "ROD-PERG", "NR-24H", "NR-2D", "NR-3D", "NR-5D",
                  "ONB-D1-01", "CONVITE-APP", "ONB-D2-04", "DES-D1-04", "DES-D1-05", "ONB-NL-D5", "ONB-NL-D7", "ONB-NL-D10", "ONB-NL-ENC",
                  "META-D10", "META-D10-RISCO", "META-D12", "META-D12-TRANSP", "META-D14", "META-D14-NAO", "ONB-D15-ENC", "TIER-D15"]
        set_context(system=True)
        ag = F.agency()
        existentes = set(MessageTemplate.objects.filter(agency=ag).values_list("code", flat=True))
        set_context()
        self.assertEqual([c for c in usados if c not in existentes], [])


class ContagemDeDiasTests(SimpleTestCase):
    def test_domingo_nao_conta(self):
        sexta, terca = dt.date(2026, 9, 25), dt.date(2026, 9, 29)
        self.assertEqual(S.contact_days(sexta, terca), 3)  # sábado, segunda e terça
        self.assertEqual(S.contact_days(terca, terca), 0)


class FilaDoDiaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.g = F.user(role="gestora", ag=cls.ag)
        set_context()

    def tearDown(self):
        set_context()

    def _criador(self, dados=None, **kw):
        with system_context():
            c = F.creator(self.ag, joined_days_ago=kw.pop("dias", 200), **kw)
            assign_manager(c, self.g)
            if dados is not False:
                semanas(c, **(dados or dict(diamonds=(3000, 3000, 3000, 3000))))
        return c

    def _fila(self, *creators, today=HOJE):
        with system_context():
            q = S.action_queue(Creator.objects.filter(pk__in=[c.pk for c in creators]), self.ag, today=today)
            S.fill_queue_messages(q, self.ag)
        return q

    def _contato(self, c, code, quando):
        with system_context():
            Contact.objects.create(creator=c, user=self.g, template_code=code, body="x",
                                   sent_at=timezone.make_aware(dt.datetime.combine(quando, dt.time(10, 0))))

    # ------------------------------------------------------------ bloco 3: o que vem do dado
    def test_queda_entra_com_o_diagnostico_certo(self):
        horas_mantidas = self._criador(dict(diamonds=(10000, 10000, 10000, 5000)))
        horas_cairam = self._criador(dict(diamonds=(10000, 10000, 10000, 2000), hours=(8, 8, 8, 3), days=(5, 5, 5, 2)))
        q = self._fila(horas_mantidas, horas_cairam)
        a = next(i for i in q if i.creator.pk == horas_mantidas.pk and i.code == "queda")
        b = next(i for i in q if i.creator.pk == horas_cairam.pk and i.code == "queda")
        self.assertEqual((a.code, a.block, a.priority, a.template), ("queda", 3, 1, "QUEDA-01"))
        self.assertIn("Queda de 50% na semana (Médio)", a.title)
        self.assertIn("Horas e dias mantidos", a.detail)
        self.assertEqual((b.code, b.template), ("queda", "APO-03"))
        self.assertIn("a conversa é sobre rotina", b.detail)
        self.assertTrue(a.text and b.text)

    def test_subindo_e_irregular_entram_a_partir_de_quarta(self):
        subindo = self._criador(dict(diamonds=(3000, 3000, 3000, 6000)))
        self.assertNotIn("subindo", [i.code for i in self._fila(subindo)])  # segunda: dia das quedas
        self.assertIn("subindo", [i.code for i in self._fila(subindo, today=dt.date(2026, 9, 30))])

    # ------------------------------------------------------------ bloco 4: rodízio
    def test_rodizio_para_quem_ficou_4_dias_sem_mensagem(self):
        c = self._criador()
        item = next(i for i in self._fila(c) if i.code == "rodizio")
        self.assertEqual((item.block, item.template), (4, "ROD-PERG"))
        self._contato(c, "ROD-PERG", dt.date(2026, 9, 25))  # sexta: sábado e segunda = 2 dias
        self.assertNotIn("rodizio", [i.code for i in self._fila(c)])
        self._contato(c, "ROD-PERG", dt.date(2026, 9, 22))
        with system_context():
            Contact.objects.filter(creator=c, sent_at__date=dt.date(2026, 9, 25)).delete()
        self.assertIn("rodizio", [i.code for i in self._fila(c)])  # terça passada: 5 dias, sem contar o domingo

    def test_rodizio_escolhe_pelo_que_ha_de_novo_sem_repetir(self):
        u = F.user()
        c = self._criador(streamer_user=u)
        self.assertEqual(next(i for i in self._fila(c) if i.code == "rodizio").template, "ROD-APP")
        self._contato(c, "ROD-APP", dt.date(2026, 9, 21))
        self.assertEqual(next(i for i in self._fila(c) if i.code == "rodizio").template, "ROD-PERG")  # não repete o último modelo

    def test_novato_e_quem_esta_sem_live_nao_entram_no_rodizio(self):
        novato = self._criador(False, dias=5)
        parado = self._criador(dict(diamonds=(5000, 5000, 0, 0), hours=(10, 10, 0, 0), days=(5, 5, 0, 0)))
        q = self._fila(novato, parado)
        self.assertNotIn("rodizio", [i.code for i in q])
        self.assertIn("regua_14", [i.code for i in q])  # quem parou segue a régua, não o rodízio

    # ------------------------------------------------------------ regras gerais
    def test_uma_mensagem_por_dia_por_criador(self):
        c = self._criador(dict(diamonds=(10000, 10000, 10000, 5000)))
        with system_context():
            CreatorPrivate.objects.update_or_create(creator=c, defaults={"birth_day": HOJE.day, "birth_month": HOJE.month})
        q = self._fila(c)
        mensagens = [i for i in q if i.is_message]
        self.assertEqual([(i.code, i.block) for i in mensagens], [("aniversario", 2)])  # o que tem data vem antes do dado
        self.assertEqual(q.deferred, 1)  # a queda espera o próximo dia livre
        self.client.force_login(self.g)
        self.client.post(reverse("g_sent", args=[c.pk, "ANIV-DIA"]), {"text": "Parabéns, do jeito que a gestora ajustou"})
        with system_context():
            self.assertEqual(Contact.objects.get(creator=c).body, "Parabéns, do jeito que a gestora ajustou")
        self.assertEqual([i for i in self._fila(c) if i.is_message], [])  # já recebeu a mensagem de hoje

    def test_domingo_nao_traz_envios(self):
        c = self._criador()
        with system_context():
            SupportTicket.objects.create(creator=c, question="Como saco?")
        q = self._fila(c, today=dt.date(2026, 9, 27))
        self.assertTrue(q.sunday)
        self.assertEqual([i.code for i in q], ["duvida"])  # pedidos e dúvidas continuam

    def test_teto_por_gestora_empurra_o_resto_para_amanha(self):
        a, b = self._criador(), self._criador()
        with system_context():
            AgencySettings.objects.filter(agency=self.ag).update(daily_message_cap=1)
        q = self._fila(a, b)
        self.assertEqual((len([i for i in q if i.is_message]), q.overflow), (1, 1))

    def test_ordem_dos_blocos(self):
        queda = self._criador(dict(diamonds=(10000, 10000, 10000, 5000)))
        rodizio = self._criador()
        parado = self._criador(dict(diamonds=(5000, 5000, 0, 0), hours=(10, 10, 0, 0), days=(5, 5, 0, 0)))
        with system_context():
            SupportTicket.objects.create(creator=rodizio, question="Dúvida")
        blocos = [i.block for i in self._fila(queda, rodizio, parado)]
        self.assertEqual(blocos, sorted(blocos))
        self.assertEqual(sorted(set(blocos)), [1, 2, 3, 4])

    # ------------------------------------------------------------ bloco 2: o que tem data
    def test_regua_sem_live_e_data_de_volta(self):
        c = self._criador(dict(diamonds=(5000, 5000, 0, 0), hours=(10, 10, 0, 0), days=(5, 5, 0, 0)))  # última LIVE até 13/09: 14 dias
        item = next(i for i in self._fila(c) if i.code.startswith("regua"))
        self.assertEqual((item.code, item.template, item.block), ("regua_14", "REG-14", 2))
        with system_context():
            sr = StopReason.objects.create(creator=c, reason="viagem", return_date=dt.date(2026, 10, 5))
        self.assertEqual([i for i in self._fila(c) if i.is_message], [])  # silêncio até a data de volta
        with system_context():
            StopReason.objects.filter(pk=sr.pk).update(return_date=dt.date(2026, 9, 20))
        volta = next(i for i in self._fila(c) if i.is_message)
        self.assertEqual((volta.code, volta.template), ("volta", "REG-VOLTA"))

    def test_regua_de_30_dias_pede_decisao_das_socias(self):
        c = self._criador(False)
        with system_context():
            F.snapshot(c, dt.date(2026, 8, 1), dt.date(2026, 8, 20), diamonds=9000, hours=20, valid_days=8, streams=8)
            F.snapshot(c, dt.date(2026, 9, 1), dt.date(2026, 9, 27))
        item = next(i for i in self._fila(c) if i.code.startswith("regua"))
        self.assertEqual((item.code, item.template, item.priority), ("regua_30", "REG-30", 1))
        self.assertIn("sócias", item.detail)

    def test_aniversario_e_batalha_proxima(self):
        c = self._criador()
        em30 = HOJE + dt.timedelta(days=30)
        with system_context():
            CreatorPrivate.objects.update_or_create(creator=c, defaults={"birth_day": em30.day, "birth_month": em30.month})
            BattleRequest.objects.create(creator=c, kind="oficial", date=HOJE + dt.timedelta(days=3), time=dt.time(20, 0), status="aprovada")
        q = self._fila(c)
        self.assertEqual(next(i for i in q if i.code == "aniversario_30").template, "ANIV-30")
        batalha = next(i for i in q if i.code == "batalha_proxima")
        self.assertIn("em 3 dias", batalha.title)
        self.assertIn("Checklist", batalha.detail)

    def test_adiar_exige_motivo_e_tira_o_item_ate_a_data(self):
        c = self._criador(dict(diamonds=(10000, 10000, 10000, 5000)))
        self.client.force_login(self.g)
        url = reverse("g_dismiss", args=[c.pk, "queda"])
        self.assertEqual(self.client.post(url, {"reason": ""}).status_code, 400)
        self.assertIn("queda", [i.code for i in self._fila(c)])
        self.assertEqual(self.client.post(url, {"reason": "Está viajando, falo na volta", "days": "2"}).status_code, 200)
        self.assertNotIn("queda", [i.code for i in self._fila(c)])
        self.assertContains(self.client.get(reverse("g_creator", args=[c.pk])), "Está viajando, falo na volta")  # fica na linha do tempo

    # ------------------------------------------------------------ tabela de tipos, restrição e visita
    def test_todos_os_tipos_estao_declarados_mesmo_os_que_ainda_nao_geram_itens(self):
        for tipo in ["restricao", "visita", "campanha", "rodada_batalhas", "resumo_mes", "quase_la", "nivel_novo", "modulo_concluido",
                     "onboarding", "regua", "aniversario", "rodizio"]:
            self.assertIn(tipo, S.ITEM_TYPES, tipo)
        self.assertTrue(set(S.COLLECTORS) <= set(S.ITEM_TYPES))
        self.assertEqual((S.item_kind("regua_14"), S.item_kind("aniversario_30"), S.item_kind("1a1_atrasado")), ("regua", "aniversario", "1a1_atrasado"))
        self.assertEqual([S.ITEM_TYPES[t][0] for t in ("restricao", "campanha", "quase_la", "rodizio")], [1, 2, 3, 4])
        c = self._criador()
        self.assertEqual(S.QueueItem(c, "campanha", 2, "t", "d").block, 2)  # item novo entra no bloco certo sem mexer na fila

    def test_restricao_fica_no_topo_ate_resolver_e_sobe_para_as_socias_no_4o_dia(self):
        from django.core.management import call_command

        from crm.models import AccountCase
        from engage.models import Notification

        c = self._criador()
        with system_context():
            admin = F.user(role="admin", ag=self.ag)
        self.client.force_login(self.g)
        acao = reverse("g_creator_action", args=[c.pk])
        self.client.post(acao, {"a": "case_open", "kind": "banimento", "note": "Conta banida ontem"})
        self.client.post(acao, {"a": "case_open", "kind": "restricao"})  # já há um caso aberto: não duplica
        with system_context():
            caso = AccountCase.objects.get(creator=c)
        item = self._fila(c)[0]
        self.assertEqual((item.code, item.block, item.priority), ("restricao", 1, 1))
        self.assertIn("Banimento na conta: dia 1", item.title)
        self.assertIn("restricao", [i.code for i in self._fila(c, today=dt.date(2026, 9, 27))])  # aparece também no domingo
        with system_context():
            AccountCase.objects.filter(pk=caso.pk).update(opened_on=timezone.localdate() - dt.timedelta(days=3))
        call_command("rotina_diaria", verbosity=0)
        with system_context():
            self.assertIsNotNone(AccountCase.objects.get(pk=caso.pk).escalated_at)
            self.assertEqual(Notification.objects.filter(user=admin, kind="restricao").count(), 1)
        call_command("rotina_diaria", verbosity=0)
        with system_context():
            self.assertEqual(Notification.objects.filter(user=admin, kind="restricao").count(), 1)  # avisa uma vez só
        self.assertIn("com as sócias", self._fila(c)[0].detail)
        self.assertContains(self.client.get(reverse("g_creator", args=[c.pk])), "com as sócias")
        self.client.post(acao, {"a": "case_resolve", "case": caso.pk, "resolution": "Recurso aceito"})
        self.assertNotIn("restricao", [i.code for i in self._fila(c)])

    def test_sugestao_de_visita_ate_3_por_gestora_na_ordem_e_com_motivo(self):
        from crm.models import Visit

        queda = self._criador(dict(diamonds=(10000, 10000, 10000, 5000)), username="a.queda.demo")
        estaveis = [self._criador(username=f"b.estavel{n}.demo") for n in range(4)]
        parado = self._criador(dict(diamonds=(5000, 5000, 0, 0), hours=(10, 10, 0, 0), days=(5, 5, 0, 0)), username="c.parado.demo")
        visitas = [i for i in self._fila(queda, parado, *estaveis) if i.code == "visita"]
        self.assertEqual(len(visitas), 3)  # no máximo 3 por gestora por dia
        self.assertEqual(visitas[0].creator.pk, queda.pk)  # queda de prioridade 1 vem primeiro
        self.assertIn("caiu 50% na semana", visitas[0].detail)
        self.assertIn("ainda sem visita registrada", visitas[1].detail)
        self.assertNotIn(parado.pk, [i.creator.pk for i in visitas])  # quem está sem LIVE não tem LIVE para visitar
        self.assertFalse(any(i.is_message for i in visitas))  # visita é tarefa: não gasta a mensagem do dia
        # "Visitei" com nota de 1 a 3 tira a pessoa das sugestões
        self.client.force_login(self.g)
        acao = reverse("g_creator_action", args=[queda.pk])
        self.client.post(acao, {"a": "visit", "score": "9"})
        self.client.post(acao, {"a": "visit", "score": "2", "date": HOJE.isoformat(), "note": "Boa interação, áudio baixo"})
        with system_context():
            self.assertEqual(Visit.objects.filter(creator=queda).count(), 1)
        self.assertNotIn(queda.pk, [i.creator.pk for i in self._fila(queda, *estaveis) if i.code == "visita"])
        self.assertContains(self.client.get(reverse("g_creator", args=[queda.pk])), "Visita à LIVE: nota 2")

    def test_visita_as_duas_pontas_7_dias_evita_repetir_14_dias_evita_esquecer(self):
        from crm.models import Visit

        c = self._criador()
        with system_context():
            Visit.objects.create(creator=c, date=HOJE - dt.timedelta(days=6), score=2)
        self.assertEqual([i for i in self._fila(c) if i.code == "visita"], [])  # visitado há menos de 7 dias: não repete
        with system_context():
            Visit.objects.filter(creator=c).update(date=HOJE - dt.timedelta(days=13))
        self.assertEqual([i for i in self._fila(c) if i.code == "visita"], [])  # ainda não chegou a 14 dias
        with system_context():
            Visit.objects.filter(creator=c).update(date=HOJE - dt.timedelta(days=14))
        visita = next(i for i in self._fila(c) if i.code == "visita")
        self.assertIn("há 14 dias sem visita", visita.detail)  # 14 dias ou mais sem visita: volta para a lista

    def test_cadencia_vale_para_a_carteira_inteira_pela_regua_de_sem_live(self):
        """Depois do D15: a pergunta aberta do 4º dia sem LIVE, sem resposta, puxa a cadência; depois do +5 dias, quem recrutou."""
        with system_context():
            rec = F.user(role="recrutadora", ag=self.ag, first_name="Adrielly")
        c = self._criador(dict(diamonds=(5000, 5000, 5000, 0), hours=(10, 10, 10, 0), days=(5, 5, 5, 0)), recruited_by=rec)  # 7 dias sem LIVE
        self.assertEqual(next(i for i in self._fila(c) if i.is_message).template, "REG-04")
        self._contato(c, "REG-04", dt.date(2026, 9, 24))
        cad = next(i for i in self._fila(c) if i.code == "cadencia")
        self.assertEqual((cad.template, cad.block), ("NR-24H", 2))
        self.assertIn("sem resposta", cad.title)
        self.assertIn("ajuste antes de enviar", cad.detail)  # os textos da cadência falam com quem está chegando
        for n, code in enumerate(["NR-24H", "NR-2D", "NR-3D"]):
            self._contato(c, code, dt.date(2026, 9, 25) + dt.timedelta(days=n))
        self.assertEqual(next(i for i in self._fila(c) if i.code == "cadencia").template, "NR-5D")
        # depois do +5 dias sem resposta: acionar quem recrutou (tarefa, não mensagem ao criador)
        with system_context():
            Contact.objects.create(creator=c, user=self.g, template_code="NR-5D", body="x", sent_at=timezone.now() - dt.timedelta(hours=30))
        recrutou = next(i for i in self._fila(c) if i.code == "cadencia_recrutou")
        self.assertFalse(recrutou.is_message)
        self.assertIn("quem recrutou: Adrielly", recrutou.detail)
        # "Respondeu" encerra tudo
        self.client.force_login(self.g)
        self.client.post(reverse("g_creator_action", args=[c.pk]), {"a": "responded"})
        self.assertEqual([i for i in self._fila(c) if i.code.startswith("cadencia")], [])

    def test_mensagem_de_rodizio_sem_resposta_nao_puxa_cadencia(self):
        c = self._criador()
        self._contato(c, "ROD-PERG", dt.date(2026, 9, 26))
        self.assertEqual([i for i in self._fila(c) if i.code.startswith("cadencia")], [])

    def test_painel_e_ficha_mostram_estado_segmento_e_prioridade(self):
        c = self._criador()
        with system_context():
            SupportTicket.objects.create(creator=c, question="Como saco?")
        self.client.force_login(self.g)
        painel = self.client.get("/gestao/")
        self.assertContains(painel, "Fila do dia")
        self.assertContains(painel, "Adiar com motivo")
        ficha = self.client.get(reverse("g_creator", args=[c.pk]))
        self.assertContains(ficha, "Semana:")
        self.assertContains(ficha, "Segmento:")
        self.assertContains(ficha, "Prioridade")
