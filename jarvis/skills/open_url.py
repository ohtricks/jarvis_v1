import subprocess
from .base import Skill


class OpenUrlSkill(Skill):
    name = "open_url"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def run(self, args: dict):
        url = (args.get("url") or "").strip()
        browser = (args.get("browser") or "").strip()  # opcional (ex: "Google Chrome")

        if not url:
            return "Nenhuma URL informada."

        # se o usuário não colocou http/https, adiciona https
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        if not self.execute:
            if browser:
                return f"(dry-run) Eu abriria:\n{url}\nno navegador:\n{browser}"
            return f"(dry-run) Eu abriria:\n{url}"

        try:
            if browser:
                subprocess.run(
                    ["open", "-a", browser, url],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                return f"Abrindo {url} no {browser}."
            else:
                subprocess.run(
                    ["open", url],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                return f"Abrindo {url}."
        except Exception as e:
            return f"Erro ao abrir URL: {e}"