import subprocess
import shlex
from .base import Skill


# comandos permitidos (comece simples e expanda depois)
ALLOWED_PREFIXES = [
    "ls", "pwd", "whoami",
    "git", "python", "pip",
    "node", "npm", "pnpm", "yarn",
    "docker", "docker-compose",
    "php", "composer",
    "cat", "echo",
    "mkdir", "touch",
    "code",
]


BLOCKED_TOKENS = [
    " rm ", " rm-", " rm\t", " rm\n", " rm/",
    "sudo",
    "shutdown", "reboot",
    "mkfs", "dd ",
    "killall", "kill -9",
    ":(){",  # fork bomb
]


class RunShellSkill(Skill):
    name = "run_shell"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def _is_allowed(self, cmd: str) -> bool:
        c = f" {cmd.strip()} ".lower()

        # bloqueios óbvios
        for t in BLOCKED_TOKENS:
            if t in c:
                return False

        # allowlist por prefixo
        first = cmd.strip().split(" ")[0]
        return first in ALLOWED_PREFIXES

    def run(self, args: dict):
        command = args.get("command")
        cwd = args.get("cwd")  # opcional

        if not command:
            return "Nenhum comando informado."

        if not self._is_allowed(command):
            return (
                "Bloqueado por segurança. "
                "Esse comando não está na allowlist. "
                "Se você quiser, eu libero explicitamente depois."
            )

        if not self.execute:
            return f"(dry-run) Eu executaria:\n{command}"

        try:
            # executa com captura de saída
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()

            if result.returncode == 0:
                return out if out else "Comando executado com sucesso."
            else:
                msg = out if out else ""
                if err:
                    msg = (msg + "\n" + err).strip()
                return f"Erro (code {result.returncode}):\n{msg}" if msg else f"Erro (code {result.returncode})."

        except Exception as e:
            return f"Erro ao executar comando: {e}"