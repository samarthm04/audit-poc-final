"""CLI smoke-test: call ask_llm and print the result."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from agents.llm_agent import ask_llm  # noqa: E402


def main() -> None:
    """Send a sample audit prompt and print the LLM response."""
    prompt = "Explain access control review in IT auditing."
    print("Sending prompt to LLM…\n")
    response = ask_llm(prompt)
    print(response)


if __name__ == "__main__":
    main()
