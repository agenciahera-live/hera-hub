from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import Agency, PartnerGroup
from crm.models import Creator

User = settings.AUTH_USER_MODEL


class AudienceMixin(models.Model):
    """Público por grupo de comunidade, Tier e parceira. Vazio = todos."""

    audience_groups = models.JSONField("grupos (vazio = todos)", default=list, blank=True)
    audience_tiers = models.JSONField("Tiers (vazio = todos)", default=list, blank=True)
    audience_partners = models.ManyToManyField(PartnerGroup, blank=True, related_name="+")
    only_first_month = models.BooleanField("só novatos (Primeiro Mês)", default=False)

    class Meta:
        abstract = True


class Campaign(AudienceMixin):
    SOURCES = [("backstage", "Oficial (Backstage)"), ("interna", "Interna"), ("relampago", "Relâmpago"), ("pontos", "Pontos (V2)")]
    METRICS = [
        ("diamonds", "Diamantes"),
        ("hours", "Horas de LIVE"),
        ("valid_days", "Dias válidos"),
        ("battles", "Batalhas"),
        ("new_followers", "Novos seguidores"),
    ]
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField("nome", max_length=120)
    source = models.CharField("origem", max_length=20, choices=SOURCES, default="backstage")
    banner = models.ImageField(upload_to="campanhas/", blank=True)
    featured = models.BooleanField("destaque do mês", default=False,
                                   help_text="Campanhas oficiais em destaque aparecem para o streamer. Não precisa cadastrar todas as do TikTok.")
    what_to_do = models.TextField("o que o streamer deve fazer (resumo)", blank=True,
                                  help_text="2 a 4 linhas simples. Ex.: faça 15 dias válidos e 40h até 30/09; batalhas contam em dobro no fim de semana.")
    tiktok_url = models.URLField("link da campanha no TikTok", blank=True,
                                 help_text="Copie o link da campanha no Backstage/TikTok. O card da campanha abre este link.")
    rules = models.TextField("regras")
    prizes = models.TextField("prêmios", blank=True)
    start = models.DateField("início")
    end = models.DateField("fim")
    metric = models.CharField("métrica acompanhada", max_length=20, choices=METRICS, default="diamonds")
    goal = models.DecimalField("alvo da campanha (opcional)", max_digits=12, decimal_places=2, null=True, blank=True)
    estimated_cost = models.DecimalField("custo estimado (R$)", max_digits=10, decimal_places=2, null=True, blank=True)
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start"]
        verbose_name = "campanha"

    def __str__(self):
        return self.name

    @property
    def tracked_in_app(self):
        """Campanhas do Backstage são acompanhadas no próprio TikTok (tempo real). O app só acompanha o progresso das internas."""
        return self.source != "backstage"

    def is_active(self, today=None):
        today = today or timezone.localdate()
        return self.published and self.start <= today <= self.end


class CampaignParticipant(models.Model):
    """Inclusão manual (ex.: 'Primeira Conquista', 'Volta por Cima'). Se não houver nenhuma, vale o público."""

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="participants")
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="campaign_entries")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("campaign", "creator")]


class PointsLedger(models.Model):
    """Extrato de pontos (tela na V2)."""

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    points = models.IntegerField()
    reason = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)


