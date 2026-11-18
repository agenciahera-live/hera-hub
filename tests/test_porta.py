"""Porta de importação (passo 2.1): o Claude envia o arquivo da leitura diária com a chave da agência."""
import datetime as dt

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.bootstrap import TASK_EN_MAP
from core.models import AgencySettings, AuditLog
from core.rls import set_context, system_context
from crm.models import Creator
from data import importer, port
from data.models import CreatorSnapshot, ImportBatch, ImportKey
from engage.models import Notification
from web import services as S

from . import factories as F
from .test_import import row, xlsx

URL = "/api/importacao/backstage/"
NOME = "Dados do criador 2026_05_20 10_05 UTC+0.xlsx"


class PortaDeImportacaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        set_context(system=True)
        cls.ag = F.agency()
        cls.admin = F.user(role="admin", ag=cls.ag)
        cls.gestora = F.user(role="gestora", ag=cls.ag)
        cls.analista = F.user(role="analista", ag=cls.ag)
        cls.chave = port.new_key(cls.ag, by=cls.admin)
        set_context()

    def setUp(self):
        self.api = Client(enforce_csrf_checks=True)  # a porta não usa cookie nem token de formulário

    def tearDown(self):
        set_context()

    def _enviar(self, linhas=None, nome=NOME, chave=None, dados=None, headers=None):
        dados = dados if dados is not None else xlsx(linhas if linhas is not None else [row()], *([headers] if headers else []))
        extra = {} if chave is False else {"HTTP_AUTHORIZATION": f"Bearer {chave or self.chave}"}
        return self.api.post(URL, {"file": SimpleUploadedFile(nome, dados)}, **extra)

    # ------------------------------------------------------------ chave
    def test_sem_chave_ou_com_chave_errada_nao_entra(self):
        self.assertEqual(self._enviar(chave=False).status_code, 401)
        self.assertEqual(self._enviar(chave="hera_chave-inventada").status_code, 401)
        self.assertEqual(self.api.post(URL, {"file": SimpleUploadedFile(NOME, xlsx([row()]))}, HTTP_AUTHORIZATION=self.chave).status_code, 401)
        self.assertEqual(self.api.get(URL, HTTP_AUTHORIZATION=f"Bearer {self.chave}").status_code, 405)
        with system_context():
            self.assertEqual(ImportBatch.objects.count(), 0)
            self.assertEqual(Creator.objects.count(), 0)

    def test_banco_guarda_so_o_resumo_da_chave(self):
        k = ImportKey.objects.get()
        self.assertNotIn(self.chave, (k.key_hash, k.hint))
        self.assertEqual(len(k.key_hash), 64)
        self.assertTrue(self.chave.startswith(k.hint))

    def test_chave_nova_cancela_a_anterior_e_so_as_socias_geram(self):
        self.client.force_login(self.gestora)
        self.assertEqual(self.client.post(reverse("g_import_key"), {"a": "new"}).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(reverse("g_import_key"), {"a": "new"})
        tela = self.client.get("/gestao/importar/")
        nova = ImportKey.objects.get(revoked_at__isnull=True)
        self.assertContains(tela, "Copie agora")
        self.assertContains(tela, "Bearer hera_")
        self.assertContains(tela, "http://testserver/api/importacao/backstage/")
        self.assertNotContains(self.client.get("/gestao/importar/"), "Bearer hera_")  # a chave aparece uma vez só
        self.assertEqual(self._enviar().status_code, 401)  # a chave antiga parou de valer
        self.assertTrue(self.chave.startswith(ImportKey.objects.get(revoked_at__isnull=False).hint))
        self.assertNotEqual(nova.hint, "")
        # desligar
        self.client.post(reverse("g_import_key"), {"a": "revoke"})
        self.assertFalse(ImportKey.objects.filter(revoked_at__isnull=True).exists())
        self.assertContains(self.client.get("/gestao/importar/"), "Desligada")

    # ------------------------------------------------------------ leitura limpa
    def test_leitura_limpa_e_gravada_sozinha(self):
        r = self._enviar([row(), row(**{"ID do criador": "7300000000000000002", "Nome do criador": "sol.demo"})])
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertEqual((j["ok"], j["situacao"], j["novos"], j["erros"]), (True, "gravado", 2, 0))
        self.assertEqual((j["periodo_inicio"], j["periodo_fim"]), ("2026-05-01", "2026-05-19"))
        with system_context():
            b = ImportBatch.objects.get()
            self.assertEqual((b.status, b.via, b.uploaded_by), ("committed", "porta", None))
            self.assertEqual(CreatorSnapshot.objects.count(), 2)
            self.assertTrue(AuditLog.objects.filter(action="importacao_automatica", target=f"lote {b.pk}").exists())
            self.assertIsNotNone(ImportKey.objects.get().last_used_at)
        # o painel mostra que a importação de hoje veio pela leitura automática, e dá para desfazer pela tela
        self.client.force_login(self.gestora)
        painel = self.client.get("/gestao/")
        self.assertContains(painel, "pela leitura automática")
        self.assertNotContains(painel, "ainda não chegou")
        self.assertContains(self.client.get("/gestao/importar/"), "leitura automática")
        self.client.post(f"/gestao/importar/{b.pk}/", {"a": "revert"})
        with system_context():
            self.assertEqual(CreatorSnapshot.objects.count(), 0)

    def test_mesmo_arquivo_duas_vezes_nao_duplica(self):
        dados = xlsx([row()])
        self.assertEqual(self._enviar(dados=dados).json()["situacao"], "gravado")
        r = self._enviar(dados=dados)
        self.assertEqual((r.status_code, r.json()["ok"], r.json()["situacao"]), (200, True, "repetido"))
        self.assertNotIn("novos", r.json())  # sem a contagem do lote antigo
        self.assertIn("já tinha sido importado", r.content.decode("utf-8"))  # acentos legíveis, sem á
        with system_context():
            self.assertEqual(ImportBatch.objects.count(), 1)
            self.assertEqual(CreatorSnapshot.objects.count(), 1)

    def test_csv_tambem_e_aceito(self):
        from .test_import import HEAD

        linha = row()
        texto = ",".join(HEAD) + "\n" + ",".join(str(linha[h]) for h in HEAD) + "\n"
        r = self._enviar(dados=texto.encode("utf-8"), nome="Dados do criador 2026_05_20 10_05 UTC+0.csv")
        self.assertEqual((r.status_code, r.json()["situacao"]), (200, "gravado"))

    # ------------------------------------------------------------ leitura com problema
    def test_leitura_com_erro_fica_para_conferencia_e_avisa_a_gestao(self):
        r = self._enviar([row(), row(**{"ID do criador": "abc"})])
        self.assertEqual(r.status_code, 422)
        j = r.json()
        self.assertEqual((j["ok"], j["situacao"], j["erros"]), (False, "conferir", 1))
        self.assertIn("1 linha com erro", j["mensagem"])
        with system_context():
            b = ImportBatch.objects.get()
            self.assertEqual((b.status, b.via), ("preview", "porta"))
            self.assertEqual(CreatorSnapshot.objects.count(), 0)  # nada gravado
            avisados = set(Notification.objects.filter(kind="dados").values_list("user_id", flat=True))
        self.assertEqual(avisados, {self.admin.pk, self.gestora.pk})
        # reenvio do mesmo problema não repete o aviso enquanto ele não for lido
        self._enviar([row(), row(**{"ID do criador": "abcd"})])
        with system_context():
            self.assertEqual(Notification.objects.filter(kind="dados", user=self.gestora).count(), 1)
        # a gestora vê o motivo no painel, confere e grava pela tela
        self.client.force_login(self.gestora)
        painel = self.client.get("/gestao/")
        self.assertContains(painel, "chegou, mas não foi gravada")
        self.assertContains(painel, "Conferir e gravar")
        self.assertContains(self.client.get(f"/gestao/importar/{b.pk}/"), "não foi gravada sozinha")
        self.client.post(f"/gestao/importar/{b.pk}/", {"a": "commit"})
        with system_context():
            self.assertEqual(CreatorSnapshot.objects.count(), 1)  # a linha boa entra; a linha com erro fica de fora
        self.assertContains(self.client.get("/gestao/"), "pela leitura automática")

    def test_muitas_saidas_de_uma_vez_ficam_para_conferencia(self):
        with system_context():
            AgencySettings.objects.filter(agency=self.ag).update(auto_import_max_exits=1)
        nomes = ["um.demo", "dois.demo", "tres.demo"]
        self._enviar([row(**{"ID do criador": f"730000000000000000{i}", "Nome do criador": n}) for i, n in enumerate(nomes, 1)])
        saidas = [row(**{"ID do criador": importer.LEFT_MARKER, "Nome do criador": n, "Agente": "", "Horário de ingresso": "-", "Status": "Saiu",
                         "Período dos dados": "2026-06-01 ~ 2026-06-10"}) for n in nomes[:2]]
        fica = row(**{"ID do criador": "7300000000000000003", "Nome do criador": "tres.demo", "Período dos dados": "2026-06-01 ~ 2026-06-10"})
        r = self._enviar(saidas + [fica], nome="Dados do criador 2026_06_11 10_00 UTC+0.xlsx")
        self.assertEqual((r.status_code, r.json()["situacao"], r.json()["saidas"]), (422, "conferir", 2))
        with system_context():
            self.assertEqual(Creator.objects.filter(status="saiu").count(), 0)  # ninguém perdeu o acesso sem conferência

    def test_arquivo_que_nao_e_a_planilha_e_recusado(self):
        casos = [
            self._enviar(dados=b"isto nao e uma planilha", nome="qualquer.xlsx"),  # ilegível
            self._enviar([{"A": 1}], headers=["A", "B"]),  # formato desconhecido
            self._enviar([{h: 1 for h in TASK_EN_MAP}], headers=list(TASK_EN_MAP), nome="_Task_202605.xlsx"),  # Task não entra pela porta
        ]
        for r in casos:
            self.assertEqual((r.status_code, r.json()["ok"], r.json()["situacao"]), (422, False, "recusado"), r.json())
        self.assertEqual(self.api.post(URL, {"outro": "campo"}, HTTP_AUTHORIZATION=f"Bearer {self.chave}").status_code, 400)
        with system_context():
            self.assertEqual(ImportBatch.objects.count(), 0)
            self.assertTrue(Notification.objects.filter(kind="dados", user=self.admin, title__contains="recusada").exists())

    # ------------------------------------------------------------ aviso de que a leitura não chegou
    def test_painel_avisa_quando_a_leitura_do_dia_nao_chegou(self):
        sp = timezone.get_current_timezone()
        cedo = dt.datetime(2026, 11, 16, 8, 0, tzinfo=sp)
        tarde = dt.datetime(2026, 11, 16, 10, 0, tzinfo=sp)
        st = S.import_status(self.ag, now=cedo)
        self.assertEqual((st["auto_on"], st["auto_late"], st["auto_deadline"]), (True, False, 10))
        self.assertTrue(S.import_status(self.ag, now=tarde)["auto_late"])
        with system_context():
            AgencySettings.objects.filter(agency=self.ag).update(auto_import_deadline_hour=12)
        self.assertFalse(S.import_status(self.ag, now=tarde)["auto_late"])  # a hora-limite é configurável
        # sem chave (leitura automática desligada), o aviso é o de sempre
        port.revoke_key(self.ag)
        st = S.import_status(self.ag, now=tarde.replace(hour=15))
        self.assertEqual((st["auto_on"], st["auto_late"]), (False, False))

    def test_textos_do_painel_com_a_leitura_ligada(self):
        with system_context():
            AgencySettings.objects.filter(agency=self.ag).update(auto_import_deadline_hour=0)  # qualquer hora já passou do limite
        self.client.force_login(self.gestora)
        painel = self.client.get("/gestao/")
        self.assertContains(painel, "A leitura automática de hoje não chegou até as 0h")
        self.assertContains(painel, "Plano B")
        self.assertContains(painel, "Importar agora")
        self.client.force_login(self.analista)
        self.assertContains(self.client.get("/gestao/"), "Quem importa é a gestão ou as sócias")
        with system_context():
            AgencySettings.objects.filter(agency=self.ag).update(auto_import_deadline_hour=24)  # nunca passa do limite
        self.assertContains(self.client.get("/gestao/"), "ainda não chegou (esperada até as 24h)")
        # a tela de importação mostra a situação da leitura automática; a gestora não vê os botões da chave
        self.client.force_login(self.gestora)
        tela = self.client.get("/gestao/importar/")
        self.assertContains(tela, "Ligada")
        self.assertContains(tela, "são as sócias")
        self.assertNotContains(tela, "Gerar chave nova")
