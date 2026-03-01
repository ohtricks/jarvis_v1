import sys
from .agent import JarvisAgent


def main():
    args = sys.argv[1:]

    execute = False
    if "--yes" in args or "-y" in args:
        execute = True
        args = [a for a in args if a not in ("--yes", "-y")]

    user_input = " ".join(args).strip()

    if not user_input:
        print("Usage: jarvis [--yes|-y] \"your command\"")
        return

    agent = JarvisAgent(execute=execute)
    response = agent.run(user_input)

    print(f"\nJarvis: {response}\n")


if __name__ == "__main__":
    main()