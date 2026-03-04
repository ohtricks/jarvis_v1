from ..base import Skill
from ._git import get_cwd, run_git, ensure_git_repo


class GitStatusSkill(Skill):
    name = "git_status"

    def run(self, args: dict) -> str:
        cwd = get_cwd(args)
        ok, msg = ensure_git_repo(cwd)
        if not ok:
            return msg
        ok, out = run_git("git status", cwd)
        return out if out else "git status sem output."
