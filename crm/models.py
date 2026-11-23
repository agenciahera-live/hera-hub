from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import Agency, PartnerGroup

User = settings.AUTH_USER_MODEL


class CreatorStatus(models.TextChoices):
    PENDENTE = "pendente", "Cadastro pendente"
    CONVIDADO = "convidado", "Convidado"
    ATIVO = "ativo", "Ativo"
    EM_SAIDA = "em_saida", "Em saída (aviso prévio)"
    SAIU = "saiu", "Saiu"
    ANONIMIZADO = "anonimizado", "Anonimizado"


# Trilhas do Playbook. O cadastro do criador só sugere; quem define é a gestão.
TRACKS = [
    ("primeira_live", "Primeira LIVE"),
    ("outra_agencia", "Veio de outra agência"),
    ("nivel_publico", "Já tem nível e público"),
]

# Nichos do roteiro de onboarding. O roteiro é o mesmo para todos; por nicho mudam o teste do D2, o que entra
# no lugar da batalha no D4 e os ganchos de conversa (o guia de cada nicho está em engage/playbook.py:NICHE_GUIDE).
NICHES = [
    ("gamer", "Gamer"),
    ("bate_papo", "Bate-papo e lifestyle"),
    ("musica", "Música e talento"),
    ("fe_educacao", "Fé, educação e conteúdo de nicho"),
    ("sem_aparecer", "Quem não quer aparecer muito"),
    ("outro", "Outro"),
]
BATTLES = [("", "Não sei ainda"), ("sim", "Faz ou topa batalha"), ("nao", "Não faz batalha")]

# Motivo de quem parou ou saiu (visão, "Regras de contato da carteira"). Saúde: só a categoria, sem detalhes.
STOP_REASONS = [
    ("viagem", "Viagem"),
    ("saude", "Saúde"),
    ("trabalho_estudo", "Trabalho ou estudo"),
    ("tecnico", "Problema técnico"),
    ("desmotivou", "Desmotivou"),
    ("pessoal", "Problema pessoal"),
    ("outra_agencia", "Outra agência"),
    ("nao_respondeu", "Não respondeu"),
    ("outro", "Outro"),
]
# "Desmotivou" pede o porquê.
STOP_DETAILS = [
    ("poucos_diamantes", "Poucos diamantes"),
    ("pouco_publico", "Pouco público"),
    ("nao_sabe", "Não sabe o que fazer na LIVE"),
    ("vergonha", "Vergonha"),
    ("outro", "Outro"),
]


class Creator(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="creators")
    tiktok_id = models.CharField("ID do criador (TikTok)", max_length=32)
    display_name = models.CharField("nome", max_length=120)
    username = models.CharField("@ atual", max_length=120)
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="creator")
    status = models.CharField(max_length=20, choices=CreatorStatus.choices, default=CreatorStatus.PENDENTE)
    joined_at = models.DateTimeField("entrada na agência (UTC)", null=True, blank=True)
    first_live_at = models.DateField("1ª LIVE (aprox.)", null=True, blank=True)
    first_live_planned = models.DateField("data combinada para a 1ª LIVE", null=True, blank=True)
    partner_group = models.ForeignKey(PartnerGroup, null=True, blank=True, on_delete=models.SET_NULL)
    recruited_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="recruited",
                                     verbose_name="recrutadora")
    referred_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals",
                                    verbose_name="indicado por (criador da Hera)",
                                    help_text="Base do Indique e ganhe: qual criador da agência indicou esta pessoa.")
    track = models.CharField("trilha (definida pela gestão)", max_length=20, choices=TRACKS, blank=True)
    track_suggested = models.CharField("trilha sugerida pelo cadastro", max_length=20, choices=TRACKS, blank=True)
    niche = models.CharField("nicho", max_length=60, choices=NICHES, blank=True)
    does_battles = models.CharField("faz batalha", max_length=3, choices=BATTLES, blank=True,
                                    help_text="Quem não faz batalha recebe as alternativas do roteiro (co-host, convidado, desafio com o chat).")
    suggested_agent_email = models.CharField("Agente no Backstage (sugestão de carteira)", max_length=200, blank=True)
    bio = models.TextField("sobre mim", blank=True)
    confirmed_username = models.BooleanField(default=False)
    app_tester = models.BooleanField("participa do teste do app", default=False,
                                     help_text="Marcado pelas sócias na tela Teste do app (passo 3.7).")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("agency", "tiktok_id")]
        ordering = ["display_name"]

    def __str__(self):
        return f"{self.display_name} (@{self.username})"

    @property
    def first_name(self):
        return (self.display_name or self.username).split(" ")[0]

    def days_in_agency(self, today=None):
        if not self.joined_at:
            return None
        today = today or timezone.now().date()
        return (today - self.joined_at.date()).days + 1

    def current_manager(self):
        a = self.assignments.filter(valid_to__isnull=True).select_related("manager").first()
        return a.manager if a else None