class Announcement(AudienceMixin):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    title = models.CharField("título", max_length=140)
    body = models.TextField("texto")
    link = models.URLField(blank=True)
    pinned = models.BooleanField("fixar no topo", default=False)
    publish_at = models.DateTimeField("publicar em", default=timezone.now)
    expires_at = models.DateTimeField("expira em", null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    notified = models.BooleanField(default=False, editable=False)

    class Meta:
        ordering = ["-pinned", "-publish_at"]
        verbose_name = "aviso"

    def __str__(self):
        return self.title


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=30)
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class Course(AudienceMixin):
    """Módulo da Hera Academy (a página educacional da visão). Abre por nível e por marco, nunca pelo tempo de casa
    sozinho (regras em engage/academy.py)."""

    OPENS = [
        ("acesso", "No primeiro acesso"),
        ("primeira_live", "Depois da 1ª LIVE"),
        ("dia15", "Ao fechar os 14 dias, ou no D15"),
        ("nivel", "Ao chegar a um nível"),
        ("gestao", "Só com liberação da gestão (cursos extras)"),
    ]

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    title = models.CharField("título", max_length=140)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    published = models.BooleanField(default=True)
    opens_on = models.CharField("quando abre", max_length=20, choices=OPENS, default="acesso")
    opens_level = models.PositiveSmallIntegerField("nível que abre", null=True, blank=True,
                                                   help_text="Só para \"Ao chegar a um nível\". Ex.: 3 abre no Nível 3.")

    class Meta:
        ordering = ["order"]
        verbose_name = "módulo da Hera Academy"
        verbose_name_plural = "módulos da Hera Academy"

    def __str__(self):
        return self.title


class Lesson(models.Model):
    TOPICS = [
        ("", "—"),
        ("rotina", "Rotina e dias de LIVE"),
        ("interacao", "Interação"),
        ("batalhas", "Batalhas e co-host"),
        ("fa_clube", "Fã-clube"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=140)
    video_url = models.URLField("link do vídeo")
    minutes = models.PositiveSmallIntegerField(default=5)
    about_battles = models.BooleanField("explica a batalha oficial", default=False,
                                        help_text="Marque na aula que explica o que é uma batalha oficial. Ela ganha um botão na tela Pedir batalha.")
    topic = models.CharField("ponto que a aula ajuda", max_length=20, choices=TOPICS, blank=True,
                             help_text="Quando esse ponto cai no mês do criador, o app recomenda esta aula.")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "aula"

    def __str__(self):
        return self.title


class ModuleRelease(models.Model):
    """Módulo liberado antes da hora pela gestão para um criador (ou curso extra liberado)."""

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="module_releases")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="releases")
    released_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    released_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("creator", "course")]


class LessonPick(models.Model):
    """A aula que a gestora escolheu na ficha. Vence a sugestão automática da aula recomendada."""

    creator = models.OneToOneField(Creator, on_delete=models.CASCADE, related_name="lesson_pick")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="+")
    picked_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    picked_at = models.DateTimeField(default=timezone.now)


class LessonProgress(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="lesson_progress")
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("lesson", "creator")]


class Tip(AudienceMixin):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    text = models.TextField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.text[:60]


class MessageTemplate(models.Model):
    """Biblioteca de mensagens: scripts do Playbook com variáveis {nome}, {dias_validos} etc.

    O mesmo código pode ter variações por trilha e por "faz batalha" (campo `variant`). Quem escolhe a variação
    certa para cada criador é engage.services.template_for. Toda mudança de texto guarda a versão anterior
    (MessageVersion) e passa pelo verificador de tom (engage/tom.py)."""

    SOURCES = [("playbook", "Playbook"), ("roteiro", "Roteiro online"), ("provisorio", "Provisório: sem texto no Playbook"),
               ("agencia", "Criado pela agência")]
    BATTLES = [("", "Tanto faz"), ("sim", "Faz ou topa batalha"), ("nao", "Não faz batalha")]

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    code = models.CharField("código", max_length=30)
    variant = models.CharField("variação", max_length=40, blank=True, help_text="Vazio = modelo geral. Ex.: outra-agencia, sem-batalha.")
    stage = models.CharField("etapa", max_length=80)
    title = models.CharField("título", max_length=140)
    body = models.TextField("mensagem")
    tracks = models.JSONField("trilhas (vazio = todas)", default=list, blank=True)
    battles = models.CharField("faz batalha", max_length=3, choices=BATTLES, blank=True)
    source = models.CharField("origem", max_length=12, choices=SOURCES, default="agencia")
    marketing = models.BooleanField("categoria marketing (sem uso)", default=False)
    order = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("agency", "code", "variant")]
        verbose_name = "modelo de mensagem"
        verbose_name_plural = "modelos de mensagem"

    def __str__(self):
        return f"{self.code}{'/' + self.variant if self.variant else ''} · {self.title}"

    @property
    def provisional(self):
        return self.source == "provisorio"

    @property
    def tone_problems(self):
        from .tom import verificar_tom_mensagem

        return verificar_tom_mensagem(self.body)

    @property
    def variables(self):
        import re

        return sorted(set(re.findall(r"\{(\w+)\}", self.body)))

    def clean(self):
        """Verificador de tom: vale para a tela Mensagens e para o painel de cadastros."""
        from django.core.exceptions import ValidationError

        problems = self.tone_problems
        if problems:
            raise ValidationError({"body": "O verificador de tom barrou esta mensagem: " + "; ".join(problems) + "."})


