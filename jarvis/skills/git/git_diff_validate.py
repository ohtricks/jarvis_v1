"""
git_diff_validate — analisa o diff atual com LLM e retorna sugestões estruturadas.
"""
import subprocess
from ..base import Skill
from ._git import get_cwd, ensure_git_repo
from ...llm import ask_llm

_MAX_DIFF_CHARS = 6000

_SYSTEM = (
    "Você é um revisor de código especialista. "
    "Analise o git diff fornecido e identifique:\n"
    "- Bugs ou erros de lógica\n"
    "- Problemas de segurança (injeção, exposição de credenciais, etc.)\n"
    "- Código morto ou redundante\n"
    "- Melhorias de qualidade ou legibilidade\n\n"
    "Responda em português brasileiro, de forma direta e técnica. "
    "Use marcadores de lista. Seja específico (mencione arquivo e linha quando possível)."
)

_PROMPT_TPL = (
    "Revise o seguinte git diff e forneça feedback:\n\n"
    "```diff\n{diff}\n```"
)


class GitDiffValidateSkill(Skill):
    name = "git_diff_validate"

    def run(self, args: dict) -> str:
        cwd = get_cwd(args)
        ok, msg = ensure_git_repo(cwd)
        if not ok:
            return msg

        try:
            diff = subprocess.check_output(
                ["git", "diff", "HEAD"],
                cwd=cwd, text=True, stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            return f"Erro ao obter diff: {e.output or e}"

        if not diff.strip():
            # tenta staged
            try:
                diff = subprocess.check_output(
                    ["git", "diff", "--cached"],
                    cwd=cwd, text=True, stderr=subprocess.STDOUT,
                )
            except subprocess.CalledProcessError as e:
                return f"Erro ao obter staged diff: {e.output or e}"

        if not diff.strip():
            return "Nenhuma alteração encontrada para validar."

        truncated = False
        if len(diff) > _MAX_DIFF_CHARS:
            diff = diff[:_MAX_DIFF_CHARS]
            truncated = True

        prompt = _PROMPT_TPL.format(diff=diff)
        try:
            analysis = ask_llm(
                messages=[
                    {"role": "system",  "content": _SYSTEM},
                    {"role": "user",    "content": prompt},
                ],
                model="brain",
                temperature=0.2,
                max_tokens=1200,
                role="git_diff_validate",
            )
        except Exception as e:
            return f"Erro na análise LLM: {e}"

        note = "\n\n_(diff truncado para análise)_" if truncated else ""
        return f"**Análise do diff:**\n\n{analysis}{note}"
