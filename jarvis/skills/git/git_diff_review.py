"""
git_diff_review.py — Skill de revisão técnica de git diff.

Retorna um payload estruturado com:
  - resumo (arquivos, adições, remoções)
  - seções por arquivo (diff content)
  - insights heurísticos
  - ações sugeridas

O payload é embutido na string de resposta via modal_payload.embed_modal().
O server.py extrai o JSON e popula RunResponse.modal_payload para a UI.
"""
from __future__ import annotations

from ..base import Skill
from ._git import get_cwd, run_git, ensure_git_repo
from ._diff_parser import parse_numstat, parse_diff_sections, merge_file_stats
from ._diff_insights import compute_insights, risk_level_for_files
from ...modal_payload import embed_modal

# ── Limites de truncamento ─────────────────────────────────────────────────────
_MAX_DIFF_CHARS = 8_000   # diff raw total antes de truncar
_MAX_FILES_SHOWN = 20      # máx de arquivos no payload
_MAX_PER_FILE_CHARS = 2_000  # diff por arquivo no payload


class GitDiffReviewSkill(Skill):
    name = "git_diff_review"

    def run(self, args: dict) -> str:
        cwd = get_cwd(args)

        ok, err_msg = ensure_git_repo(cwd)
        if not ok:
            return err_msg

        # ── 1. Coletar numstat (staged + unstaged) ─────────────────────────────
        _, unstaged_numstat = run_git("git diff --numstat", cwd)
        _, staged_numstat = run_git("git diff --cached --numstat", cwd)

        file_stats = merge_file_stats(
            parse_numstat(unstaged_numstat or ""),
            parse_numstat(staged_numstat or ""),
        )

        if not file_stats:
            return "Não há alterações no repositório. Working tree e stage estão limpos."

        total_files = len(file_stats)
        total_adds = sum(f["additions"] for f in file_stats)
        total_dels = sum(f["deletions"] for f in file_stats)

        # ── 2. Diff raw (combinado staged + unstaged) ──────────────────────────
        _, raw_unstaged = run_git("git diff", cwd)
        _, raw_staged = run_git("git diff --cached", cwd)
        raw_diff = "\n".join(filter(None, [raw_unstaged, raw_staged])).strip()

        truncated = len(raw_diff) > _MAX_DIFF_CHARS
        diff_for_parsing = raw_diff[:_MAX_DIFF_CHARS] if truncated else raw_diff

        # ── 3. Diff sections por arquivo ───────────────────────────────────────
        diff_sections = parse_diff_sections(diff_for_parsing)

        # ── 4. Insights heurísticos ────────────────────────────────────────────
        risk = risk_level_for_files([f["file"] for f in file_stats])
        insights = compute_insights(file_stats, diff_sections)

        # ── 5. Montar payload ──────────────────────────────────────────────────
        shown_stats = file_stats[:_MAX_FILES_SHOWN]
        shown_diff = diff_sections[:_MAX_FILES_SHOWN]

        files_payload = [
            {
                "file": f["file"],
                "additions": f["additions"],
                "deletions": f["deletions"],
                "status": _infer_status(f),
            }
            for f in shown_stats
        ]

        diff_payload = [
            {
                "file": s["file"],
                "content": s["content"][:_MAX_PER_FILE_CHARS],
                "truncated": len(s["content"]) > _MAX_PER_FILE_CHARS,
            }
            for s in shown_diff
        ]

        n = total_files
        noun = "arquivo alterado" if n == 1 else "arquivos alterados"
        summary = f"{n} {noun} (+{total_adds} / -{total_dels})"

        modal = {
            "ui_hint": "modal",
            "modal_type": "git_diff_review",
            "payload": {
                "title": "Git Diff Review",
                "summary": summary,
                "meta": {
                    "files_changed": total_files,
                    "additions": total_adds,
                    "deletions": total_dels,
                    "risk_level": risk,
                    "truncated": truncated,
                    "total_files": total_files,
                    "shown_files": len(shown_stats),
                    # raw_diff_excerpt só presente quando truncado (para evitar payload gigante)
                    **({"raw_diff_excerpt": raw_diff[:2000]} if truncated else {}),
                },
                "sections": {
                    "files": files_payload,
                    "diff": diff_payload,
                    "insights": insights,
                },
                "actions": _build_actions(total_files, risk),
            },
        }

        human = f"Senhor, analisei o diff atual. {summary}."
        return embed_modal(human, modal)


# ── Helpers privados ───────────────────────────────────────────────────────────

def _infer_status(file_stat: dict) -> str:
    """Infere status do arquivo pela contagem de linhas."""
    adds = file_stat["additions"]
    dels = file_stat["deletions"]
    if dels == 0:
        return "added"
    if adds == 0:
        return "deleted"
    return "modified"


def _build_actions(files_changed: int, risk_level: str) -> list[dict]:
    """Constrói lista de ações disponíveis no modal."""
    return [
        {
            "id": "validate_diff",
            "label": "Validar diff",
            "description": "Jarvis revisa o diff em busca de problemas óbvios.",
            "command": "valide o diff atual do projeto",
            "enabled": True,
        },
        {
            "id": "suggest_improvements_from_diff",
            "label": "Sugerir melhorias",
            "description": "Jarvis sugere melhorias baseadas no que foi alterado.",
            "command": "sugira melhorias para as alterações do diff atual",
            "enabled": True,
        },
        {
            "id": "generate_patch_from_diff",
            "label": "Gerar patch",
            "description": "Exporta o diff como arquivo .patch.",
            "command": "gere um patch das alterações atuais",
            "enabled": True,
        },
        {
            "id": "stage_and_commit",
            "label": "Stage + Commit",
            "description": "Adiciona tudo e cria um commit (requer confirmação).",
            "command": "faça git add all e commit das alterações atuais",
            "enabled": True,
            "risk": "risky",
        },
    ]
