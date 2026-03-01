import subprocess
from .base import Skill

class OpenAppSkill(Skill):
    name = "open_app"

    def run(self, args: dict):
        app = args.get("app")
        if not app:
            return "Nenhum app informado."

        subprocess.run(["open", "-a", app])
        return f"{app} aberto."