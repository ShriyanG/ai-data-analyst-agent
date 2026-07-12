"""Simple evaluation harness for benchmark questions."""

import json
from pathlib import Path


def load_questions(path: str = "evaluation/test_questions.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    questions = load_questions()
    print(f"Loaded {len(questions)} benchmark questions from evaluation set.")
    for item in questions:
        print(f"- [{item['id']}] {item['question']}")


if __name__ == "__main__":
    main()
