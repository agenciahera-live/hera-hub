"""Carrega uma semana do Acompanhamento Semanal (formato de build_semana.py) em uma agência de demonstração SEPARADA.

    python manage.py demo_semana --arquivo "..\\exemplo-semana.json"

Para que serve: ver a fila do dia com a distribuição real da carteira (muitos sem LIVE, muitos na prioridade 3)
e conferir se o motor do app (data/states.py) chega ao mesmo estado, segmento e prioridade que o script.

Cuidados:
- o arquivo tem números reais com os @ trocados. Ele NÃO entra no repositório: fica fora da pasta hera-hub;
- nada é misturado com a agência principal: tudo vai para a agência "semana-demo", que o comando apaga e recria;
- os nomes das gestoras do arquivo viram "Gestora A", "Gestora B"... (logins gestora.a@semana.demo etc.);
- os logins @semana.demo têm senha conhecida e NÃO PODEM existir em produção: o comando se recusa a rodar lá.

Para os testes automáticos existe uma semana pequena e inventada, no mesmo formato: tests/fixtures/semana-sintetica.json.

O arquivo traz totais por semana; o app trabalha com fotos acumuladas do mês. O comando monta as fotos de outubro
e novembro que dão exatamente aqueles totais semanais.
"""
import datetime as dt
import json
from collections import Counter
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from allauth.account.models import EmailAddress
from core.access import assign_manager
from core.bootstrap import setup_agency
from core.models import Agency, Membership
from core.rls import system_context
from crm.models import Creator, CreatorStatus
from data import states
from data.engine import recalculate
from data.models import CreatorSnapshot, ImportBatch

PASSWORD = "hera-demo-2026"
SLUG = "semana-demo"
STATE_CODES = {"Inativo 30d+": "inativo", "Sem live": "sem_live", "Queda": "queda", "Subindo": "subindo", "Novo": "novo",
               "Horas sem retorno": "horas_sem_retorno", "Irregular": "irregular", "Estável": "estavel"}
SEGMENT_CODES = {"Top": "top", "Médio": "medio", "Desenvolvimento": "desenvolvimento", "Base": "base"}


def week_ranges(labels, year):
    """["05–11/10", ..., "26/10–01/11", "02–08/11"] → [(início, fim), ...]"""
    out = []
    for label in labels:
        a, b = label.replace("-", "–").split("–")
        d2, m2 = (int(x) for x in b.split("/"))
        d1, m1 = (int(x) for x in a.split("/")) if "/" in a else (int(a), m2)
        out.append((dt.date(year, m1, d1), dt.date(year, m2, d2)))
    return out


