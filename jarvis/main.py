# jarvis/main.py
import sys
from .agent import JarvisAgent
from .modal_payload import extract_modal


def main():
    args = sys.argv[1:]

    execute = False

    # aliases
    if "--execute" in args or "-x" in args or "--yes" in args or "-y" in args:
        execute = True
        args = [a for a in args if a not in ("--execute", "-x", "--yes", "-y")]

    # força dry mesmo se tiver session mode execute
    if "--dry" in args or "--dry-run" in args:
        execute = False
        args = [a for a in args if a not in ("--dry", "--dry-run")]

    user_input = " ".join(args).strip()

    if not user_input:
        print('Usage: jarvis [--execute|-x|--yes|-y|--dry] "your command"')
        return

    agent = JarvisAgent(execute=execute)
    response = agent.run(user_input)

    clean, modal = extract_modal(response)
    print(f"\nJarvis: {clean}\n")
    if modal:
        meta = modal.get("payload", {}).get("meta", {})
        print(
            f"[Modal {modal.get('modal_type', 'modal')}: "
            f"{modal.get('payload', {}).get('summary', '')} | "
            f"risco: {meta.get('risk_level', '?')}]\n"
        )


if __name__ == "__main__":
    main()