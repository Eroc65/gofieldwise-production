"""CLI entry point for the startup operations platform.

Usage
-----
    # Interactive chat (REPL)
    python -m autogpt.main

    # Single-shot command
    python -m autogpt.main --message "Build me a Flask app called myapp and deploy it."

    # With verbose logging
    python -m autogpt.main --verbose
"""

from __future__ import annotations

import argparse
import sys

from autogpt.config import Config
from autogpt.orchestrator import Orchestrator
from autogpt.utils.logger import get_logger


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="autogpt",
        description="AI-powered startup operations platform (Polsia-like).",
    )
    parser.add_argument(
        "--message",
        "-m",
        type=str,
        default=None,
        help="Single message to send to the orchestrator (non-interactive mode).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose/debug logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    args = _parse_args(argv)

    config = Config()
    if args.verbose:
        config.verbose = True

    log = get_logger("autogpt.main", config.verbose)

    try:
        config.validate()
    except ValueError as exc:
        log.error("Configuration error: %s", exc)
        sys.exit(1)

    orchestrator = Orchestrator(config)

    if args.message:
        # Single-shot mode
        reply = orchestrator.chat(args.message)
        print(reply)
        return

    # Interactive REPL mode
    print("🚀  Auto-GPT Startup Operations Platform")
    print("   Type your message, or 'quit' / 'exit' to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        reply = orchestrator.chat(user_input)
        print(f"\nAssistant: {reply}\n")


if __name__ == "__main__":
    main()
