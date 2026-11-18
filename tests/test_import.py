"""Importação: conversões, upsert, reimportação sem duplicar, desfazer, saída, fuso."""
import datetime as dt
import io
from decimal import Decimal

import openpyxl
from django.test import TestCase

from core.bootstrap import BACKSTAGE_PT_MAP, TASK_EN_MAP
from core.rls import set_context
from crm.models import Creator, CreatorStatus, CreatorUsername, ExitRecord
from data import importer
from data import parsing as P
from data.models import CreatorSnapshot, ImportBatch, MonthlyResult, TaskResult

from . import factories as F

HEAD = [h for h in BACKSTAGE_PT_MAP if h not in ("Novos fãs", "Total de Diamantes do Fã-clube", "% de contribuição de fãs", "Total de fãs", "Fãs ativos do Fã-clube")]


def row(**kw):
    base = {h: "-" for h in HEAD}
    base.update({
        "Período dos dados": "2026-05-01 ~ 2026-05-19", "ID do criador": "7300000000000000001", "Nome do criador": "luna.demo",
        "Grupo": "Não está em um grupo", "Agente": "gestora1@hera.demo", "Horário de ingresso": "2026-05-02 02:07:59 (UTC+0)",
        "Dias desde que entrou para a rede": "17", "Diamantes": "406739", "Duração da LIVE": "90h 2m 52s",
        "Dias válidos de início de LIVE": "12", "Novos seguidores": "80", "Transmissões de LIVE": "91",
        "Diamantes do mês passado": "833244", "Diamantes - Porcentagem alcançada": "48.81%",
        "Duração da LIVE - Porcentagem alcançada": "49.51%", "Batalhas": "800", "Status": "",
    })
    base.update(kw)
    return base


def xlsx(rows, headers=HEAD):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h) for h in headers])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class ParsingTests(TestCase):
    def test_duration_text(self):
        self.assertEqual(P.duration_to_seconds("90h 2m 52s"), 324172)
        self.assertEqual(P.duration_to_seconds("59m 31s"), 3571)
        self.assertEqual(P.duration_to_seconds("0s"), 0)
        self.assertEqual(P.duration_to_seconds("-"), 0)
        self.assertEqual(P.duration_to_seconds(33.645), 121122)  # Task: horas decimais
        with self.assertRaises(P.ParseError):
            P.duration_to_seconds("noventa horas")

    def test_percent_text(self):
        self.assertEqual(P.pct_to_fraction("48.81%"), Decimal("0.4881"))
        self.assertEqual(P.pct_to_fraction("-100.00%"), Decimal("-1"))
        self.assertIsNone(P.pct_to_fraction("-"))
        with self.assertRaises(P.ParseError):
            P.pct_to_fraction("48,81")

    def test_timezone_utc_to_sao_paulo(self):
        d = P.utc_timestamp("2026-05-02 02:07:59 (UTC+0)")
        self.assertEqual(d.tzinfo, dt.timezone.utc)
        sp = P.to_sao_paulo(d)
        self.assertEqual((sp.date(), sp.hour), (dt.date(2026, 5, 1), 23))  # 02h UTC = 23h do dia anterior em Brasília

    def test_period_and_filename(self):
        self.assertEqual(P.parse_period("2026-05-01 ~ 2026-05-19"), (dt.date(2026, 5, 1), dt.date(2026, 5, 19)))
        t = P.export_time_from_filename("Dados do criador 2026_05_20 10_05 UTC+0.xlsx")
        self.assertEqual(t, dt.datetime(2026, 5, 20, 10, 5, tzinfo=dt.timezone.utc))
        self.assertEqual(P.parse_task_month("202606"), dt.date(2026, 6, 1))