class Command(BaseCommand):
    help = "Carrega a semana de exemplo (números reais, nomes trocados) na agência de demonstração 'semana-demo'."

    def add_arguments(self, parser):
        parser.add_argument("--arquivo", required=True, help="Caminho do exemplo-semana.json (fora do repositório).")
        parser.add_argument("--ano", type=int, default=2026)

    def handle(self, *args, **o):
        from django.conf import settings

        if settings.IS_PRODUCTION:
            raise CommandError("Este comando cria logins de demonstração com senha conhecida (@semana.demo) e não roda em produção.")
        path = Path(o["arquivo"])
        if not path.exists():
            raise CommandError(f"Arquivo não encontrado: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        weeks = week_ranges(data["weeks"], o["ano"])
        sunday = weeks[4][1]
        monday = sunday + dt.timedelta(days=1)
        m1 = sunday.replace(day=1)  # mês corrente da leitura
        m0 = (m1 - dt.timedelta(days=1)).replace(day=1)  # mês anterior
        m0_end = m1 - dt.timedelta(days=1)
        User = get_user_model()
        with system_context():
            Agency.objects.filter(slug=SLUG).delete()
            User.objects.filter(email__endswith="@semana.demo").delete()
            ag = setup_agency(name="Semana real (demonstração)", slug=SLUG)
            batch = ImportBatch.objects.create(agency=ag, kind="backstage", filename=path.name, file_hash="demo-semana", status="committed",
                                               via="tela", committed_at=timezone.now(), period_start=m0, period_end=sunday,
                                               exported_at=timezone.make_aware(dt.datetime.combine(monday, dt.time(10, 0))))
            users = {}

            def user(email, name, role):
                u = User.objects.create_user(username=email, email=email, password=PASSWORD, first_name=name)
                EmailAddress.objects.create(user=u, email=email, verified=True, primary=True)
                Membership.objects.create(user=u, agency=ag, role=role)
                return u

            user("admin@semana.demo", "Admin", "admin")
            for i, name in enumerate(sorted({c["mgr"] for c in data["creators"]})):
                letter = chr(ord("a") + i)
                users[name] = user(f"gestora.{letter}@semana.demo", f"Gestora {letter.upper()}", "gestora")

            for n, c in enumerate(data["creators"], start=1):
                joined = dt.datetime.fromtimestamp(c["jt"], tz=dt.timezone.utc) if c.get("jt") else timezone.now() - dt.timedelta(days=c["dsj"])
                cr = Creator.objects.create(agency=ag, tiktok_id=str(7900000000000000000 + n), display_name=c["h"], username=c["h"],
                                            status=CreatorStatus.ATIVO, joined_at=joined)
                assign_manager(cr, users[c["mgr"]])
                self._snapshots(cr, c, batch, weeks, m0, m0_end, m1, sunday, monday)
            recalculate(ag)

            # conferência: o motor do app chega ao mesmo resultado que o script?
            diffs, got = [], Counter()
            for c in data["creators"]:
                cr = Creator.objects.get(agency=ag, username=c["h"])
                ws = states.week_state(cr, list(cr.snapshots.all()), monday)
                got[ws.label] += 1
                want = (STATE_CODES.get(c["st"]), SEGMENT_CODES.get(c["seg"]), c["pr"])
                if (ws.state, ws.segment, ws.priority) != want:
                    diffs.append(f"  @{c['h']}: script {c['st']}/{c['seg']}/P{c['pr']} · app {ws.label}/{ws.segment_label}/P{ws.priority}")
        self.diffs = diffs  # quem chama pelo código (testes) lê o resultado da conferência aqui
        self.stdout.write(f"{len(data['creators'])} criadores carregados na agência '{SLUG}'. Semana analisada: {weeks[4][0]:%d/%m} a {sunday:%d/%m}.")
        self.stdout.write("Estados pelo app: " + ", ".join(f"{k} {v}" for k, v in got.most_common()))
        if diffs:
            self.stdout.write(self.style.WARNING(f"{len(diffs)} criador(es) com estado, segmento ou prioridade diferente do script:"))
            self.stdout.write("\n".join(diffs))
        else:
            self.stdout.write(self.style.SUCCESS("Estado, segmento e prioridade iguais aos do script para todos os criadores."))
        self.stdout.write(self.style.SUCCESS(f"Entre com admin@semana.demo ou gestora.a@semana.demo (senha: {PASSWORD})."))

    def _snapshots(self, cr, c, batch, weeks, m0, m0_end, m1, sunday, monday):
        """Fotos acumuladas de outubro e novembro que reproduzem os totais semanais do arquivo."""
        wD, wH, wV = c["wD"], c["wH"], c["wV"]
        prev = c.get("sep") or [0, 0, 0, 0]  # mês anterior inteiro: diamantes, horas, dias válidos, batalhas
        # a semana 3 cruza a virada do mês: o que caiu no mês corrente é o acumulado do mês menos a semana 4
        spill = {"d": max(0, c["oD"] - wD[4]), "h": max(0.0, c["oH"] - wH[4]), "v": max(0, c["oV"] - wV[4])}
        spill = {"d": min(spill["d"], wD[3]), "h": min(spill["h"], wH[3]), "v": min(spill["v"], wV[3])}
        in_prev = [(wD[0], wH[0], wV[0]), (wD[1], wH[1], wV[1]), (wD[2], wH[2], wV[2]),
                   (wD[3] - spill["d"], wH[3] - spill["h"], wV[3] - spill["v"])]
        tot_d = max(prev[0], sum(x[0] for x in in_prev))
        tot_h = max(prev[1], sum(x[1] for x in in_prev))
        tot_v = max(prev[2], sum(x[2] for x in in_prev))
        acc = [tot_d - sum(x[0] for x in in_prev), tot_h - sum(x[1] for x in in_prev), tot_v - sum(x[2] for x in in_prev)]
        pk_week = c.get("pkW", 0)
        pk_prev = prev[3] if len(prev) > 3 else 0
        last_live = monday - dt.timedelta(days=c["since"]) if c.get("since", 999) < 900 else None
        points = []  # (início do mês, fim, diamantes, horas, dias, batalhas, fãs)
        if weeks[0][0] > m0:
            points.append((m0, weeks[0][0] - dt.timedelta(days=1), acc[0], acc[1], acc[2], 0, 1))
        ends = [weeks[0][1], weeks[1][1], weeks[2][1], m0_end]
        for i, end in enumerate(ends):
            acc = [acc[0] + in_prev[i][0], acc[1] + in_prev[i][1], acc[2] + in_prev[i][2]]
            pk = round(pk_prev * (acc[1] / tot_h)) if tot_h else 0
            points.append((m0, end, acc[0], acc[1], acc[2], pk, 1))
        if weeks[3][1] >= m1:  # dias da semana 3 que já são do mês corrente
            points.append((m1, weeks[3][1], spill["d"], spill["h"], spill["v"], max(0, c.get("oPK", 0) - pk_week), 0))
        points.append((m1, sunday, c["oD"], c["oH"], c["oV"], c.get("oPK", pk_week), c.get("nfc", 0)))
        # a última LIVE cai no dia certo: a semana em que ela aconteceu fecha nesse dia
        if last_live is not None:
            fixed = []
            for k, p in enumerate(points):
                before = points[k - 1] if k and points[k - 1][0] == p[0] else None
                start = before[1] + dt.timedelta(days=1) if before else p[0]
                grew = p[3] > (before[3] if before else 0)
                if grew and start <= last_live < p[1]:
                    fixed.append((p[0], last_live) + p[2:])
                fixed.append(p)
            points = fixed
        for start, end, d, h, v, pk, fans in points:
            CreatorSnapshot.objects.update_or_create(
                creator=cr, period_start=start, period_end=end,
                defaults=dict(batch=batch, agency=cr.agency, exported_at=batch.exported_at, username_at=cr.username,
                              diamonds=int(d), live_seconds=int(round(h * 3600)), valid_days=int(v), streams=int(v), battles=int(pk),
                              new_fans=int(fans), graduation_status="Não se graduou" if c.get("grad") == "N" else "Criador já existente",
                              level_status=c.get("lvl", "")))
