import subprocess
from .base import Skill

class OpenUrlSkill(Skill):
    name = "open_url"

    def run(self, args: dict):
        url = args.get("url")
        browser = args.get("browser")  # opcional (ex: "Google Chrome")

        if not url:
            return "Nenhuma URL informada."

        # se o usuário não colocou http/https, adiciona https
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        if browser:
            subprocess.run(["open", "-a", browser, url])
            return f"Abrindo {url} no {browser}."
        else:
            subprocess.run(["open", url])
            return f"Abrindo {url}."