from ..base import Skill
from ._git import get_cwd, run_git, ensure_git_repo


class GitCommitSkill(Skill):
    name = "git_commit"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def run(self, args: dict) -> str:
        message = (args.get("message") or "").strip()
        if not message:
            return "Mensagem do commit é obrigatória."
        cwd = get_cwd(args)
        ok, msg = ensure_git_repo(cwd)
        if not ok:
            return msg
        if not self.execute:
            return f'(dry-run) Eu executaria: git commit -m "{message}"  (em {cwd})'
        # Passa como lista para evitar injeção de shell via caracteres especiais na mensagem
        ok, out = run_git(["git", "commit", "-m", message], cwd)
        if "nothing to commit" in (out or ""):
            return "Nada para commitar. Working tree limpa."
        return out if out else ("Commit realizado." if ok else "Falha no commit.")
