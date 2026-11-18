"""Cálculos: Tier, meta, ritmo, previsão, métricas derivadas de snapshots, grupo e onboarding."""
import datetime as dt
from decimal import Decimal

from django.test import TestCase

from core.rls import set_context
from data import engine as E
from data.models import MonthlyResult

from . import factories as F


class TierTests(TestCase):
    def setUp(self):
        set_context(system=True)
        self.rules = E.tier_rules(F.agency())

    def test_boundaries_are_inclusive_lower(self):
        cases = {0: 1, 39_999: 1, 40_000: 2, 79_999: 2, 80_000: 3, 149_999: 3, 150_000: 4, 249_999: 4, 250_000: 5,
                 349_999: 5, 350_000: 6, 499_999: 6, 500_000: 7, 799_999: 7, 800_000: 8, 1_199_999: 8, 1_200_000: 9,
                 1_599_999: 9, 1_600_000: 10, 9_000_000: 10}
        for d, t in cases.items():
            self.assertEqual(E.tier_for(d, self.rules), t, d)

    def test_rules_are_configurable(self):
        r = self.rules[1]
        r.min_diamonds = 50_000
        r.save()
        rules = E.tier_rules(r.agency)
        self.assertEqual(E.tier_for(45_000, rules), 1)
        self.assertEqual(E.tier_for(50_000, rules), 2)


class PaceTests(TestCase):
    def test_pace_forecast_and_status(self):
        # 12.400 de 40.000 com dados até 11/10 (11 dias de 31)
        p = E.compute_pace(12_400, 40_000, dt.date(2026, 10, 1), dt.date(2026, 10, 11))
        self.assertEqual((p.elapsed_days, p.remaining_days, p.month_days), (11, 20, 31))
        self.assertAlmostEqual(p.avg_per_day, 1127.27, places=2)
        self.assertAlmostEqual(p.needed_per_day, 1380.0, places=2)
        self.assertAlmostEqual(p.forecast, 12_400 + 1127.2727 * 20, places=1)
        self.assertFalse(p.on_track)
        self.assertAlmostEqual(p.pct, 0.31)
        self.assertEqual(p.missing, 27_600)

    def test_on_track_when_average_covers_need(self):
        p = E.compute_pace(20_000, 40_000, dt.date(2026, 9, 1), dt.date(2026, 9, 13))
        self.assertTrue(p.on_track)

    def test_goal_reached_and_last_day(self):
        p = E.compute_pace(45_000, 40_000, dt.date(2026, 9, 1), dt.date(2026, 9, 30))
        self.assertTrue(p.on_track)
        self.assertEqual(p.remaining_days, 0)
        self.assertEqual(p.forecast, 45_000)
        p2 = E.compute_pace(30_000, 40_000, dt.date(2026, 9, 1), dt.date(2026, 9, 30))
        self.assertFalse(p2.on_track)

    def test_tiktok_target_from_percent(self):
        self.assertAlmostEqual(E.tiktok_target(406_739, Decimal("0.4881")), 833_310.8, places=0)
        self.assertIsNone(E.tiktok_target(0, Decimal("0.5")))
        self.assertIsNone(E.tiktok_target(100, None))


class TargetTests(TestCase):
    def setUp(self):
        set_context(system=True)
        self.ag = F.agency()
        self.c = F.creator(self.ag)

    def test_reference_comes_from_tiktok_or_agency_default(self):
        """A gestão não define número para o criador: a referência é a do TikTok ou, sem ela, o padrão da agência."""
        s = F.snapshot(self.c, dt.date(2026, 9, 1), dt.date(2026, 9, 13), diamonds=10_000, hours=10, valid_days=4, pct_diamonds=Decimal("0.25"))
        t = E.targets_for(self.c, s)
        self.assertEqual(t["diamonds"], (40_000, "tiktok"))
        self.assertEqual(t["hours"], (15.0, "padrao"))
        self.assertEqual(t["valid_days"], (5.0, "padrao"))
        self.assertEqual({src for _valor, src in t.values()}, {"tiktok", "padrao"})


