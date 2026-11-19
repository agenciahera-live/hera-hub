"""Carga da biblioteca padrão de mensagens (engage/playbook.py) no banco de uma agência.

Dois usos:
- agência nova ou comando de preparo (setup_agency): só CRIA o que falta. Nunca mexe em texto que já existe,
  porque a agência pode ter editado a mensagem pela tela;
- migração de uma revisão do Playbook (overwrite=True): troca o texto pelo novo e guarda o anterior como versão.
"""
from . import playbook


def sync_defaults(agency, overwrite=False, MessageTemplate=None, MessageVersion=None, only_codes=None):
    """Devolve (criados, atualizados). As classes podem vir de uma migração (modelos históricos).

    `only_codes`: com overwrite, troca só esses códigos (revisão pontual). Os outros, que a agência pode ter editado
    pela tela, ficam como estão; os que faltam continuam sendo criados."""
    if MessageTemplate is None:
        from .models import MessageTemplate, MessageVersion
    created = updated = 0
    existing = {(t.code, t.variant): t for t in MessageTemplate.objects.filter(agency=agency)}
    for order, m in enumerate(playbook.MESSAGES):
        fields = {"stage": m["stage"], "title": m["title"], "body": m["body"], "tracks": m["tracks"], "battles": m["battles"],
                  "source": m["source"], "order": order}
        row = existing.get((m["code"], m["variant"]))
        if row is None:
            MessageTemplate.objects.create(agency=agency, code=m["code"], variant=m["variant"], **fields)
            created += 1
        elif overwrite and only_codes is not None and m["code"] not in only_codes:
            MessageTemplate.objects.filter(pk=row.pk).update(order=order)  # só a posição na lista acompanha
        elif overwrite:
            if row.body != m["body"] or row.title != m["title"]:
                MessageVersion.objects.create(template_id=row.pk, title=row.title, body=row.body)
                updated += 1
            MessageTemplate.objects.filter(pk=row.pk).update(**fields)  # update() não dispara o sinal: a versão já foi guardada acima
    if overwrite and only_codes is None:
        MessageTemplate.objects.filter(agency=agency, code__in=playbook.RETIRED).delete()
    return created, updated
