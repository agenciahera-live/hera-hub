"""Verificador de tom: palavras que não aparecem nas telas do criador.

Regras da visão de 11/11/2026 (ver CLAUDE.md, "Regras da visão"):
- sem meta, relatório, cobrança, prazo, horário e ranking;
- linguagem neutra de gênero (nada de "sua gestora", "obrigada", "juntas", "bem-vinda").

A mesma lista será usada pela biblioteca de mensagens.
"""
import re

VETADAS = {
    "meta": r"metas?",
    "relatório": r"relat[óo]rios?",
    "cobrança": r"cobran[çc]as?",
    "prazo": r"prazos?",
    "horário": r"hor[áa]rios?",
    "ranking": r"rankings?",
    "gestora (use \"a Hera\")": r"gestoras?",
    "obrigada/obrigado (use \"valeu\")": r"obrigad[ao]s?",
    "juntas/juntos": r"junt[ao]s",
    "bem-vinda/bem-vindo (use \"boas-vindas\")": r"bem[- ]vind[ao]s?",
}

_PADROES = {nome: re.compile(rf"(?<![\w-]){p}(?![\w-])", re.IGNORECASE) for nome, p in VETADAS.items()}


def verificar_tom(texto):
    """Devolve a lista de problemas encontrados no texto (vazia = texto aprovado)."""
    texto = texto or ""
    return [nome for nome, padrao in _PADROES.items() if padrao.search(texto)]


# ------------------------------------------------------------------ mensagens da gestão (biblioteca de mensagens)
# Regra da visão para as mensagens: barrar meta, cobrança, prazo, horário e texto só no feminino.
# A lista é menor que a das telas: quem fala na mensagem é a gestora ("obrigada por avisar" é ela falando de si).
VETADAS_MENSAGEM = {
    "meta": r"metas?",
    "cobrança": r"cobran[çc]as?",
    "prazo": r"prazos?",
    "horário": r"hor[áa]rios?",
}
# "horário de Brasília" é fuso, não horário pedido pela Hera.
_PERMITIDOS = re.compile(r"hor[áa]rio de bras[íi]lia", re.IGNORECASE)
_PADROES_MSG = {nome: re.compile(rf"(?<![\w-]){p}(?![\w-])", re.IGNORECASE) for nome, p in VETADAS_MENSAGEM.items()}

# Texto só no feminino: palavra no feminino dirigida ao criador, sem a forma neutra "(o)" ou "(a)" ao lado.
# É uma lista de palavras conhecidas, não uma análise da frase: pega os casos que já apareceram nos roteiros da Hera.
_FEM = r"bem[- ]vinda|agenciada|pronta|preparada|encaminhada|focada|sozinha|insegura|tranquila|animada|cansada|inscrita|classificada|graduada|premiada"
_FEMININO = [
    re.compile(r"(?<![\w-])bem[- ]vindas?(?![\w(-])", re.IGNORECASE),
    re.compile(r"(?<![\w-])você mesma(?![\w(-])", re.IGNORECASE),
    # "você está pronta", "tá super encaminhada", "ficou insegura", "vira agenciada"...
    re.compile(rf"(?<![\w-])(?:você|seja|está|tá|estar|ficou|fica|ficar|vira|virar)(?:\s+(?:já|super|bem|muito|mais|tão))*\s+(?:{_FEM})s?(?![\w(-])", re.IGNORECASE),
]


def verificar_tom_mensagem(texto):
    """Problemas de tom em uma mensagem da gestão ao criador (lista vazia = aprovada)."""
    texto = _PERMITIDOS.sub(" ", texto or "")
    achados = [nome for nome, padrao in _PADROES_MSG.items() if padrao.search(texto)]
    if any(p.search(texto) for p in _FEMININO):
        achados.append("texto só no feminino (use a forma neutra, como “pronto(a)”)")
    return achados