class CreatorPrivate(models.Model):
    """Dados pessoais com acesso mínimo (LGPD)."""

    creator = models.OneToOneField(Creator, on_delete=models.CASCADE, related_name="private")
    whatsapp = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    whatsapp_group_url = models.URLField("link do grupo individual no WhatsApp", blank=True,
                                         help_text="Link de convite do grupo do streamer com a gestora (chat.whatsapp.com/...).")
    # Aniversário: só dia e mês (o ano não é pedido). Informado no primeiro acesso ou pela gestão.
    birth_day = models.PositiveSmallIntegerField("dia do aniversário", null=True, blank=True)
    birth_month = models.PositiveSmallIntegerField("mês do aniversário", null=True, blank=True)
    # Indique e ganhe (passo 4.7): o link de indicação do app do TikTok, que o próprio criador cola e guarda
    referral_link = models.URLField("link de indicação (Indique e ganhe)", blank=True)


class CreatorUsername(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="usernames")
    username = models.CharField(max_length=120)
    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("creator", "username")]


class PortfolioAssignment(models.Model):
    """Carteira gestora ↔ creator, com histórico. Atribuição manual (decisão 29/09)."""

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="assignments")
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portfolio")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
                                    verbose_name="quem atribuiu")

    class Meta:
        indexes = [models.Index(fields=["manager", "valid_to"])]


class Absence(models.Model):
    """A gestora avisou "Hoje não trabalho" (visão, "Ausência da gestora").

    Os itens do dia passam para o dia seguinte, na ordem da fila. Os que não podem esperar (D10, D12, D14, encerramento,
    batalha oficial e restrição) vão para quem cobre: uma sócia ou uma recrutadora. Quem cobre enxerga a carteira dela
    só nesse dia (no banco: função hera_covers). Cancelar ("Voltei") não apaga: fica a data do cancelamento."""

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="absences")
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name="absences", verbose_name="gestora")
    day = models.DateField("dia")
    cover = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="covering",
                              verbose_name="quem cobre", help_text="Vazio = as sócias.")
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-day", "-id"]
        indexes = [models.Index(fields=["cover", "day"])]
        constraints = [models.UniqueConstraint(fields=["manager", "day"], condition=models.Q(cancelled_at__isnull=True),
                                               name="uma_ausencia_ativa_por_gestora_por_dia")]


TAG_CHOICES = [
    ("novo", "Novo"),
    ("potencial", "Potencial"),
    ("alto_desempenho", "Alto desempenho"),
    ("inativo", "Inativo"),
    ("risco", "Risco"),
    ("monitoria", "Precisa de monitoria"),
    ("crescimento", "Em crescimento"),
]


class CreatorTag(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="tags")
    tag = models.CharField(max_length=30, choices=TAG_CHOICES)
    set_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("creator", "tag")]


