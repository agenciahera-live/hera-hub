"""Popula o app com dados FICTÍCIOS para demonstração e testes manuais.

    python manage.py seed_demo

Gera as exportações no formato real (pasta seeds/), importa tudo pelo importador de verdade
e cria usuários de demonstração (senha: hera-demo-2026).
"""
import datetime as dt
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from allauth.account.models import EmailAddress

from core.access import assign_manager
from core.bootstrap import setup_agency
from core.models import Consent, Membership
from core.rls import system_context
from crm.models import ActionItem, Creator, CreatorPrivate, CreatorStatus, Note, OneOnOne, CreatorTag
from data import importer
from data.engine import recalculate
from data.seedgen import generate
from engage import models as E
from engage.services import publish_announcement

PASSWORD = "hera-demo-2026"
STAFF = [
    ("admin@hera.demo", "Admin", "admin"),
    ("gestora1@hera.demo", "Ana Gestora", "gestora"),
    ("gestora2@hera.demo", "Bruna Gestora", "gestora"),
    ("gestora3@hera.demo", "Carla Gestora", "gestora"),
    ("recrutadora@hera.demo", "Rita Recrutadora", "recrutadora"),
    ("conteudo@hera.demo", "Cris Conteúdo", "conteudo"),
    ("financeiro@hera.demo", "Fabio Financeiro", "financeiro"),
    ("analista@hera.demo", "Alex Analista", "analista"),
]

DEMO_VIDEO = "https://example.com/trocar-pelo-link-real"
# Os 7 módulos da Hera Academy (visão, "Página educacional") e um curso extra, com aulas de exemplo.
# (título, descrição, quando abre, nível, [(aula, minutos, ponto que ajuda, explica a batalha oficial)])
DEMO_MODULES = [
    ("1. Começar", "Como abrir uma LIVE, luz e enquadramento, o que pode e o que não pode.", "acesso", None,
     [("Xô Restrições e Banimentos", 12, "", False), ("O básico para começar bem", 6, "", False), ("Luz e enquadramento", 5, "", False)]),
    ("2. Primeiros 14 dias", "O que é dia válido, a regra do TikTok e o Desafio dos 5 dias.", "acesso", None,
     [("O que é dia válido", 4, "rotina", False), ("Desafio dos 5 dias", 5, "rotina", False)]),
    ("3. Interação", "Ganchos de conversa, chamar pelo nome, Heart Me e fã-clube.", "acesso", None,
     [("Interação que prende a audiência", 7, "interacao", False), ("Heart Me e fã-clube", 6, "fa_clube", False)]),
    ("4. Batalhas", "Primeira batalha, co-host e convidados, batalha oficial.", "primeira_live", None,
     [("Sua primeira batalha em 8 minutos", 8, "batalhas", True), ("Co-host e convidados", 6, "batalhas", False)]),
    ("5. Rotina e crescimento", "Dias de LIVE, vídeos e cortes, comunidade.", "dia15", None,
     [("Rotina fixa: como escolher seus dias de LIVE", 6, "rotina", False), ("Vídeos e cortes das suas LIVEs", 7, "", False)]),
    ("6. Nível e monetização", "Presentes, campanhas, graduação e próximos níveis.", "dia15", None,
     [("Presentes e campanhas", 6, "", False), ("Graduação e próximos níveis", 5, "", False)]),
    ("7. Estratégia avançada", "Campanhas da plataforma, networking, planejamento de LIVE e batalha oficial de alto nível.", "nivel", 3,
     [("Planejamento de LIVE", 8, "rotina", False), ("Batalha oficial de alto nível", 9, "batalhas", False)]),
    ("Curso extra: organização financeira", "Como organizar o que você ganha com as LIVEs.", "gestao", None,
     [("Organização financeira para criadores", 10, "", False)]),
]


def demo_academy(agency):
    """Cria (ou arruma) os módulos de exemplo. Aulas que já existem com o mesmo título mudam de módulo, sem perder
    o que o criador já assistiu. Os módulos antigos de demonstração somem quando ficam vazios."""
    for order, (title, desc, opens_on, level, lessons) in enumerate(DEMO_MODULES):
        co, _ = E.Course.objects.update_or_create(agency=agency, title=title, defaults={
            "description": desc, "order": order, "opens_on": opens_on, "opens_level": level, "published": True})
        for i, (lt, mins, topic, battle) in enumerate(lessons):
            ls = E.Lesson.objects.filter(course__agency=agency, title=lt).first()
            data = {"course": co, "minutes": mins, "topic": topic, "about_battles": battle, "order": i}
            if ls:
                for k, v in data.items():
                    setattr(ls, k, v)
                ls.save()
            else:
                E.Lesson.objects.create(title=lt, video_url=DEMO_VIDEO, **data)
    for old in ("Comece por aqui", "Crescer com constância"):
        E.Course.objects.filter(agency=agency, title=old, lessons__isnull=True).delete()


