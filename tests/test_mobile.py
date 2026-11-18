"""Tela do streamer testada a 375 px de largura (sem rolagem horizontal)."""
import datetime as dt
import os
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from core.access import assign_manager
from core.rls import set_context
from data.engine import recalculate

from . import factories as F

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@unittest.skipIf(sync_playwright is None, "Playwright não instalado")
class MobileLayoutTests(StaticLiveServerTestCase):
    def setUp(self):
        set_context(system=True)
        ag = F.agency()
        self.u = F.user(email="mobile@teste.local")
        self.u.set_password("senha-teste-123")
        self.u.save()
        c = F.creator(ag, username="um.nome.de.usuario.bem.comprido.demo", streamer_user=self.u)
        assign_manager(c, F.user(role="gestora", ag=ag))
        today = dt.date.today()
        F.snapshot(c, today.replace(day=1), today, diamonds=1_234_567, hours=88.5, valid_days=20, streams=30, pct_diamonds=0.4)
        recalculate(ag)
        set_context()

    def test_streamer_pages_fit_375px(self):
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True).new_page()
            page.goto(self.live_server_url + "/accounts/login/")
            page.fill("#id_login", "mobile@teste.local")
            page.fill("#id_password", "senha-teste-123")
            page.click("form[action='/accounts/login/'] button")
            page.wait_for_url(self.live_server_url + "/")
            for path in ["/", "/desempenho/", "/campanhas/", "/academy/", "/perfil/", "/duvidas/", "/beneficios/", "/batalhas/nova/"]:
                page.goto(self.live_server_url + path)
                width = page.evaluate("document.documentElement.scrollWidth")
                self.assertLessEqual(width, 375, f"rolagem horizontal em {path}: {width}px")
                self.assertTrue(page.locator("nav.nav-bottom").is_visible(), path)
            browser.close()
