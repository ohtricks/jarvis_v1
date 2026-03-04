from ..base import Skill
from ._git import get_cwd, run_git, ensure_git_repo


class GitPushSkill(Skill):
    name = "git_push"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def run(self, args: dict) -> str:
        cwd = get_cwd(args)
        ok, msg = ensure_git_repo(cwd)
        if not ok:
            return msg
        remote = (args.get("remote") or "origin").strip()
        branch = (args.get("branch") or "").strip()
        if not branch:
            ok_b, branch = run_git("git branch --show-current", cwd)
            if not ok_b:
                branch = ""
        cmd = f"git push {remote} {branch}".strip() if branch else f"git push {remote}"
        if not self.execute:
            return f"(dry-run) Eu executaria: {cmd}  (em {cwd})"
        ok, out = run_git(cmd, cwd)
        return out if out else ("Push realizado." if ok else "Falha no push.")
