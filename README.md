# Committer

CLI tool to suggest a commit message with AI and apply `git commit` interactively.

## Stack

- Bash
- OpenAI API (via `curl` + `jq`)

## Requirements

- Bash
- `curl` and `jq`
- Git
- OpenAI API key (`OPENAI_API_KEY`)

## Environment variables

The tool automatically loads `.env` from the current directory if present.

Example:

```env
OPENAI_API_KEY=your-key-here
```

## Installation

Clone the repository and make the scripts executable:

```bash
chmod +x gcomm committer.sh
```

To run `gcomm` from anywhere, create a symlink in a directory on your `PATH`:

```bash
ln -s /path/to/repo/gcomm ~/.local/bin/gcomm
```

Both scripts resolve symlinks at runtime, so the prompts and configuration are always loaded from the real repository location.

## Quick start

Stage the files you want to commit, then run:

```bash
git add <files>
gcomm
```

You can also pass options:

```bash
gcomm --model gpt-4o-mini --temperature 0.0
```

## How it works

1. Reads staged changes using `git diff --staged`.
2. Loads prompts from `prompts/system.txt` and `prompts/user.txt`.
3. Generates a suggestion using the OpenAI Chat Completions API.
4. Prints the suggested message.
5. Asks whether the commit should be applied.
6. If confirmed, runs `git commit -F -` with the suggested message.

## Interactive prompt example

```text
Suggested commit message:
feat(cli): add interactive commit confirmation

Do you want to apply this message and run git commit for staged changes? [y/N]:
```

## Options

| Option          | Default       | Description             |
|-----------------|---------------|-------------------------|
| `--model`       | `gpt-4o-mini` | OpenAI model to use     |
| `--temperature` | `0.0`         | Model temperature       |

## Structure

- `gcomm`: entry point (resolves symlinks, delegates to `committer.sh`)
- `committer.sh`: main CLI logic
- `prompts/system.txt`: system instructions
- `prompts/user.txt`: user prompt template
