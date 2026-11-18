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