class Note(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class OneOnOne(models.Model):
    """Registro de 1:1 com os 7 blocos do Playbook e o cabeçalho da visão (passo 4.2; regras em crm/one_on_one.py).

    O print da conversa não é enviado ao app (decisão de 19/11/2026): a gestora guarda no drive dela e marca
    `print_saved`. Sem registro completo, o 1:1 não conta."""

    CHANNELS = [("ligacao", "Ligação"), ("video", "Vídeo"), ("audio", "Áudio"), ("mensagem", "Mensagem")]
    MIN_ACTIONS = 2  # visão: plano com 2 a 3 ações

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="one_on_ones")
    manager = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)  # quem registrou
    conducted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="quem conduziu")
    channel = models.CharField("canal", max_length=10, choices=CHANNELS, blank=True)
    print_saved = models.BooleanField("guardei o print da conversa no meu drive", default=False)
    notes = models.TextField("anotações", blank=True)
    date = models.DateField(default=timezone.localdate)
    tier_at = models.PositiveSmallIntegerField(null=True, blank=True)
    b1_performance = models.TextField("1. Performance da semana/mês", blank=True)
    b2_constancia = models.TextField("2. Constância e agenda", blank=True)
    b3_qualidade = models.TextField("3. Qualidade de conteúdo", blank=True)
    b4_monetizacao = models.TextField("4. Monetização", blank=True)
    b5_dificuldades = models.TextField("5. Dificuldades do creator", blank=True)
    b7_next_date = models.DateField("7. Próximo 1:1", null=True, blank=True)
    reviewed_previous_plan = models.BooleanField("revisei o plano anterior", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    @property
    def missing(self):
        """O que falta para o 1:1 contar (vazio = completo)."""
        out = []
        if not self.channel:
            out.append("canal")
        names = ["1. Performance", "2. Constância", "3. Qualidade", "4. Monetização", "5. Dificuldades"]
        blocks = [self.b1_performance, self.b2_constancia, self.b3_qualidade, self.b4_monetizacao, self.b5_dificuldades]
        out += [n for n, b in zip(names, blocks) if not (b or "").strip()]
        if len(self.actions.all()) < self.MIN_ACTIONS:
            out.append(f"6. Plano ({self.MIN_ACTIONS} ações ou mais)")
        if self.b7_next_date is None:
            out.append("7. Próximo 1:1")
        if not self.print_saved:
            out.append("print guardado")
        return out

    @property
    def complete(self):
        return not self.missing

    @property
    def conductor(self):
        return self.conducted_by or self.manager


class ActionItem(models.Model):
    one_on_one = models.ForeignKey(OneOnOne, null=True, blank=True, on_delete=models.CASCADE, related_name="actions")
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="action_items")
    action = models.CharField("6. Ação", max_length=240)
    owner = models.CharField("responsável", max_length=80)
    due_date = models.DateField("prazo")
    done = models.BooleanField(default=False)


class Contact(models.Model):
    """Cada mensagem que a gestora marcou como enviada ("Enviei")."""

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="contacts")
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    channel = models.CharField(max_length=20, default="whatsapp")
    template_code = models.CharField(max_length=40, blank=True)
    body = models.TextField(blank=True)
    sent_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-sent_at"]


class CadenceState(models.Model):
    """Cadência de não-resposta (+24h, +2d, +3d, +5d)."""

    STEPS = [(1, "+24h"), (2, "+2 dias"), (3, "+3 dias"), (4, "+5 dias")]
    STEP_OFFSETS_H = {1: 24, 2: 48, 3: 72, 4: 120}
    STEP_TEMPLATE = {1: "NR-24H", 2: "NR-2D", 3: "NR-3D", 4: "NR-5D"}

    creator = models.OneToOneField(Creator, on_delete=models.CASCADE, related_name="cadence")
    started_at = models.DateTimeField(default=timezone.now)
    step = models.PositiveSmallIntegerField(default=1, choices=STEPS)
    resolved_at = models.DateTimeField(null=True, blank=True)

    @property
    def due_at(self):
        return self.started_at + timezone.timedelta(hours=self.STEP_OFFSETS_H[self.step])


class OnboardingItem(models.Model):
    ANCHORS = [("entrada", "Dia de casa"), ("primeira_live", "Dia do desafio (a partir da 1ª LIVE)")]
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    code = models.CharField(max_length=30)
    label = models.CharField(max_length=120)
    anchor = models.CharField(max_length=20, choices=ANCHORS, default="entrada")
    day = models.PositiveSmallIntegerField()
    auto_rule = models.CharField(max_length=30, blank=True, help_text="streams>=N, battles>=1, meta_onboarding")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = [("agency", "code")]

    def __str__(self):
        return self.label


class CreatorOnboarding(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="onboarding")
    item = models.ForeignKey(OnboardingItem, on_delete=models.CASCADE)
    done = models.BooleanField(default=False)
    auto = models.BooleanField(default=False)
    done_at = models.DateTimeField(null=True, blank=True)
    done_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = [("creator", "item")]


