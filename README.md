# Committer

CLI tool to suggest a commit message with AI and apply `git commit` interactively.

## Stack

- Python 3
- OpenAI SDK
- Bash

## Requirements

- Python 3.10+
- Git
- OpenAI API key (`OPENAI_API_KEY`)

## Environment variables

The project automatically loads `.env` from the repository root.

Example:

```env
OPENAI_API_KEY=your-key-here
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick start (recommended)

Before running, stage the files you want to commit:

```bash
git add <files>
```

Use the `gcomm` script, which creates `.venv` (if it does not exist), installs dependencies on first run, activates the environment, and runs the CLI:

```bash
./gcomm
```

You can also pass options:

```bash
./gcomm --model gpt-4o-mini
```

## Manual usage

Before running, stage the files you want to commit:

```bash
git add <files>
```

Then run:

```bash
python committer.py
```

Available options:

```bash
python committer.py --model gpt-4o-mini --temperature 0.0
```

## How it works

1. Reads staged changes only using `git diff --staged`.
2. Loads prompts from `prompts/system.txt` and `prompts/user.txt`.
3. Generates a suggestion using OpenAI Chat Completions.
4. Prints the suggested message.
5. Asks in English whether the commit should be applied.
6. If confirmed, runs `git commit -m "<message>"`.

## Interactive prompt example

```text
Suggested commit message:
feat(cli): add interactive commit confirmation

Do you want to apply this message and run git commit for staged changes? [y/N]:
```

## Structure

- `committer.py`: main CLI
- `gcomm`: Bash wrapper for setup and execution
- `prompts/system.txt`: system instructions
- `prompts/user.txt`: user prompt template
- `requirements.txt`: Python dependencies