class SnapshotMetricsTests(TestCase):
    """Métricas diárias/semanais só existem como diferença entre snapshots."""

    def setUp(self):
        set_context(system=True)
        self.ag = F.agency()
        self.c = F.creator(self.ag)

    def test_daily_deltas_from_daily_imports(self):
        snaps = [
            F.snapshot(self.c, dt.date(2026, 9, 1), dt.date(2026, 9, 1), diamonds=1000, hours=2, valid_days=1, streams=1),
            F.snapshot(self.c, dt.date(2026, 9, 1), dt.date(2026, 9, 2), diamonds=1000, hours=2, valid_days=1, streams=1),
            F.snapshot(self.c, dt.date(2026, 9, 1), dt.date(2026, 9, 3), diamonds=4000, hours=3.5, valid_days=2, streams=2),
        ]
        ivs = E.intervals(snaps)
        self.assertEqual([(i.start.day, i.end.day, i.days) for i in ivs], [(1, 1, 1), (2, 2, 1), (3, 3, 1)])
        self.assertEqual([i.diamonds for i in ivs], [1000, 0, 3000])
        self.assertEqual([i.had_live for i in ivs], [True, False, True])
        self.assertAlmostEqual(ivs[2].hours, 1.5)
        self.assertEqual(E.days_without_live(snaps), 0)
        self.assertEqual(E.days_without_live(snaps[:2]), 1)

    def test_daily_imports_are_grouped_by_week(self):
        # setembro/2026 começa numa terça: 01–06 é a 1ª semana, 07–13 a 2ª
        acumulado = {1: 1000, 2: 1000, 3: 4000, 6: 5000, 7: 5000, 8: 9000, 13: 9500}
        snaps = [F.snapshot(self.c, dt.date(2026, 9, 1), dt.date(2026, 9, d), diamonds=v, hours=d, valid_days=1, streams=d)
                 for d, v in acumulado.items()]
        semanas = E.weekly_intervals(snaps)
        self.assertEqual([(w.start.day, w.end.day) for w in semanas], [(1, 6), (7, 13)])
        self.assertEqual([w.diamonds for w in semanas], [5000, 4500])
        self.assertEqual(sum(w.diamonds for w in semanas), 9500)
        # a semana não cruza a virada do mês
        snaps.append(F.snapshot(self.c, dt.date(2026, 10, 1), dt.date(2026, 10, 2), diamonds=700, hours=1, valid_days=1, streams=1))
        snaps.insert(0, F.snapshot(self.c, dt.date(2026, 9, 1), dt.date(2026, 9, 30), diamonds=12_000, hours=40, valid_days=9, streams=40))
        snaps.sort(key=lambda s: s.period_end)
        semanas = E.weekly_intervals(snaps)
        self.assertEqual([(w.start, w.end) for w in semanas][-2:], [
            (dt.date(2026, 9, 14), dt.date(2026, 9, 30)), (dt.date(2026, 10, 1), dt.date(2026, 10, 2))])

    def test_weekly_deltas_and_month_reset(self):
        snaps = [
            F.snapshot(self.c, dt.date(2026, 8, 1), dt.date(2026, 8, 31), diamonds=30_000, hours=40, valid_days=20, streams=25),
            F.snapshot(self.c, dt.date(2026, 9, 1), dt.date(2026, 9, 6), diamonds=5_000, hours=8, valid_days=4, streams=5),
            F.snapshot(self.c, dt.date(2026, 9, 1), dt.date(2026, 9, 13), diamonds=5_000, hours=8, valid_days=4, streams=5),
            F.snapshot(self.c, dt.date(2026, 9, 1), dt.date(2026, 9, 20), diamonds=5_000, hours=8, valid_days=4, streams=5),
        ]
        ivs = E.intervals(snaps)
        self.assertEqual([(i.start, i.end) for i in ivs][1:], [
            (dt.date(2026, 9, 1), dt.date(2026, 9, 6)), (dt.date(2026, 9, 7), dt.date(2026, 9, 13)), (dt.date(2026, 9, 14), dt.date(2026, 9, 20))])
        self.assertEqual(ivs[1].diamonds, 5_000)  # 1º snapshot do mês compara com zero
        self.assertEqual(E.days_without_live(snaps), 14)  # sem LIVE desde 06/09
        self.assertEqual(E.cumulative_until(snaps, dt.date(2026, 9, 13), "diamonds"), 35_000)
        self.assertEqual(E.cumulative_until(snaps, dt.date(2026, 8, 31), "valid_days"), 20)


class GroupAndOnboardingTests(TestCase):
    def setUp(self):
        set_context(system=True)
        self.ag = F.agency()

    def test_first_month_by_tenure_then_group_by_closed_month(self):
        novato = F.creator(self.ag, joined_days_ago=10)
        self.assertEqual(E.group_for(novato, today=dt.date(2026, 9, 28)), "Primeiro Mês")
        veterano = F.creator(self.ag, joined_days_ago=300)
        self.assertEqual(E.group_for(veterano, today=dt.date(2026, 9, 28)), "Primeiro Mês")  # sem mês fechado
        MonthlyResult.objects.create(creator=veterano, month=dt.date(2026, 8, 1), diamonds=90_000, source="task", tier=3)
        self.assertEqual(E.group_for(veterano, today=dt.date(2026, 9, 28)), "Prata")
        MonthlyResult.objects.create(creator=veterano, month=dt.date(2026, 9, 1), diamonds=900_000, source="backstage", tier=8)
        self.assertEqual(E.official_tier(veterano, today=dt.date(2026, 9, 28))[0], 3)  # mês corrente não vale (D5)
        # grupos da visão: Bronze T1, Prata T2–T3, Ouro T4, Diamante T5 ou mais
        from data.models import GroupRule

        grupos = list(GroupRule.objects.filter(agency=self.ag))
        self.assertEqual([E.group_for_tier(t, grupos) for t in (1, 2, 3, 4, 5, 8, 10)],
                         ["Bronze", "Prata", "Prata", "Ouro", "Diamante", "Diamante", "Diamante"])

    def test_onboarding_goal_met_and_at_risk(self):
        c = F.creator(self.ag, joined_days_ago=0)
        c.joined_at = dt.datetime(2026, 9, 1, 12, tzinfo=dt.timezone.utc)
        c.save()
        s1 = F.snapshot(c, dt.date(2026, 9, 1), dt.date(2026, 9, 10), hours=6, valid_days=2, streams=3)
        ob = E.onboarding_status(c, [s1])
        self.assertEqual((ob["day"], ob["valid_days"], ob["met"]), (10, 2, False))
        self.assertTrue(ob["at_risk"])  # Dia 10 sem a meta = risco
        s2 = F.snapshot(c, dt.date(2026, 9, 1), dt.date(2026, 9, 14), hours=16, valid_days=5, streams=6)
        ob = E.onboarding_status(c, [s1, s2])
        self.assertTrue(ob["met"])