class MessageVersion(models.Model):
    """Versão anterior de um modelo de mensagem, guardada a cada mudança de texto ou de título. Nada é sobrescrito."""

    template = models.ForeignKey(MessageTemplate, on_delete=models.CASCADE, related_name="versions")
    title = models.CharField(max_length=140)
    body = models.TextField()
    saved_at = models.DateTimeField("valeu até", default=timezone.now)
    saved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
                                 help_text="Quem fez a mudança que aposentou esta versão.")

    class Meta:
        ordering = ["-saved_at", "-id"]
        verbose_name = "versão anterior de mensagem"


class FaqItem(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    category = models.CharField("categoria", max_length=60)
    question = models.CharField("pergunta", max_length=240)
    answer = models.TextField("resposta", help_text="Pode usar {nome}, {dias_validos_mes}, {horas_mes}, {falta_dias_min}, {falta_horas_min}, {tier}")
    keywords = models.CharField("sinônimos/palavras-chave", max_length=400, blank=True, help_text="separados por vírgula, ex.: pk, batalha")
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)
    helpful = models.PositiveIntegerField(default=0, editable=False)
    not_helpful = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        verbose_name = "pergunta (Q&A)"
        verbose_name_plural = "perguntas (Q&A)"

    def __str__(self):
        return self.question


class FaqSearch(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    query = models.CharField(max_length=240)
    results = models.PositiveSmallIntegerField()
    at = models.DateTimeField(auto_now_add=True)


class SupportTicket(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="tickets")
    question = models.TextField()
    status = models.CharField(max_length=20, default="aberto", choices=[("aberto", "Aberto"), ("respondido", "Respondido")])
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)


class PartnerOffer(AudienceMixin):
    CATEGORIES = [
        ("iluminacao", "Iluminação"), ("som", "Som"), ("cadeira", "Cadeira"), ("celular", "Celular e acessórios"),
        ("cursos", "Cursos"), ("servicos", "Serviços"), ("outros", "Outros"),
    ]
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    brand = models.CharField("marca", max_length=80)
    title = models.CharField("oferta", max_length=140)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    coupon = models.CharField("cupom", max_length=60, blank=True)
    url = models.URLField("link", blank=True)
    affiliate = models.BooleanField("link gera comissão para a Hera", default=False)
    recommended_for = models.CharField("kit recomendado para", max_length=60, blank=True, help_text="ex.: Tier 1–2")
    valid_until = models.DateField("válido até", null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "benefício"

    def __str__(self):
        return f"{self.brand} · {self.title}"


class OfferClick(models.Model):
    offer = models.ForeignKey(PartnerOffer, on_delete=models.CASCADE, related_name="clicks")
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    used_coupon = models.BooleanField(default=False)
    at = models.DateTimeField(auto_now_add=True)


class Survey(AudienceMixin):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    title = models.CharField(max_length=140)
    intro = models.CharField(max_length=240, blank=True)
    anonymous = models.BooleanField("respostas anônimas", default=False)
    opens_at = models.DateTimeField(default=timezone.now)
    closes_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "pesquisa"

    def __str__(self):
        return self.title

    def is_open(self):
        now = timezone.now()
        return self.opens_at <= now and (self.closes_at is None or now <= self.closes_at)


class SurveyQuestion(models.Model):
    KINDS = [("nps", "Nota 0–10"), ("single", "Escolha única"), ("multi", "Múltipla escolha"), ("text", "Texto curto")]
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=240)
    kind = models.CharField(max_length=10, choices=KINDS)
    options = models.JSONField(default=list, blank=True, help_text='["opção 1", "opção 2"]')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class SurveyCompletion(models.Model):
    """Quem já respondeu (separado das respostas, para permitir anonimato)."""

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="completions")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("survey", "user")]


