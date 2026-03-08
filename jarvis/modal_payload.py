"""
modal_payload.py — Mecanismo de payload estruturado para a UI do Jarvis.

COMO FUNCIONA
─────────────
Skills que retornam dados estruturados (modais, revisões, dashboards) embedam
um JSON especial na string de resposta usando o sentinel __JARVIS_MODAL__.

    "Texto humano da resposta\n__JARVIS_MODAL__{"ui_hint":"modal",...}"

O server.py detecta o sentinel, extrai o JSON e popula modal_payload no RunResponse.
O CLI (main.py) exibe apenas a parte humana, ignorando o JSON.

CONTRATOS DE MODAL SUPORTADOS
──────────────────────────────
modal_type: "git_diff_review"
    payload.title          str
    payload.summary        str       descrição curta legível
    payload.meta           dict      files_changed, additions, deletions, risk_level, truncated
    payload.sections       dict
        .files             list[FileEntry]   {file, additions, deletions, status}
        .diff              list[DiffSection] {file, content, truncated}
        .insights          list[Insight]     {level, message}
    payload.actions        list[Action]      {id, label, description, command, enabled}

EXTENSÃO FUTURA
───────────────
Para criar um novo tipo de modal, adicione uma entrada em MODAL_TYPES e implemente
o builder correspondente. O contrato RunResponse já suporta modal_payload: dict.
"""
from __future__ import annotations

import json
from typing import Any

# Sentinela embutida na string de resposta da skill
MODAL_SENTINEL = "__JARVIS_MODAL__"

# Tipos de modal suportados — documentação apenas (não validado em runtime)
MODAL_TYPES = {
    "git_diff_review": "Revisão de git diff com arquivos, insights e ações",
    # Futuros:
    # "build_error_review": "Log de build com erros e sugestões de fix",
    # "execution_plan":     "Plano multi-step com riscos e aprovação",
    # "code_review":        "Review de código com problemas e melhorias",
    # "log_viewer":         "Log de execução com filtros e highlights",
}


def embed_modal(human_message: str, payload: dict[str, Any]) -> str:
    """
    Retorna string de skill com payload de modal embutido.

    Uso:
        return embed_modal("Analisei o diff. 3 arquivos alterados.", modal_dict)
    """
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"{human_message.strip()}\n{MODAL_SENTINEL}{serialized}"


def extract_modal(response: str) -> tuple[str, dict[str, Any] | None]:
    """
    Extrai modal payload de uma string de resposta do agente.

    Retorna (response_limpa, modal_dict | None).
    A response_limpa é adequada para exibição no chat/CLI.

    Usa raw_decode para tolerar texto extra após o JSON (e.g. mensagens
    do executor encadeadas depois do output da skill).
    """
    if MODAL_SENTINEL not in response:
        return response, None

    before, _, raw = response.partition(MODAL_SENTINEL)
    raw = raw.strip()
    try:
        decoder = json.JSONDecoder()
        modal, _ = decoder.raw_decode(raw)
    except (json.JSONDecodeError, ValueError):
        # JSON corrompido: devolve a resposta original sem modificação
        return response, None

    return before.strip(), modal
