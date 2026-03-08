"""
git_generate_patch — exporta o diff atual como arquivo .patch.
"""
import subprocess
import time
from pathlib import Path
from ..base import Skill
from ._git import get_cwd, ensure_git_repo


class GitGeneratePatchSkill(Skill):
    name = "git_generate_patch"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def run(self, args: dict) -> str:
        cwd = get_cwd(args)
        ok, msg = ensure_git_repo(cwd)
        if not ok:
            return msg

        timestamp = int(time.time())
        patch_path = Path.home() / ".jarvis" / f"patch_{timestamp}.patch"

        if not self.execute:
            return f"(dry-run) Eu exportaria o diff para {patch_path}."

        try:
            diff = subprocess.check_output(
                ["git", "diff", "HEAD"],
                cwd=cwd, text=True, stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            return f"Erro ao gerar diff: {e.output or e}"

        if not diff.strip():
            try:
                diff = subprocess.check_output(
                    ["git", "diff", "--cached"],
                    cwd=cwd, text=True, stderr=subprocess.STDOUT,
                )
            except subprocess.CalledProcessError as e:
                return f"Erro ao gerar staged diff: {e.output or e}"

        if not diff.strip():
            return "Nenhuma alteração para exportar como patch."

        patch_path.parent.mkdir(parents=True, exist_ok=True)
        patch_path.write_text(diff, encoding="utf-8")

        lines = diff.count("\n")
        size_kb = round(len(diff.encode()) / 1024, 1)
        return (
            f"Patch exportado para `{patch_path}`\n"
            f"Tamanho: {size_kb} KB · {lines} linhas"
        )
