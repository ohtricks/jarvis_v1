# jarvis/main.py
import os
import sys
from .agent import JarvisAgent


def main():
    args = sys.argv[1:]

    execute = False

    # flags
    if "--execute" in args or "-x" in args:
        execute = True
        args = [a for a in args if a not in ("--execute", "-x")]

    # alias antigo (pra não quebrar)
    if "--yes" in args or "-y" in args:
        execute = True
        args = [a for a in args if a not in ("--yes", "-y")]

    # env var (bom pra UI futura)
    if os.getenv("JARVIS_EXECUTE", "0") == "1":
        execute = True

    user_input = " ".join(args).strip()

    if not user_input:
        print('Usage: jarvis [--execute|-x] "your command"')
        print('   or: jarvis [--yes|-y] "your command"  (alias)')
        return 1

    agent = JarvisAgent(execute=execute)
    response = agent.run(user_input)

    print(f"\nJarvis: {response}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())