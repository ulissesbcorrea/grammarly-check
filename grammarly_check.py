#!/usr/bin/env python3
"""
grammarly-check — Check text for grammar and style issues via Grammarly API.

Usage:
  export GRAMMARLY_EMAIL="your@email.com"
  export GRAMMARLY_PASSWORD="your-password"

  python3 grammarly_check.py < file.txt
  echo "Text to check" | python3 grammarly_check.py
  python3 grammarly_check.py "Text to check inline"

Dependencies: requests, websocket-client
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid

import requests
import websocket


GRAMMARLY_COOKIE_URL = "https://grammarly.com/"
GRAMMARLY_AUTH_URL = "https://auth.grammarly.com/v3/api/login"
GRAMMARLY_WS_URL = "wss://capi.grammarly.com/freews"

ORIGIN = "chrome-extension://kbfnbcaeplbcioakkpcpgfkobkghlhen"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) "
    "Gecko/20100101 Firefox/115.0"
)


# ── Auth helpers ──────────────────────────────────────────────────────────────


def _get_cookies() -> tuple[dict[str, str], requests.Session]:
    """Fetch initial cookies from grammarly.com."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    resp = session.get(GRAMMARLY_COOKIE_URL, timeout=15)
    resp.raise_for_status()
    return dict(session.cookies), session


def _premium_login(session: requests.Session, email: str, password: str) -> bool:
    """Authenticate with a paid Grammarly account."""
    csrf = session.cookies.get("csrf-token", domain=".grammarly.com")
    container = session.cookies.get("gnar_containerId", domain=".grammarly.com")
    grauth = session.cookies.get("grauth", domain=".grammarly.com")

    if not csrf or not container:
        print(
            "[!] Auth cookies not found — falling back to anonymous mode.",
            file=sys.stderr,
        )
        return False

    cookie_str = (
        f"gnar_containerId={container}; grauth={grauth}; csrf-token={csrf}"
    )

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "user-agent": USER_AGENT,
        "x-client-type": "funnel",
        "x-client-version": "1.2.2026",
        "x-container-id": container,
        "x-csrf-token": csrf,
        "cookie": cookie_str,
    }

    payload = {"email_login": {
        "email": email, "password": password, "secureLogin": "false",
    }}

    resp = session.post(GRAMMARLY_AUTH_URL, headers=headers, json=payload, timeout=15)
    if resp.status_code == 200:
        print("[+] Premium authentication successful.", file=sys.stderr)
        return True

    print(
        f"[!] Auth failed (HTTP {resp.status_code}): {resp.text[:200]}",
        file=sys.stderr,
    )
    return False


# ── Core API ──────────────────────────────────────────────────────────────────