class ExitRecord(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="exits")
    requested_at = models.DateField(default=timezone.localdate)
    within_free_period = models.BooleanField("antes de 15 dias", default=False)
    reason_code = models.CharField("motivo", max_length=20, choices=STOP_REASONS, blank=True)
    reason = models.TextField("motivo declarado (detalhe)", blank=True)
    action = models.CharField(
        max_length=40,
        choices=[("excluida", "Excluída do sistema pela agência"), ("aviso_previo", "Aviso prévio pelo app"), ("detectada", "Detectada na importação")],
        default="aviso_previo",
    )
    notice_ends_at = models.DateField(null=True, blank=True)
    return_eligible_at = models.DateField(null=True, blank=True)
    anonymize_at = models.DateField(null=True, blank=True)
    reviewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-requested_at"]


class AccessCode(models.Model):
    """Código de acesso ao app. A gestão gera e envia no grupo individual; o criador usa em "Primeiro acesso"
    (ou para criar uma senha nova). Cada código vale uma vez, e gerar outro cancela o anterior."""

    MAX_ATTEMPTS = 5
    ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem I, O, 0 e 1, que se confundem
    LENGTH = 8

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="access_codes")
    code = models.CharField(max_length=12)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField("cancelado em", null=True, blank=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at", "-id"]

    @property
    def display(self):
        return f"{self.code[:4]}-{self.code[4:]}"

    def is_active(self, now=None):
        return self.used_at is None and self.revoked_at is None and self.expires_at > (now or timezone.now())


class Reply(models.Model):
    """O criador respondeu a uma mensagem ("Respondeu") ou escreveu por conta própria ("O criador me escreveu").
    Cada registro é uma linha nova: nada é sobrescrito."""

    KINDS = [("respondeu", "Respondeu"), ("escreveu", "O criador escreveu")]
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="replies")
    kind = models.CharField(max_length=12, choices=KINDS)
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.SET_NULL, related_name="replies")
    note = models.TextField("o que disse (resumo)", blank=True)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]


class StopReason(models.Model):
    """Motivo de quem parou de fazer LIVE, registrado pela gestão. Se houver data de volta, os alertas esperam até lá."""

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="stop_reasons")
    reason = models.CharField("motivo", max_length=20, choices=STOP_REASONS)
    detail = models.CharField("por que desmotivou", max_length=20, choices=STOP_DETAILS, blank=True)
    return_date = models.DateField("data de volta informada", null=True, blank=True)
    note = models.TextField("observação", blank=True)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]


class Reminder(models.Model):
    """Lembrete com data ("retorno prometido até dia 15"). Entra na fila da gestora no dia marcado."""

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="reminders")
    text = models.CharField("lembrete", max_length=240)
    due_date = models.DateField("para o dia")
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    done_at = models.DateTimeField(null=True, blank=True)
    done_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["due_date", "id"]


class BattleRecord(models.Model):
    """Registro de uma batalha agendada depois que ela aconteceu, feito pela gestão.
    Serve para calibrar as próximas (oponente, rounds, resultado). O criador não vê."""

    RESULTS = [("venceu", "Venceu"), ("perdeu", "Perdeu"), ("empate", "Empate"), ("nao_aconteceu", "Não aconteceu")]
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="battle_records")
    request = models.ForeignKey("engage.BattleRequest", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="records", verbose_name="pedido de batalha ligado")
    date = models.DateField("data da batalha")
    opponent = models.CharField("oponente (@ e agência)", max_length=120, blank=True)
    rounds = models.PositiveSmallIntegerField("rounds", default=1)
    result = models.CharField("resultado", max_length=15, choices=RESULTS)
    diamonds = models.PositiveIntegerField("diamantes do criador na batalha", null=True, blank=True)
    opponent_diamonds = models.PositiveIntegerField("diamantes do oponente", null=True, blank=True)
    note = models.TextField("observação para as próximas", blank=True)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date", "-id"]


