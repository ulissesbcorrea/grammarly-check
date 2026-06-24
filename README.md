# grammarly-check

**grammarly-check** checks text for grammar, spelling, and style issues using
either [**LanguageTool**][languagetool] (recommended) or the Grammarly API.

**LanguageTool** is the default backend — it supports Portuguese (Brazil)
natively, works with a free public API, and needs no authentication.
The Grammarly backend is kept for English-only use cases.

```
┌─────────────────────────────────────────────────────────┐
│  languagetool_check.py   ← default, Portuguese + more   │
│  grammarly_check.py      ← Grammarly API (English only) │
└─────────────────────────────────────────────────────────┘
```

## Features

- Check Portuguese (**pt-BR**), English, and 25+ other languages.
- **Strip LaTeX** markup automatically (`--detex`).
- Read text from stdin, file (`--file`), or inline arguments.
- Two output formats: human-readable (colored) and JSON (`--json`).
- Ready-to-use pre-commit hook for LaTeX / Markdown projects.
- Splits long texts into chunks to stay within API limits.

## Quick start

```bash
# Check a LaTeX file (auto-detects Portuguese)
python3 languagetool_check.py --detex --file paper.tex

# Inline text
echo "Este texto têm erros de gramatica." | python3 languagetool_check.py

# Explicit language
python3 languagetool_check.py --language pt-BR < artigo.tex

# JSON output
python3 languagetool_check.py --json < text.txt
```

## Requirements

```bash
pip install requests
```

## Pre-commit hook

Check staged files before every commit (informative only — never blocks):

```bash
git config core.hooksPath .githooks
```

## Strip LaTeX

The `--detex` flag removes LaTeX commands, keeping only readable text:

```bash
python3 languagetool_check.py --detex --file capitulo.tex
```

## Output example

![screenshot](etc/screenshot.png)

```
#1 [ORTOGRAFIA]
  Mensagem:   Possível erro de ortografia.
  Categoria:  Erro de Escrita
  Grifo:      "gramatica"
  Sugestões:  gramática

#2 [GRAMÁTICA]
  Mensagem:   Erro de concordância verbal.
  Categoria:  Gramática Geral
  Grifo:      "foram colocado"
  Sugestões:  foram colocados, foi colocado

--- Total: 2 problemas encontrados ---
```

## LanguageTool API (free)

The public API at `api.languagetool.org` is free and needs no key.
For higher rate limits, set up a local LanguageTool server or get a
[Premium API key](https://languagetool.org/premium):

```bash
export LT_USERNAME="your@email.com"
export LT_API_KEY="your-key"
```

## Grammarly backend (English only)

The Grammarly WebSocket API only checks **English** reliably.

```bash
export GRAMMARLY_EMAIL="your@email.com"
export GRAMMARLY_PASSWORD="your-password"
echo "This sentence have a error." | python3 grammarly_check.py
```

## API

### LanguageTool

| Variable        | Default                            | Description                          |
|-----------------|------------------------------------|--------------------------------------|
| `LT_API_URL`    | `https://api.languagetool.org/v2`  | API endpoint.                        |
| `LT_USERNAME`   | —                                  | Premium username (optional).         |
| `LT_API_KEY`    | —                                  | Premium API key (optional).          |

### Grammarly

| Variable            | Default   | Description                               |
|---------------------|-----------|-------------------------------------------|
| `GRAMMARLY_EMAIL`   | —         | Email for premium account (optional).     |
| `GRAMMARLY_PASSWORD`| —         | Password for premium account (optional).  |
| `GRAMMARLY_FORMAT`  | `pretty`  | Output format: `pretty` or `json`.        |

## License

MIT.

[languagetool]: https://languagetool.org
