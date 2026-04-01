"""CLI entry point for the startup operations platform.

Usage
-----
    # Interactive chat (REPL)
    python -m autogpt.main

    # Single-shot command
    python -m autogpt.main --message "Build me a Flask app called myapp and deploy it."

    # Launch the web chat UI
    python -m autogpt.main --web

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
        "--web",
        "-w",
        action="store_true",
        help="Launch the FastAPI web chat UI instead of the CLI.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the web server to (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for the web server (default: WEB_PORT env var or 8000).",
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

    # ------------------------------------------------------------------ #
    # Web UI mode
    # ------------------------------------------------------------------ #
    if args.web:
        try:
            import uvicorn
        except ImportError:
            log.error(
                "uvicorn is not installed. "
                "Run `pip install fastapi uvicorn[standard]` to enable the web UI."
            )
            sys.exit(1)

        from autogpt.web.app import create_app

        app = create_app(config)
        port = args.port or config.web_port
        log.info("Starting web UI on http://%s:%d", args.host, port)
        uvicorn.run(app, host=args.host, port=port)
        return

    # ------------------------------------------------------------------ #
    # CLI / REPL mode
    # ------------------------------------------------------------------ #
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