class AccountCase(models.Model):
    """Restrição ou banimento na conta do criador no TikTok. Enquanto estiver aberto, fica no primeiro bloco da fila;
    no 4º dia sem solução, sobe para as sócias (rotina diária)."""

    KINDS = [("restricao", "Restrição"), ("banimento", "Banimento")]
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="account_cases")
    kind = models.CharField("tipo", max_length=12, choices=KINDS, default="restricao")
    opened_on = models.DateField("aberto em", default=timezone.localdate)
    note = models.TextField("o que aconteceu", blank=True)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    escalated_at = models.DateTimeField("subiu para as sócias em", null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.CharField("como terminou", max_length=240, blank=True)
    resolved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-opened_on", "-id"]

    def days_open(self, today=None):
        return ((today or timezone.localdate()) - self.opened_on).days + 1


class Visit(models.Model):
    """Visita da gestora a uma LIVE do criador, com nota de 1 a 3. Alimenta a sugestão de visita da fila."""

    SCORES = [(1, "1 · precisa de ajuda"), (2, "2 · no caminho"), (3, "3 · muito boa")]
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="visits")
    date = models.DateField("dia da visita", default=timezone.localdate)
    score = models.PositiveSmallIntegerField("nota", choices=SCORES)
    note = models.TextField("o que viu (cenário, câmera, áudio, interação, batalha, diretrizes)", blank=True)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date", "-id"]


class AlertDismissal(models.Model):
    """Item da fila adiado pela gestora, com motivo. Até a data, o item não volta para a fila."""

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="dismissals")
    code = models.CharField(max_length=40)
    reason = models.CharField("motivo do adiamento", max_length=240, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    until = models.DateTimeField()
    by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)


# ------------------------------------------------------------------ painel das sócias (etapa 4, passo 4.1)
class ApprovalRequest(models.Model):
    """Pedido de decisão às sócias (visão, princípio 9 e "As aprovações viram uma lista no painel").

    Neste passo: manter ou encerrar um criador, pedido pela gestora a partir da fila. Campanha nova e premiação
    entram nos passos 4.5 e 4.6 (por isso o criador pode ficar vazio). Só as sócias decidem; nada é apagado."""

    KINDS = [("manter_encerrar", "Manter ou encerrar"), ("campanha", "Campanha nova"), ("premiacao", "Premiação")]
    DECISIONS = {"manter_encerrar": [("manter", "Manter"), ("encerrar", "Encerrar")],
                 "premiacao": [("aprovar", "Aprovar"), ("recusar", "Não aprovar")]}
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="approvals")
    creator = models.ForeignKey(Creator, null=True, blank=True, on_delete=models.CASCADE, related_name="approvals")
    kind = models.CharField(max_length=20, choices=KINDS, default="manter_encerrar")
    reason = models.CharField("motivo (item da fila)", max_length=160, blank=True)
    item_code = models.CharField(max_length=40, blank=True)
    note = models.TextField("observação de quem pediu", blank=True)
    requested_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    requested_at = models.DateTimeField(default=timezone.now)
    decision = models.CharField(max_length=20, blank=True)
    decision_note = models.TextField("observação da decisão", blank=True)
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    @property
    def pending(self):
        return not self.decided_at

    @property
    def decision_label(self):
        return dict(self.DECISIONS.get(self.kind, [])).get(self.decision, self.decision)


class SentCheck(models.Model):
    """Sorteio semanal de 5 "Enviei" para as sócias conferirem no grupo individual (visão, "Conferência por sorteio")."""

    RESULTS = [("", "A conferir"), ("estava", "Conferi: estava lá"), ("nao_achei", "Não encontrei")]
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="sent_checks")
    week = models.DateField("segunda da semana do sorteio")
    contact = models.ForeignKey("Contact", on_delete=models.CASCADE, related_name="checks")
    manager = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+", verbose_name="quem marcou Enviei")
    result = models.CharField(max_length=12, choices=RESULTS, blank=True)
    note = models.CharField(max_length=240, blank=True)
    checked_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("week", "contact")]
        ordering = ["week", "id"]


class QueueDay(models.Model):
    """Retrato da fila do dia de cada gestora, tirado pela rotina das 6h, para o painel medir a fila concluída.

    Guarda só os criadores com mensagem na fila (o @ não sai daqui); concluir = "Enviei" ou "Adiar" no mesmo dia."""

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="queue_days")
    manager = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    day = models.DateField()
    creator_ids = models.JSONField(default=list)
    items = models.PositiveIntegerField("itens na fila (mensagens e tarefas)", default=0)
    overflow = models.PositiveIntegerField("mensagens acima do teto", default=0)

    class Meta:
        unique_together = [("agency", "manager", "day")]


