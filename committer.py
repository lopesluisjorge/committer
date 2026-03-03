#!/usr/bin/env python3
"""CLI to suggest commit messages based on local changes."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
SYSTEM_PROMPT_FILE = PROMPTS_DIR / "system.txt"
USER_PROMPT_FILE = PROMPTS_DIR / "user.txt"


def run_git_command(args: list[str]) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or "Unknown error while running git."
        raise RuntimeError(stderr) from exc
    return result.stdout


def run_git_command_stream(args: list[str]) -> None:
    """Run a git command streaming stdout/stderr to the terminal."""
    try:
        subprocess.run(["git", *args], check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git {' '.join(args)} failed with exit code {exc.returncode}") from exc


def get_diff() -> str:
    """Return staged-only diff or full diff (staged + unstaged)."""
    return run_git_command(["diff", "--staged"])


def load_prompt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Could not read prompt file at {path}: {exc}") from exc


def build_prompt(diff: str) -> tuple[str, str]:
    system = load_prompt(SYSTEM_PROMPT_FILE)
    user_template = load_prompt(USER_PROMPT_FILE)
    if "{diff}" not in user_template:
        raise RuntimeError("User prompt must contain the {diff} placeholder.")
    user = user_template.format(diff=diff[:14000])
    return system, user


def suggest_with_llm(diff: str, model: str, temperature: float) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI SDK is not installed. Run: pip install -r requirements.txt"
        ) from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY was not found in the environment.")

    system_content, user_content = build_prompt(diff)
    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI request failed: {exc}") from exc

    suggestion = ""
    if response.choices:
        suggestion = (response.choices[0].message.content or "").strip()
    if not suggestion:
        raise RuntimeError("The model did not return a suggestion.")
    return suggestion


def fallback_suggestion(diff: str) -> str:
    """Simple heuristic fallback when LLM is unavailable."""
    lower = diff.lower()
    if "readme" in lower or "docs/" in lower:
        return "docs: update documentation"
    if "test" in lower:
        return "test: improve test coverage"
    if "requirements" in lower or "poetry.lock" in lower or "package-lock" in lower:
        return "chore: update dependencies"
    if "fix" in lower or "bug" in lower:
        return "fix: correct behavior"
    return "chore: update code"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="committer",
        description="Suggest a commit message based on git diff.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model used by the SDK (default: gpt-4o-mini).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Model temperature (default: 0.0).",
    )
    return parser.parse_args()


def ask_to_apply_commit(suggestion: str) -> bool:
    print(f"Suggested commit message:\n{suggestion}\n")
    prompt = "Do you want to apply this message and run git commit for staged changes? [y/N]: "
    answer = input(prompt).strip().lower()
    return answer in {"y", "yes"}


def apply_commit(suggestion: str) -> None:
    run_git_command_stream(["commit", "-m", suggestion])


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    args = parse_args()

    try:
        diff = get_diff()
    except RuntimeError as exc:
        print(f"Error reading diff: {exc}", file=sys.stderr)
        return 1

    if not diff.strip():
        print("No changes found to suggest a commit message.", file=sys.stderr)
        return 1

    try:
        suggestion = suggest_with_llm(
            diff=diff, model=args.model, temperature=args.temperature
        )
    except RuntimeError as exc:
        if args.no_fallback:
            print(f"Failed to generate suggestion with LLM: {exc}", file=sys.stderr)
            return 1
        suggestion = fallback_suggestion(diff)

    if not ask_to_apply_commit(suggestion=suggestion):
        print("Commit canceled by user.")
        return 0

    try:
        apply_commit(suggestion=suggestion)
    except RuntimeError as exc:
        print(f"Failed to commit changes: {exc}", file=sys.stderr)
        return 1

    print("Commit created successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
