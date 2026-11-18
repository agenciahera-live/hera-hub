from allauth.account.adapter import DefaultAccountAdapter


class InviteOnlyAccountAdapter(DefaultAccountAdapter):
    """Não existe cadastro aberto: o criador entra pelo código de acesso (crm/first_access.py) e a equipe é cadastrada pelas sócias."""

    def is_open_for_signup(self, request):
        return False
