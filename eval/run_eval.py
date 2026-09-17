"""Runs eval/test_questions.jsonl through the agent and logs which route the planner chose.

Run with:
    python -m eval.run_eval
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import run_agent

QUESTIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_questions.jsonl")


def extract_planner_route(trace: list) -> str:
    for entry in trace:
        if entry.startswith("planner -> "):
            return entry.split("planner -> ", 1)[1]
    return "unknown"


def main():
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    correct = 0
    print(f"Running {len(cases)} eval questions...\n")

    for i, case in enumerate(cases, start=1):
        question = case["question"]
        expected = case["expected_route"]

        result = run_agent(question)
        actual = extract_planner_route(result["trace"])
        match = actual == expected
        correct += int(match)

        status = "PASS" if match else "FAIL"
        print(f"[{i}] {status}  expected={expected!r} actual={actual!r}")
        print(f"    q: {question}")
        print(f"    a: {result['answer'][:150]}")
        print()

    print(f"Routing accuracy: {correct}/{len(cases)}")


if __name__ == "__main__":
    main()