class RiskSignal(models.Model):
    """Sinal de risco de um criador Diamante marcado pela gestora a partir da conversa (Playbook, seção 5; passo 4.3).

    Vale por 30 dias (decisão da Mariana de 19/11/2026); o registro fica na linha do tempo. Só a gestão vê."""

    KINDS = [("demorou", "Demorou a responder"), ("tom", "Mudou o tom"), ("outra_agencia", "Falou de outra agência"),
             ("reclamou", "Reclamou de algo")]
    VALID_DAYS = 30
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="risk_signals")
    kind = models.CharField(max_length=20, choices=KINDS)
    note = models.CharField("observação", max_length=240, blank=True)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]


# ------------------------------------------------------------------ Indique e ganhe (passo 4.7; regras em crm/referrals.py)
class ReferralBand(models.Model):
    """Faixa do regulamento do Indique e ganhe (novembro de 2026): no mês N da pessoa indicada, horas E dias válidos
    mínimos e o bônus. Vale a maior faixa atingida, sem somar. Editável em Configurações (nada fixo no código)."""

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="referral_bands")
    program_month = models.PositiveSmallIntegerField("mês da pessoa indicada (1, 2 ou 3)")
    min_hours = models.PositiveSmallIntegerField("horas de LIVE no mês")
    min_valid_days = models.PositiveSmallIntegerField("dias válidos no mês")
    amount = models.DecimalField("bônus (R$)", max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["program_month", "min_hours"]
        verbose_name = "faixa do Indique e ganhe"
        verbose_name_plural = "faixas do Indique e ganhe"

    def __str__(self):
        return f"Mês {self.program_month}: {self.min_hours}h e {self.min_valid_days} dias → R$ {self.amount}"


class Referral(models.Model):
    """Uma indicação do Indique e ganhe: quem indicou (`referrer`) e a pessoa indicada (`referred`).

    Nasce quando a gestão preenche "indicado por" na ficha (decisão da Mariana de 22/11/2026, 1A). O app confere sozinho
    o que dá para conferir (`auto_issue`: já fez parte da Hera, grupo parceiro); o resto as sócias conferem e marcam
    válida ou não validada. Quem indicou vê só a situação, nunca os números da pessoa indicada.
    Só o sistema e as sócias gravam (RLS em web/migrations/0014)."""

    STATUSES = [("", "Em andamento"), ("valida", "Válida"), ("nao_validada", "Não validada")]
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="referrals")
    referred = models.OneToOneField(Creator, on_delete=models.CASCADE, related_name="referral", verbose_name="pessoa indicada")
    referrer = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="referrals_made", verbose_name="quem indicou")
    registered_at = models.DateTimeField("registrada em", default=timezone.now)
    registered_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    late = models.BooleanField("registrada depois da entrada", default=False)
    auto_issue = models.CharField("o que o app encontrou", max_length=160, blank=True)
    status = models.CharField(max_length=14, choices=STATUSES, blank=True, default="")
    reason = models.CharField("motivo (não validada)", max_length=240, blank=True)
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-registered_at"]


class ReferralBonus(models.Model):
    """Bônus de uma indicação em um mês fechado (Mês 1, 2, 3) ou o bônus único de graduação. Calculado pela rotina
    diária com os dados do Backstage; `amount` 0 = o mês não gerou bônus, com o motivo em forma de fato.
    Quem indicou lê os dele; só as sócias e o financeiro leem todos; a gestora não vê valores."""

    KINDS = [("m1", "Mês 1"), ("m2", "Mês 2"), ("m3", "Mês 3"), ("grad", "Graduação")]
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name="bonuses")
    kind = models.CharField(max_length=4, choices=KINDS)
    month = models.DateField("mês apurado")
    amount = models.DecimalField("bônus (R$)", max_digits=8, decimal_places=2, default=0)
    reason = models.CharField("por que não gerou bônus", max_length=200, blank=True)
    computed_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateField("pago em", null=True, blank=True)
    paid_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    receipt_at = models.DateField("recibo assinado recebido em", null=True, blank=True)
    receipt_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        unique_together = [("referral", "kind")]
        ordering = ["month", "kind"]