class ImportFlowTests(TestCase):
    def setUp(self):
        set_context(system=True)
        self.ag = F.agency()

    def tearDown(self):
        set_context()

    def _import(self, data, name="Dados do criador 2026_05_20 10_05 UTC+0.xlsx"):
        b = importer.create_preview(self.ag, data, name)
        importer.commit(b)
        return b

    def test_new_creator_becomes_pending_with_snapshot(self):
        b = self._import(xlsx([row()]))
        self.assertEqual(b.counts["new"], 1)
        self.assertEqual((b.period_start, b.period_end), (dt.date(2026, 5, 1), dt.date(2026, 5, 19)))  # período vale também para creator novo
        c = Creator.objects.get()
        self.assertEqual(c.status, CreatorStatus.PENDENTE)
        self.assertEqual(c.tiktok_id, "7300000000000000001")  # 19 dígitos preservados como texto
        self.assertEqual(c.suggested_agent_email, "gestora1@hera.demo")
        self.assertEqual(c.joined_at, dt.datetime(2026, 5, 2, 2, 7, 59, tzinfo=dt.timezone.utc))
        s = CreatorSnapshot.objects.get()
        self.assertEqual((s.diamonds, s.live_seconds, s.valid_days, s.streams), (406739, 324172, 12, 91))
        self.assertEqual(s.pct_diamonds, Decimal("0.4881"))
        self.assertEqual(s.period_start, dt.date(2026, 5, 1))
        self.assertIsNone(s.pct_valid_days)  # "-" vira vazio

    def test_reimport_same_file_does_not_duplicate(self):
        data = xlsx([row()])
        self._import(data)
        b2 = importer.create_preview(self.ag, data, "Dados do criador 2026_05_20 10_05 UTC+0.xlsx")
        self.assertEqual(b2.counts["unchanged"], 1)
        self.assertIsNotNone(b2.counts["duplicate_of"])
        importer.commit(b2)
        self.assertEqual(Creator.objects.count(), 1)
        self.assertEqual(CreatorSnapshot.objects.count(), 1)

    def test_upsert_same_period_updates_new_period_adds(self):
        self._import(xlsx([row()]))
        self._import(xlsx([row(**{"Diamantes": "500000"})]), "Dados do criador 2026_05_20 18_00 UTC+0.xlsx")
        self.assertEqual(CreatorSnapshot.objects.get().diamonds, 500000)
        self._import(xlsx([row(**{"Período dos dados": "2026-05-01 ~ 2026-05-26", "Diamantes": "600000"})]), "Dados do criador 2026_05_27 10_00 UTC+0.xlsx")
        self.assertEqual(CreatorSnapshot.objects.count(), 2)

    def test_username_change_keeps_history(self):
        self._import(xlsx([row()]))
        self._import(xlsx([row(**{"Nome do criador": "luna.nova.demo", "Período dos dados": "2026-05-01 ~ 2026-05-26"})]), "Dados do criador 2026_05_27 10_00 UTC+0.xlsx")
        c = Creator.objects.get()
        self.assertEqual(c.username, "luna.nova.demo")
        self.assertEqual(set(CreatorUsername.objects.values_list("username", flat=True)), {"luna.demo", "luna.nova.demo"})

    def test_revert_restores_previous_state(self):
        self._import(xlsx([row()]))
        b2 = self._import(xlsx([row(**{"Diamantes": "999999"}), row(**{"ID do criador": "7300000000000000002", "Nome do criador": "sol.demo"})]),
                          "Dados do criador 2026_05_20 20_00 UTC+0.xlsx")
        self.assertEqual(Creator.objects.count(), 2)
        importer.revert(b2)
        self.assertEqual(Creator.objects.count(), 1)  # o creator criado pelo lote some
        self.assertEqual(CreatorSnapshot.objects.get().diamonds, 406739)  # valor anterior volta
        self.assertEqual(ImportBatch.objects.get(pk=b2.pk).status, "reverted")

    def test_left_creator_detected_by_username(self):
        self._import(xlsx([row()]))
        left = row(**{"ID do criador": importer.LEFT_MARKER, "Agente": "", "Horário de ingresso": "-", "Status": "Saiu",
                      "Período dos dados": "2026-06-01 ~ 2026-06-10"})
        b = self._import(xlsx([left]), "Dados do criador 2026_06_11 10_00 UTC+0.xlsx")
        self.assertEqual(b.counts["exit"], 1)
        c = Creator.objects.get()
        self.assertEqual(c.status, CreatorStatus.SAIU)
        ex = ExitRecord.objects.get()
        self.assertFalse(ex.within_free_period)
        self.assertEqual(ex.return_eligible_at, dt.date(2026, 6, 10) + dt.timedelta(days=90))
        importer.revert(b)
        self.assertEqual(Creator.objects.get().status, CreatorStatus.PENDENTE)
        self.assertEqual(ExitRecord.objects.count(), 0)

    def test_errors_are_reported_not_imported(self):
        b = importer.create_preview(self.ag, xlsx([row(**{"Duração da LIVE": "muito"}), row(**{"ID do criador": "abc"})]), "x.xlsx")
        self.assertEqual(b.counts["error"], 2)
        self.assertIn("duração ilegível", b.rows.first().errors)

    def test_extra_fan_columns_version_accepted(self):
        headers = HEAD[:-1] + ["Novos fãs", "Total de fãs", "Status"]
        b = self._import(xlsx([row(**{"Novos fãs": "12", "Total de fãs": "300"})], headers))
        self.assertEqual(b.counts["new"], 1)
        self.assertEqual(CreatorSnapshot.objects.get().new_fans, 12)

    def test_unknown_format_rejected(self):
        with self.assertRaises(importer.ImportError_):
            importer.create_preview(self.ag, xlsx([{"A": 1}], ["A", "B"]), "x.xlsx")

    def test_task_import_ignores_bonus_and_closes_month(self):
        self._import(xlsx([row()]))
        headers = list(TASK_EN_MAP)
        t = {h: 0 for h in headers}
        t.update({"Data Month": "202605", "Creator ID": "7300000000000000001", "Handle": "luna.demo", "Diamonds": 810000,
                  "Valid days(d)": 25, "LIVE duration(h)": 120.5, "Is violative creators": False, "Estimated bonus": 123.45})
        b = self._import(xlsx([t], headers), "_Task_202605_UTC+0_2026_06_10_09_49_20.xlsx")
        self.assertEqual(b.kind, "task")
        tr = TaskResult.objects.get()
        self.assertEqual((tr.diamonds, tr.valid_days), (810000, 25))
        self.assertFalse(hasattr(tr, "estimated_bonus"))
        mr = MonthlyResult.objects.get(month=dt.date(2026, 5, 1))
        self.assertEqual((mr.source, mr.tier), ("task", 8))
