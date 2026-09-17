"""Simple REPL entrypoint for AgentRAG.

Run with:
    python -m src.cli
"""

from src.agent import run_agent


def main():
    print("AgentRAG CLI — ask a question, or type 'exit' / 'quit' to leave.\n")

    while True:
        try:
            query = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye!")
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            print("bye!")
            break

        result = run_agent(query)

        print(f"\nagent> {result['answer']}\n")
        print(f"  (trace: {' | '.join(result['trace'])})")
        print(f"  (tool calls: {result['tool_calls_made']})\n")


if __name__ == "__main__":
    main()
