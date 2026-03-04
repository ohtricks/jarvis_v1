from ..base import Skill
from ._git import get_cwd, run_git, ensure_git_repo


class GitAddAllSkill(Skill):
    name = "git_add_all"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def run(self, args: dict) -> str:
        cwd = get_cwd(args)
        ok, msg = ensure_git_repo(cwd)
        if not ok:
            return msg
        if not self.execute:
            return f"(dry-run) Eu executaria: git add -A  (em {cwd})"
        ok, out = run_git("git add -A", cwd)
        return ("Stage atualizado.\n" + out).strip() if out else "Stage atualizado."