class Command(BaseCommand):
    help = "Cria dados fictícios de demonstração."

    def add_arguments(self, parser):
        parser.add_argument("--out", default=str(Path(settings.BASE_DIR) / "seeds"))

    def handle(self, *args, **opts):
        from django.core.management.base import CommandError

        if settings.IS_PRODUCTION:
            raise CommandError("Este comando cria logins de demonstração com senha conhecida (@hera.demo) e não roda em produção.")
        User = get_user_model()
        with system_context():
            agency = setup_agency()
            files, _ = generate(opts["out"])
            self.stdout.write(f"{len(files)} arquivos fictícios gerados em {opts['out']}")
            admin = None
            users = {}
            for email, name, role in STAFF:
                first, *last = name.split(" ")
                u, _ = User.objects.get_or_create(username=email, defaults={"email": email, "first_name": first, "last_name": " ".join(last)})
                u.set_password(PASSWORD)
                u.is_staff = role in ("admin", "conteudo")
                u.is_superuser = role == "admin"
                u.save()
                EmailAddress.objects.get_or_create(user=u, email=email, defaults={"verified": True, "primary": True})
                Membership.objects.get_or_create(user=u, agency=agency, role=role, defaults={"phone": "+55 11 90000-0000"})
                users[email] = u
                if role == "admin":
                    admin = u
            # importa na ordem cronológica, pelo importador real
            for f in files:
                b = importer.create_preview(agency, f.read_bytes(), f.name, user=admin)
                importer.commit(b, recalc=False)
                self.stdout.write(f"  importado {f.name}: {b.counts['new']} novos, {b.counts['updated']} atualizados, {b.counts['exit']} saídas")

            # carteira: atribuição manual (aqui usando a sugestão da coluna Agente)
            for c in Creator.objects.filter(agency=agency):
                mgr = users.get(c.suggested_agent_email)
                if mgr:
                    assign_manager(c, mgr)
                if c.status == CreatorStatus.PENDENTE:
                    c.status = CreatorStatus.ATIVO
                    c.save(update_fields=["status"])
                CreatorPrivate.objects.get_or_create(creator=c, defaults={"whatsapp": f"+55 11 9{c.pk:04d}-{c.pk:04d}"})

            # 12 streamers com acesso ao app (diretos da Hera), vários Tiers
            direct = list(Creator.objects.filter(agency=agency, partner_group__is_direct=True, status=CreatorStatus.ATIVO,
                                                 joined_at__lt=dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc)).order_by("id"))
            picks = direct[:10] + list(Creator.objects.filter(agency=agency, status=CreatorStatus.ATIVO, joined_at__gte=dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc))[:2])
            for i, c in enumerate(picks, start=1):
                email = f"streamer{i:02d}@hera.demo"
                u, _ = User.objects.get_or_create(username=email, defaults={"email": email, "first_name": c.first_name.split(".")[0].title()})
                u.set_password(PASSWORD)
                u.save()
                EmailAddress.objects.get_or_create(user=u, email=email, defaults={"verified": True, "primary": True})
                c.user = u
                c.display_name = u.first_name + f" Demo {i:02d}"
                c.save(update_fields=["user", "display_name"])
                Membership.objects.get_or_create(user=u, agency=agency, role="streamer")
                Consent.objects.get_or_create(user=u, version=settings.CONSENT_VERSION)
            # recrutadora "recrutou" alguns
            for c in Creator.objects.filter(agency=agency).order_by("id")[:8]:
                c.recruited_by = users["recrutadora@hera.demo"]
                c.save(update_fields=["recruited_by"])

            self._content(agency, users)
            recalculate(agency)
            self._crm(agency, users)
        self.stdout.write(self.style.SUCCESS(
            "Pronto. Entre com admin@hera.demo, gestora1@hera.demo ou streamer01@hera.demo (senha: %s)" % PASSWORD))

    def _content(self, agency, users):
        today = timezone.localdate()
        m0 = today.replace(day=1)
        m_end = (m0 + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
        camps = [
            ("Primeira Conquista", "interna", "valid_days", 5, [], [], True, "Complete 5 dias válidos e 15h nos seus primeiros 14 dias.", "Reconhecimento no grupo + entrada na Ativação"),
            ("Desafio da Consistência", "backstage", "valid_days", 15, [1], [], False, "Faixas: Bronze 7 dias válidos + 15h · Prata 15 dias + 40h · Ouro 40 mil diamantes no mês.", "Promoção de LIVE, tripé ou luz, R$ 50 ou Galáxia"),
            ("Em Ascensão", "backstage", "diamonds", 80000, [2], [], False, "Estágio 1: 20 dias válidos, 60h, 250 batalhas. Estágio 2: bônus por diamantes, definido no TikTok.", "Microfone lapela; bônus para quem graduar"),
            ("Rumo à Elite", "backstage", "diamonds", None, [3, 4, 5, 6, 7], [], False, "Estágio 1: 10 dias válidos, 30h, 200 batalhas. Estágio 2: bônus por novos fãs e diamantes de convidados.", "Presente em LIVE ou valor em dinheiro"),
        ]
        for name, src, metric, goal, tiers, groups, first, rules, prizes in camps:
            E.Campaign.objects.get_or_create(agency=agency, name=name, defaults=dict(
                source=src, metric=metric, goal=goal, audience_tiers=tiers, audience_groups=groups, only_first_month=first,
                rules=rules, prizes=prizes, start=m0, end=m_end,
                tiktok_url="https://example.com/trocar-pelo-link-da-campanha-no-tiktok",
                featured=src == "backstage" and name != "Rumo à Elite",
                what_to_do={"Primeira Conquista": "Complete 5 dias válidos (1h por dia) e 15h de LIVE nos seus primeiros 14 dias.",
                            "Desafio da Consistência": "Faça LIVE de pelo menos 1h em 15 dias do mês e some 40h. Quem chegar a 40 mil diamantes gradua para o Tier 2.",
                            "Em Ascensão": "20 dias válidos, 60h e 250 batalhas no mês. Depois, os diamantes decidem o bônus."}.get(name, "")))
        E.Campaign.objects.get_or_create(agency=agency, name="Maratona de Fim de Semana", defaults=dict(
            source="relampago", metric="hours", goal=4, rules="Some 4 horas de LIVE entre sexta e domingo. Sorteio entre quem somar as 4 horas.",
            prizes="Sorteio de uma Galáxia em LIVE", tiktok_url="https://example.com/trocar-pelo-link-da-campanha-no-tiktok",
            what_to_do="Some 4 horas de LIVE entre sexta e domingo. Quem somar as 4 horas entra no sorteio.", start=today - dt.timedelta(days=3), end=today + dt.timedelta(days=2)))

        demo_academy(agency)

        ann, created = E.Announcement.objects.get_or_create(agency=agency, title="Treino ao vivo de batalhas nesta quinta, 20h", defaults={
            "body": "Aula aberta com dicas de PK e dos momentos de pico. O link sai no Grupo de Avisos.", "pinned": True, "created_by": users["conteudo@hera.demo"]})
        if created:
            publish_announcement(ann)
        E.Announcement.objects.get_or_create(agency=agency, title="Prata: encontro mensal", defaults={
            "body": "Encontro só para o grupo Prata na próxima semana.", "audience_groups": ["Prata"], "created_by": users["conteudo@hera.demo"]})

        offers = [
            ("LuzMax Demo", "Ring light 26 cm com 15% off", "iluminacao", "HERA15", True, "Tier 1–2"),
            ("SomBom Demo", "Microfone de lapela sem fio", "som", "HERALIVE", False, "Tier 3–4"),
            ("Cadeirinha Demo", "Cadeira gamer com frete grátis", "cadeira", "", True, ""),
        ]
        for brand, title, cat, cup, aff, rec in offers:
            E.PartnerOffer.objects.get_or_create(agency=agency, brand=brand, title=title, defaults={
                "category": cat, "coupon": cup, "url": "https://example.com/oferta-demo", "affiliate": aff, "recommended_for": rec})

        sv, created = E.Survey.objects.get_or_create(agency=agency, title="Como está o app para você?", defaults={"intro": "3 perguntas · 1 minuto", "anonymous": True})
        if created:
            E.SurveyQuestion.objects.create(survey=sv, text="De 0 a 10, quanto você recomendaria a Hera para uma amiga streamer?", kind="nps", order=0)
            E.SurveyQuestion.objects.create(survey=sv, text="O que você mais usa no app?", kind="single", options=["Meu mês", "Campanhas", "Academy", "Dúvidas"], order=1)
            E.SurveyQuestion.objects.create(survey=sv, text="O que podemos melhorar?", kind="text", order=2)

    def _crm(self, agency, users):
        g1 = users["gestora1@hera.demo"]
        for c in Creator.objects.filter(agency=agency, assignments__manager=g1, assignments__valid_to__isnull=True)[:3]:
            Note.objects.get_or_create(creator=c, body="Prefere LIVE à noite; combinar batalha no fim de semana.", defaults={"author": g1})
            CreatorTag.objects.get_or_create(creator=c, tag="potencial", defaults={"set_by": g1})
            o, created = OneOnOne.objects.get_or_create(creator=c, manager=g1, date=timezone.localdate() - dt.timedelta(days=10), defaults={
                "b1_performance": "Subiu 12% em diamantes vs. mês passado.", "b2_constancia": "4 dias por semana, sem atrasos.",
                "b3_qualidade": "Luz boa; melhorar interação no início.", "b4_monetizacao": "Aproveitar campanha do mês.",
                "b5_dificuldades": "Agenda apertada na quarta.", "b7_next_date": timezone.localdate() - dt.timedelta(days=2)})
            if created:
                ActionItem.objects.create(one_on_one=o, creator=c, action="Testar 2 batalhas no sábado", owner="streamer", due_date=timezone.localdate() - dt.timedelta(days=1))
        streamer = Creator.objects.filter(agency=agency, user__username="streamer01@hera.demo").first()
        if streamer:
            prof = E.CommunityProfile.objects.exclude(creator=streamer).first()
            E.BattleRequest.objects.get_or_create(creator=streamer, date=timezone.localdate() + dt.timedelta(days=4), time=dt.time(20, 0), defaults={
                "kind": "especial", "goal_diamonds": 20000, "opponent": prof, "promote": True, "notes": "Quero fazer uma batalha temática de aniversário."})
