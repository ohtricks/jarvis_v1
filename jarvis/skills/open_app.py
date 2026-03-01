import subprocess
from .base import Skill

APP_ALIASES = {
    # browsers
    "safari": "Safari",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "firefox": "Firefox",

    # dev
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",

    # db
    "workbench": "MySQLWorkbench",
    "mysql workbench": "MySQLWorkbench",

    # communication
    "slack": "Slack",
    "discord": "Discord",
    "whatsapp": "WhatsApp",
}

def normalize_app_name(name: str) -> str:
    if not name:
        return name
    key = name.strip().lower()
    return APP_ALIASES.get(key, name.strip())

class OpenAppSkill(Skill):
    name = "open_app"

    def run(self, args: dict):
        app_raw = args.get("app")
        app = normalize_app_name(app_raw)

        if not app:
            return "Nenhum app informado."

        subprocess.run(["open", "-a", app])
        return f"{app} aberto."