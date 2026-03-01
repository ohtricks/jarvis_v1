import sys
from .agent import JarvisAgent

def main():
    agent = JarvisAgent()

    user_input = " ".join(sys.argv[1:])

    if not user_input:
        print("Usage: jarvis 'your command'")
        return

    response = agent.run(user_input)

    print(f"\nJarvis: {response}\n")


if __name__ == "__main__":
    main()