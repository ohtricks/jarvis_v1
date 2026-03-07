"""
voice_tools.py — Define as ferramentas (FunctionDeclarations) expostas ao Gemini Live.

Estratégia: uma única ferramenta `ask_jarvis(command: str)` que roteia tudo pelo
pipeline completo do Jarvis (router → planner/executor → risk gate → skills → memory).
Isso preserva toda a lógica existente sem duplicação.
"""
from __future__ import annotations

from google.genai import types


def build_voice_tools() -> list[types.Tool]:
    """Retorna a lista de tools para passar ao Gemini Live API."""
    ask_jarvis = types.FunctionDeclaration(
        name="ask_jarvis",
        description=(
            "Executa qualquer comando no Jarvis — abre apps, navega na web, "
            "roda git, lê emails, executa scripts, etc. "
            "Passe o comando em linguagem natural em português. "
            "Se a ação exigir confirmação (git push, envio de email, etc.) "
            "o Jarvis retornará uma mensagem pedindo confirmação — "
            "nesse caso, informe o usuário e aguarde a resposta dele antes de confirmar."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "command": types.Schema(
                    type="STRING",
                    description="Comando em linguagem natural para o Jarvis executar.",
                )
            },
            required=["command"],
        ),
    )
    return [types.Tool(function_declarations=[ask_jarvis])]
