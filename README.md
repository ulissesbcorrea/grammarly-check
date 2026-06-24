# grammarly-check

**grammarly-check** is a CLI tool that checks text for grammar, spelling, and
style issues by talking directly to the Grammarly API over WebSocket.  It
works without authentication (free tier) and supports premium accounts for
richer suggestions.

It is a clean-room reimplementation of the protocol documented by
[dexterleng/grammarly-api][dexterleng] and
[emacs-grammarly/grammarly][emacs-grammarly].

## Features

- Read text from stdin, a file, or inline arguments.
- Premium account authentication via environment variables.
- Two output formats: human-readable (default) and JSON.
- Ready-to-use pre-commit hook for LaTeX / Markdown projects.
- Lists every issue with category, impact, highlighted snippet, suggested
  replacement and explanation.

## Requirements

- Python ≥ 3.10
- `requests`
- `websocket-client`

```bash
pip install -r requirements.txt
```

## Quick start

```bash
# Basic usage (free tier)
echo "This sentence have a error." | python3 grammarly_check.py

# With premium credentials
export GRAMMARLY_EMAIL="your@email.com"
export GRAMMARLY_PASSWORD="your-password"
cat paper.tex | python3 grammarly_check.py

# JSON output (for programmatic consumption)
GRAMMARLY_FORMAT=json echo "... text ..." | python3 grammarly_check.py
```

### Inline text

```bash
python3 grammarly_check.py "The quick brown fox jump over the lazy dog."
```

### From a file

```bash
python3 grammarly_check.py < chapter.tex
```

## Pre-commit hook

Enable the bundled hook to check staged `.tex` / `.md` / `.txt` / `.rst`
files before every commit:

```bash
git config core.hooksPath .githooks
```

Or copy it manually:

```bash
cp examples/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Hook behaviour: it extracts all added lines from the staged diff, pipes them
through `grammarly_check.py`, and prints the report.  It **never blocks the
commit** — it is informative only.

## Output example

```
--- Alert #1 ---
  Title:       Subject-verb agreement error
  Category:    Faulty subject-verb agreement / Grammar
  Impact:      critical
  Highlight:   "are"
  Suggestions: am
  Explanation: It seems that the verb are does not agree with the subject.

--- Summary: 3 free, 0 premium ---
```

## Environment variables

| Variable            | Default   | Description                               |
|---------------------|-----------|-------------------------------------------|
| `GRAMMARLY_EMAIL`   | —         | Email for premium account (optional).     |
| `GRAMMARLY_PASSWORD`| —         | Password for premium account (optional).  |
| `GRAMMARLY_FORMAT`  | `pretty`  | Output format: `pretty` or `json`.        |

## How it works

1. **Cookie acquisition** — a GET request to `https://grammarly.com/`
   retrieves `gnar_containerId`, `grauth` and `csrf-token` cookies.
2. **Premium login (optional)** — a POST to
   `https://auth.grammarly.com/v3/api/login` authenticates the account.
3. **WebSocket connection** — opens `wss://capi.grammarly.com/freews` with
   the cookies as headers.
4. **Text submission** — sends an initialisation frame followed by a
   `submit_ot` frame containing the text.
5. **Alert collection** — the server replies with zero or more `alert`
   frames and a final `finished` frame.  Alerts are parsed and returned.

## Limitations

- The port number (`443`) must be omitted from the WebSocket URL when
  premium authentication is used; some network configurations may interfere.
- The dialect is hard-coded to `american` — Grammarly Premium subscribers
  can change this to `british`, `canadian`, `australian`, or the
  Portuguese-specific dialect (`brazilian`) if available.
- The API is **not official** and may break without notice.  Use at your
  own risk.

## Related projects

- [dexterleng/grammarly-api][dexterleng] — original JavaScript reference.
- [emacs-grammarly/grammarly][emacs-grammarly] — Emacs Lisp client.
- [znck/grammarly](https://github.com/znck/grammarly) — VS Code extension.

## License

MIT.

[dexterleng]: https://github.com/dexterleng/grammarly-api
[emacs-grammarly]: https://github.com/emacs-grammarly/grammarly
