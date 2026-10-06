"""List the models available through the Gemini OpenAI-compatible endpoint.

Usage:
    uv run python scripts/list_models.py            # all models
    uv run python scripts/list_models.py flash-lite # filter by substring
"""

import os
import sys

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI

from spec_check.llm import GEMINI_BASE_URL


def main() -> int:
    load_dotenv(find_dotenv(usecwd=True))
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set (put it in .env)", file=sys.stderr)
        return 1

    needle = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    client = OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)
    names = sorted(m.id.removeprefix("models/") for m in client.models.list())
    for name in names:
        if needle in name.lower():
            print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