class Award(models.Model):
    """Premiação de campanha (passo 4.6; decisões da Mariana de 23/11/2026).

    O criador não pede prêmio: a Hera envia quando ele ganha. A gestora ou uma sócia registra na ficha o que ganhou,
    o tipo (diamantes na LIVE ou Pix), o valor e a data; as sócias aprovam todo prêmio (pedido `ApprovalRequest`
    "premiacao", que só elas decidem, também no banco); depois a entrega: diamantes na LIVE (gestora ou sócia marca a
    data) ou Pix (financeiro ou sócia marca "pago em", com recibo preenchido e "recibo recebido").
    O criador não lê esta tabela (RLS em web/migrations/0016)."""

    KINDS = [("diamantes", "Diamantes na LIVE"), ("pix", "Pix")]
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="awards")
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="awards")
    campaign = models.ForeignKey("engage.Campaign", null=True, blank=True, on_delete=models.SET_NULL, related_name="awards")
    campaign_name = models.CharField("campanha (texto)", max_length=120, blank=True,
                                     help_text="Preenchido com o nome da campanha escolhida, ou escrito quando ela não está no app.")
    title = models.CharField("o que ganhou", max_length=160, help_text="Ex.: 1º lugar, faixa de 50 mil diamantes")
    kind = models.CharField("tipo", max_length=10, choices=KINDS)
    diamonds = models.PositiveIntegerField("diamantes", null=True, blank=True)
    value = models.DecimalField("valor (R$)", max_digits=10, decimal_places=2, null=True, blank=True)
    won_on = models.DateField("ganhou em")
    note = models.CharField("observação", max_length=240, blank=True)
    registered_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    registered_at = models.DateTimeField(default=timezone.now)
    approval = models.OneToOneField(ApprovalRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="award")
    delivered_on = models.DateField("entregue em (LIVE ou Pix)", null=True, blank=True)
    delivered_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    receipt_at = models.DateField("recibo assinado recebido em", null=True, blank=True)
    receipt_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-won_on", "-registered_at"]

    @property
    def status(self):
        ap = self.approval
        if ap is None or not ap.decided_at:
            return "aguardando"
        if ap.decision != "aprovar":
            return "recusada"
        return "entregue" if self.delivered_on else "a_entregar"

    STATUS_LABELS = {"aguardando": "Aguardando as sócias", "recusada": "Não aprovada", "a_entregar": "A entregar", "entregue": "Entregue"}

    @property
    def status_label(self):
        return self.STATUS_LABELS[self.status]

    @property
    def prize_label(self):
        if self.kind == "pix":
            return f"Pix de R$ {self.value:.2f}".replace(".", ",") if self.value is not None else "Pix"
        return f"{self.diamonds:,} diamantes na LIVE".replace(",", ".") if self.diamonds else "Diamantes na LIVE"

    @property
    def where(self):
        return self.campaign.name if self.campaign_id else self.campaign_name


class PixInfo(models.Model):
    """Dados para receber por Pix (Indique e ganhe, passo 4.7; premiações, passo 4.6). Decisão da Mariana de 22/11/2026:
    ficam no app. Só o próprio criador grava; só ele, as sócias e o financeiro leem (RLS em web/migrations/0015).
    A gestora não vê. Apagados na anonimização (LGPD)."""

    KEY_TYPES = [("cpf", "CPF"), ("email", "E-mail"), ("telefone", "Celular"), ("aleatoria", "Chave aleatória")]
    creator = models.OneToOneField(Creator, on_delete=models.CASCADE, related_name="pix")
    full_name = models.CharField("nome completo (como no CPF)", max_length=160)
    cpf = models.CharField("CPF (só números)", max_length=11)
    key_type = models.CharField("tipo de chave Pix", max_length=10, choices=KEY_TYPES)
    key = models.CharField("chave Pix", max_length=140)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def cpf_masked(self):
        return f"***.{self.cpf[3:6]}.***-{self.cpf[-2:]}" if len(self.cpf) == 11 else "***"

    @property
    def cpf_display(self):
        c = self.cpf
        return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}" if len(c) == 11 else c

    @property
    def key_masked(self):
        k = self.key
        if self.key_type == "cpf":
            return self.cpf_masked
        if self.key_type == "email" and "@" in k:
            user, dom = k.split("@", 1)
            return f"{user[:2]}***@{dom}"
        return f"***{k[-4:]}" if len(k) > 4 else "***"
