"""Run the three required demonstration questions."""
from hydropinpoint.agent.graph import ask

QUESTIONS = (
    "Which wards need pumps tomorrow?",
    "Which hospitals are near the top 3 hotspots, and what is the route from the nearest shelter?",
    "What happens at 40 mm/h?",
)


def main() -> None:
    for question in QUESTIONS:
        result = ask(question)
        print(f"QUESTION: {question}")
        print(f"ANSWER: {result['answer']}")
        print(f"TRACE: status={result['status']} attempts={result['attempts']}")
        print(f"NUMBER SOURCES: {result['citations']}")


if __name__ == "__main__":
    main()