class SurveyAnswer(models.Model):
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name="answers")
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)  # vazio se anônima
    value = models.TextField()
    at = models.DateTimeField(auto_now_add=True)


class CommunityProfile(models.Model):
    """Cartão público do streamer dentro da agência (@ do TikTok é público).
    Usado no convite de batalha e, na V2, na Comunidade. Sem dados sensíveis, por isso fora do RLS."""

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    creator = models.OneToOneField(Creator, on_delete=models.CASCADE, related_name="community")
    public_name = models.CharField(max_length=80)
    username = models.CharField(max_length=120)
    tier = models.PositiveSmallIntegerField(default=1)
    accepts_battles = models.BooleanField("aceita convites de batalha", default=True)
    about = models.TextField("sobre mim", blank=True)
    brand_link = models.URLField("link da minha marca", blank=True)

    def __str__(self):
        return f"@{self.username}"


class CampaignStanding(models.Model):
    """Progresso de cada participante, calculado após cada importação. Sem posição: não existe ranking no app."""

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="standings")
    creator_id_ref = models.BigIntegerField(db_index=True)
    username = models.CharField(max_length=120)
    tier = models.PositiveSmallIntegerField()
    value = models.DecimalField(max_digits=14, decimal_places=2)
    reached_goal = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["username"]


class BattleRequest(models.Model):
    KINDS = [("oficial", "Batalha agendada"), ("especial", "Batalha especial"), ("pk", "PK agendada"), ("cohost", "Cohost"), ("tematica", "LIVE temática")]
    STATUS = [("pendente", "Aguardando a Hera"), ("aprovada", "Aprovada"), ("outro_horario", "Sugerido outro dia ou hora"), ("recusada", "Não aprovada"), ("realizada", "Realizada")]
    ROUNDS = [(1, "1 round"), (3, "3 rounds")]
    MAX_OTHER_OPTIONS = 3
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="battle_requests")
    kind = models.CharField("tipo", max_length=20, choices=KINDS)
    date = models.DateField("data")
    time = models.TimeField("horário")
    other_options = models.JSONField("outras opções de dia e hora", default=list, blank=True,
                                     help_text='Lista de {"date": "AAAA-MM-DD", "time": "HH:MM"} oferecidas pelo criador.')
    rounds = models.PositiveSmallIntegerField("rounds", choices=ROUNDS, default=1)
    duration_min = models.PositiveSmallIntegerField("duração (min)", default=60)
    goal_diamonds = models.PositiveIntegerField("meta de diamantes", null=True, blank=True)
    opponent = models.ForeignKey(CommunityProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="com quem")
    opponent_text = models.CharField("com quem (texto livre)", max_length=120, blank=True)
    promote = models.BooleanField("divulgar no Grupo de Avisos", default=False)
    notes = models.TextField("observações", blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="pendente")
    manager_reply = models.CharField("resposta da gestora", max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-time"]

    @property
    def other_options_display(self):
        """Outras opções de dia e hora, prontas para mostrar (ex.: '14/11 às 20:00')."""
        import datetime as dt

        out = []
        for o in self.other_options or []:
            try:
                d, t = dt.date.fromisoformat(o["date"]), dt.time.fromisoformat(o["time"])
            except (KeyError, TypeError, ValueError):
                continue
            out.append(f"{d:%d/%m} às {t:%H:%M}")
        return out

    def crosses_tiktok_day(self):
        """O dia TikTok vira às 21h de Brasília: LIVE que cruza esse horário divide as horas em 2 dias."""
        start = self.time.hour * 60 + self.time.minute
        return start < 21 * 60 < start + self.duration_min
