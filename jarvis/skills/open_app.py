import subprocess

def open_app(app_name: str):
    try:
        subprocess.run(["open", "-a", app_name])
        return f"{app_name} aberto com sucesso."
    except Exception as e:
        return f"Erro ao abrir {app_name}: {str(e)}"