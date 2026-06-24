#!/usr/bin/env python3
"""
languagetool-check — Check text for grammar and style issues via LanguageTool API.

Detects the language automatically and supports Portuguese (Brazil) natively.

Usage:
  python3 languagetool_check.py < file.txt
  echo "Text to check" | python3 languagetool_check.py
  python3 languagetool_check.py "inline text"
  python3 languagetool_check.py --language pt-BR < artigo.tex

Environment:
  LT_API_URL   LanguageTool API endpoint (default: https://api.languagetool.org/v2)
  LT_USERNAME  LanguageTool Premium username (optional)
  LT_API_KEY   LanguageTool Premium API key (optional)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

import requests

API_URL = os.environ.get("LT_API_URL", "https://api.languagetool.org/v2")


CHUNK_SIZE = 15000  # characters per API request (free tier limit ~20k)


def _split_chunks(text: str, max_size: int = CHUNK_SIZE) -> list[str]:
    """Split *text* into chunks at sentence boundaries, each ≤ *max_size* chars."""
    if len(text) <= max_size:
        return [text]

    # Split at sentence boundaries (., !, ? followed by space or newline).
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""

    for sent in sentences:
        if len(current) + len(sent) + 1 > max_size:
            if current:
                chunks.append(current)
            # If a single sentence is too long, split mid-sentence.
            if len(sent) > max_size:
                for i in range(0, len(sent), max_size):
                    chunks.append(sent[i:i + max_size])
                current = ""
            else:
                current = sent
        else:
            current = (current + " " + sent) if current else sent

    if current:
        chunks.append(current)

    return chunks


def _check_chunk(
    text: str,
    language: str,
    headers: dict[str, str],
    timeout: int,
) -> dict:
    """Send a single chunk to LanguageTool and return the raw JSON response."""
    resp = requests.post(
        f"{API_URL}/check",
        data={"text": text, "language": language},
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def check_text(
    text: str,
    language: str = "auto",
    enabled_rules: list[str] | None = None,
    disabled_rules: list[str] | None = None,
    username: str | None = None,
    api_key: str | None = None,
    timeout: int = 30,
) -> list[dict]:
    """Send *text* to LanguageTool and return a list of matches.

    Automatically splits long text into chunks to stay within API limits.

    Parameters
    ----------
    text:
        The text to check.
    language:
        Language code (e.g. ``"pt-BR"``, ``"en-US"``) or ``"auto"`` for
        automatic detection.
    enabled_rules, disabled_rules:
        Rule IDs to force-enable or disable.
    username, api_key:
        LanguageTool Premium credentials (optional — free tier is sufficient
        for most needs).

    Returns
    -------
    list[dict]
        Each dict contains *message*, *short_message*, *replacements*,
        *context*, *offset*, *length*, *rule_category*, *rule_id*,
        *rule_issue_type*, *sentence*, and *language*.
    """
    headers: dict[str, str] = {}
    if username and api_key:
        headers["Authorization"] = _basic_auth(username, api_key)

    if enabled_rules:
        headers.setdefault("X-Enabled-Rules", ",".join(enabled_rules))
    if disabled_rules:
        headers.setdefault("X-Disabled-Rules", ",".join(disabled_rules))

    chunks = _split_chunks(text)

    all_matches: list[dict] = []
    lang_info: dict = {}

    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            print(f"[*] Chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...", file=sys.stderr)

        result = _check_chunk(chunk, language, headers, timeout)
        lang_info = result.get("language", {})

        for m in result.get("matches", []):
            ctx = m.get("context", {})
            rule = m.get("rule", {})

            all_matches.append({
                "message": m.get("message", ""),
                "short_message": m.get("shortMessage", ""),
                "replacements": [r["value"] for r in m.get("replacements", [])],
                "context_text": ctx.get("text", ""),
                "offset": m.get("offset", 0),
                "length": m.get("length", 0),
                "highlight": m.get("context", {}).get("text", "")[
                    m.get("offset", 0):m.get("offset", 0) + m.get("length", 0)
                ],
                "rule_category": rule.get("category", {}).get("name", ""),
                "rule_id": rule.get("id", ""),
                "rule_issue_type": rule.get("issueType", ""),
                "sentence": m.get("sentence", ""),
                "language": lang_info.get("detectedLanguage", {}).get("code", language),
            })

    return all_matches


def _basic_auth(username: str, api_key: str) -> str:
    """Build HTTP Basic Auth header value."""
    import base64
    token = base64.b64encode(f"{username}:{api_key}".encode()).decode()
    return f"Basic {token}"


# ── Output formatting ────────────────────────────────────────────────────────


def _output_json(matches: list[dict]) -> None:
    json.dump(matches, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


_COLORS = {
    "misspelling": "\033[91m",   # red
    "grammar": "\033[93m",       # yellow
    "style": "\033[94m",         # blue
    "typographical": "\033[96m", # cyan
    "uncategorized": "\033[90m", # grey
    "reset": "\033[0m",
    "bold": "\033[1m",
}

_TYPES = {
    "misspelling": "ortografia",
    "grammar": "gramática",
    "style": "estilo",
    "typographical": "tipografia",
}


def _output_pretty(matches: list[dict]) -> None:
    if not matches:
        print("✓ Nenhum problema encontrado.")
        return

    for i, m in enumerate(matches, 1):
        itype = m.get("rule_issue_type", "uncategorized")
        color = _COLORS.get(itype, _COLORS["uncategorized"])
        label = _TYPES.get(itype, itype)

        print(f"\n{color}{_COLORS['bold']}#{i} [{label.upper()}]{_COLORS['reset']}")
        print(f"  Mensagem:   {m['message']}")
        print(f"  Categoria:  {m['rule_category']}")
        if m.get("short_message"):
            print(f"  Resumo:     {m['short_message']}")
        if m["highlight"]:
            print(f"  Grifo:     {color}\"{m['highlight']}\"{_COLORS['reset']}")
        if m["replacements"]:
            sug = ", ".join(m["replacements"][:5])
            print(f"  Sugestões:  {sug}")
        print(f"  Sentença:   {m['sentence'][:120]}")

    print(f"\n--- Total: {len(matches)} problemas encontrados ---")


# ── Detex (strip LaTeX) ─────────────────────────────────────────────────────


def detex(text: str) -> str:
    """Remove LaTeX commands from *text*, keeping only readable content."""
    text = re.sub(r"\\[a-zA-Z]+(?:\{[^}]*\}|\[[^\]]*\])*", "", text)
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"%.*", "", text)
    text = re.sub(r"\\", " ", text)
    text = re.sub(r"\^[a-z]", "", text)
    text = re.sub(r"~", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── CLI ──────────────────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    username = os.environ.get("LT_USERNAME")
    api_key = os.environ.get("LT_API_KEY")

    parser = argparse.ArgumentParser(
        description="Check text for grammar and style issues via LanguageTool.",
    )
    parser.add_argument(
        "text", nargs="*",
        help="Text to check (if omitted, reads from stdin).",
    )
    parser.add_argument(
        "-l", "--language", default="auto",
        help="Language code (e.g. pt-BR, en-US) or 'auto' for auto-detect.",
    )
    parser.add_argument(
        "--detex", action="store_true",
        help="Strip LaTeX markup before checking.",
    )
    parser.add_argument(
        "--json", dest="fmt", action="store_const", const="json", default="pretty",
        help="Output JSON instead of human-readable format.",
    )
    parser.add_argument(
        "--file", type=str, help="Read text from file.",
    )

    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            text = f.read()
    elif args.text:
        text = " ".join(args.text)
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    if args.detex:
        text = detex(text)

    text = text.strip()
    if not text:
        print("Nenhum texto para verificar.", file=sys.stderr)
        sys.exit(0)

    print(f"[*] Verificando {len(text)} caracteres...", file=sys.stderr)

    matches = check_text(
        text,
        language=args.language,
        username=username,
        api_key=api_key,
    )

    if args.fmt == "json":
        _output_json(matches)
    else:
        _output_pretty(matches)


if __name__ == "__main__":
    main()