def check_text(text: str, email: str | None = None,
               password: str | None = None) -> list[dict]:
    """Send *text* to Grammarly and return a list of alerts.

    Parameters
    ----------
    text:
        The text to be checked.
    email, password:
        Optional premium credentials.  When omitted the free tier is used.

    Returns
    -------
    list[dict]
        Each dict contains *title*, *category*, *group*, *impact*,
        *highlight_text*, *replacements*, *explanation* and *free*.
    """
    cookies, session = _get_cookies()

    if email and password:
        _premium_login(session, email, password)
        # Re-fetch cookies after login to pick up session changes.
        cookies, _ = _get_cookies()

    container = cookies.get("gnar_containerId", "")
    grauth = cookies.get("grauth", "")
    csrf = cookies.get("csrf-token", "")

    ws = websocket.WebSocket()
    ws.connect(
        GRAMMARLY_WS_URL,
        origin=ORIGIN,
        header=[
            f"Cookie: gnar_containerId={container}; grauth={grauth}; csrf-token={csrf}",
            f"User-Agent: {USER_AGENT}",
        ],
        timeout=15,
    )

    # 1. Initialisation message.
    ws.send(json.dumps({
        "type": "initial",
        "token": None,
        "docid": str(uuid.uuid4()),
        "client": "extension_chrome",
        "protocolVersion": "1.0",
        "clientSupports": [
            "free_clarity_alerts",
            "readability_check",
            "filler_words_check",
            "sentence_variety_check",
            "free_occasional_premium_alerts",
        ],
        "dialect": "american",
        "clientVersion": "14.924.2437",
        "extDomain": "editpad.org",
        "action": "start",
        "id": 0,
    }))

    time.sleep(0.5)

    # 2. Submit text for checking.
    ws.send(json.dumps({
        "ch": [f"+0:0:{text}:0"],
        "rev": 0,
        "action": "submit_ot",
        "id": 1,
    }))

    alerts: list[dict] = []

    while True:
        try:
            raw = ws.recv()
            if not raw:
                break
            data = json.loads(raw)
        except (websocket.WebSocketTimeoutException, json.JSONDecodeError):
            continue

        action = data.get("action", "")

        if action == "alert":
            alerts.append({
                "title": data.get("title", ""),
                "category": data.get("categoryHuman", data.get("category", "")),
                "group": data.get("group", ""),
                "impact": data.get("impact", ""),
                "begin": data.get("begin", 0),
                "end": data.get("end", 0),
                "highlight_text": data.get("highlightText", ""),
                "replacements": data.get("replacements", []),
                "explanation": _strip_html(data.get("explanation", "")),
                "free": data.get("free", True),
            })
        elif action == "finished":
            break

    ws.close()
    return alerts


# ── Output formatting ────────────────────────────────────────────────────────


def _strip_html(html: str) -> str:
    """Remove HTML tags and decode common entities."""
    clean = re.sub(r"<[^>]+>", "", html)
    for entity, char in [("&nbsp;", " "), ("&amp;", "&"),
                          ("&lt;", "<"), ("&gt;", ">"),
                          ("&quot;", '"')]:
        clean = clean.replace(entity, char)
    return clean.strip()


def _output_json(alerts: list[dict]) -> None:
    """Print alerts as JSON for programmatic consumption."""
    json.dump(alerts, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def _output_pretty(alerts: list[dict]) -> None:
    """Print a human-readable report."""
    if not alerts:
        print("✓ No issues found.")
        return

    premium = sum(1 for a in alerts if not a["free"])
    free = len(alerts) - premium

    for i, a in enumerate(alerts, 1):
        badge = "" if a["free"] else " [PREMIUM]"
        print(f"\n--- Alert #{i}{badge} ---")
        print(f"  Title:       {a['title']}")
        print(f"  Category:    {a['category']} / {a['group']}")
        print(f"  Impact:      {a['impact']}")
        if a["highlight_text"]:
            print(f"  Highlight:   \"{a['highlight_text']}\"")
        if a["replacements"]:
            print(f"  Suggestions: {', '.join(a['replacements'])}")
        if a["explanation"]:
            print(f"  Explanation: {a['explanation']}")

    print(f"\n--- Summary: {free} free, {premium} premium ---")


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    email = os.environ.get("GRAMMARLY_EMAIL")
    password = os.environ.get("GRAMMARLY_PASSWORD")
    fmt = os.environ.get("GRAMMARLY_FORMAT", "pretty")  # "pretty" | "json"

    text: str | None = None

    if not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    elif len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])

    if not text:
        print("Usage:", file=sys.stderr)
        print(f"  {sys.argv[0]} < file.txt", file=sys.stderr)
        print(f"  echo \"text\" | {sys.argv[0]}", file=sys.stderr)
        print(f"  {sys.argv[0]} \"inline text\"", file=sys.stderr)
        print("", file=sys.stderr)
        print("Set GRAMMARLY_EMAIL and GRAMMARLY_PASSWORD for premium access.",
              file=sys.stderr)
        sys.exit(1)

    alerts = check_text(text, email=email, password=password)

    if fmt == "json":
        _output_json(alerts)
    else:
        _output_pretty(alerts)


if __name__ == "__main__":
    main()
