"""Porta de importação (sem login): o Claude envia aqui o arquivo da leitura diária do Backstage.

    POST /api/importacao/backstage/
    Authorization: Bearer <chave gerada pelas sócias em Importar dados>
    formulário com o campo "file" = planilha "Dados do criador" (.xlsx ou .csv)

Resposta em JSON. 200 = os dados entraram (ou o arquivo era repetido). 422 = o arquivo chegou, mas não foi gravado.
Toda a regra fica em data/port.py; aqui só se confere a chave e o arquivo.
"""
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from data import port

logger = logging.getLogger(__name__)


def _json(data, status):
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})  # acentos legíveis no terminal


def _fail(status, message):
    return _json({"ok": False, "situacao": "recusado", "mensagem": message}, status)


@csrf_exempt  # não há sessão nem cookie: quem autoriza é a chave no cabeçalho
@require_POST
def import_backstage(request):
    kind, _, token = request.headers.get("Authorization", "").partition(" ")
    key = port.key_for_token(token) if kind.lower() == "bearer" else None
    if key is None:
        return _fail(401, "Chave inválida ou cancelada. Peça às sócias uma chave nova em Importar dados.")
    f = request.FILES.get("file")
    if f is None:
        return _fail(400, "Envie a planilha no campo “file” do formulário.")
    if f.size > port.MAX_BYTES:
        return _fail(413, "Arquivo grande demais para ser a planilha do Backstage.")
    try:
        result = port.receive(key.agency, f.read(), f.name)
    except Exception:
        # Erro inesperado ao gravar: nada fica pela metade (a gravação é uma transação só). O detalhe vai para o log.
        logger.exception("Porta de importação: erro ao receber %s", f.name)
        return _fail(500, "Erro interno ao gravar a leitura. Nada foi alterado. Plano B: subir a planilha pela tela.")
    return _json(result.as_dict(), result.http_status)


MAX_JSON_BYTES = 5 * 1024 * 1024


@csrf_exempt
@require_POST
def import_campaigns(request):
    """Leitura de campanhas do Backstage (passo 3.4), enviada pelo Claude junto com a leitura diária.

        POST /api/importacao/campanhas/
        Authorization: Bearer <a mesma chave da leitura diária>
        Content-Type: application/json   (formato em engage/campaigns.py:receive_reading e na tela Importar dados)
    """
    import json

    from core.models import AuditLog
    from core.rls import system_context
    from engage import campaigns

    kind, _, token = request.headers.get("Authorization", "").partition(" ")
    key = port.key_for_token(token) if kind.lower() == "bearer" else None
    if key is None:
        return _fail(401, "Chave inválida ou cancelada. Peça às sócias uma chave nova em Importar dados.")
    if len(request.body) > MAX_JSON_BYTES:
        return _fail(413, "Leitura grande demais para a tela de campanhas do Backstage.")
    try:
        payload = json.loads(request.body.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        return _fail(400, "Envie a leitura em JSON (UTF-8).")
    try:
        with system_context():
            counts = campaigns.receive_reading(key.agency, payload)
            AuditLog.objects.create(agency=key.agency, action="leitura_de_campanhas", target="campanhas", detail=counts)
            if counts["campanhas_novas"]:
                n, w = counts["campanhas_novas"], counts["para_aprovar"]
                body = f"{n} campanha{'s' if n > 1 else ''} nova{'s' if n > 1 else ''}."
                if w:  # passo 4.5: as da plataforma esperam avaliação (desde 23/11, a gestora no Dashboard ou uma sócia)
                    body += (f" {w} espera{'m' if w > 1 else ''} avaliação: no Dashboard (quadro “Campanhas novas para avaliar”)"
                             " ou no Painel das sócias.")
                else:
                    body += " Escolha quais são foco em Campanhas."
                port._notify(key.agency, "Campanhas novas lidas do Backstage", body, "/gestao/#campanhas-novas" if w else "/gestao/campanhas/")
    except campaigns.ReadingError as e:
        return _fail(422, str(e))
    except Exception:
        logger.exception("Porta de campanhas: erro ao gravar a leitura")
        return _fail(500, "Erro interno ao gravar a leitura de campanhas. Nada foi alterado.")
    return _json({"ok": True, "situacao": "gravado", "mensagem": "Leitura de campanhas gravada.", **counts}, 200)
