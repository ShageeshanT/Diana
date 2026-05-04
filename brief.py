#!/usr/bin/env python3
"""Diana brief — one shot morning brief.

Pulls today's Google Calendar events, recent unread Gmail, and open GitHub
notifications in a single batched call to the Composio MCP, then prints a
clean summary. No third party Python deps, just the stdlib.

Usage:
  COMPOSIO_CONSUMER_KEY=ck_xxx ./brief.py
  COMPOSIO_CONSUMER_KEY=ck_xxx ./brief.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

MCP_URL = "https://connect.composio.dev/mcp"


def call_mcp(consumer_key: str, tools: list[dict]) -> dict:
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "COMPOSIO_MULTI_EXECUTE_TOOL",
            "arguments": {"tools": tools},
        },
    }).encode()
    req = urllib.request.Request(
        MCP_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "x-consumer-api-key": consumer_key,
        },
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read().decode()
    m = re.search(r"data:\s*(\{.*\})\s*$", raw, re.S)
    if not m:
        raise RuntimeError("unexpected MCP response: " + raw[:200])
    env = json.loads(m.group(1))
    return json.loads(env["result"]["content"][0]["text"])


def today_window():
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")


def shorten(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def render(out: dict) -> str:
    today = datetime.now().strftime("%a %d %b %Y")
    lines = [f"\n  Diana Brief, {today}", "  " + "─" * 40]

    cal = out.get("GOOGLECALENDAR_EVENTS_LIST", {}).get("data") or {}
    events = cal.get("items") or cal.get("events") or []
    lines.append(f"\n  Calendar today ({len(events)})")
    if not events:
        lines.append("    nothing on the books")
    for ev in events[:5]:
        start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date") or ""
        time_str = start.split("T")[1][:5] if "T" in start else "all day"
        lines.append(f"    {time_str:<8} {shorten(ev.get('summary'), 60)}")

    gm = out.get("GMAIL_FETCH_EMAILS", {}).get("data") or {}
    msgs = gm.get("messages") or gm.get("emails") or gm.get("results") or []
    lines.append(f"\n  Unread Gmail ({len(msgs)})")
    if not msgs:
        lines.append("    inbox zero")
    for m in msgs[:5]:
        sub = m.get("subject") or "(no subject)"
        sender = m.get("sender") or m.get("from") or "?"
        lines.append(f"    {shorten(sender, 28):<28}  {shorten(sub, 60)}")

    gh = out.get("GITHUB_LIST_NOTIFICATIONS_FOR_THE_AUTHENTICATED_USER", {}).get("data") or {}
    notes = gh if isinstance(gh, list) else (gh.get("notifications") or gh.get("results") or [])
    lines.append(f"\n  GitHub notifications ({len(notes)})")
    if not notes:
        lines.append("    quiet on the repo front")
    for n in notes[:5]:
        repo = ((n.get("repository") or {}).get("full_name")) or "?"
        title = (n.get("subject") or {}).get("title") or "?"
        lines.append(f"    {shorten(repo, 28):<28}  {shorten(title, 60)}")

    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Diana morning brief")
    ap.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted brief")
    args = ap.parse_args()

    key = os.environ.get("COMPOSIO_CONSUMER_KEY")
    if not key:
        sys.exit(
            "error: set COMPOSIO_CONSUMER_KEY in env\n"
            "  hint: it lives at /data/.openclaw/openclaw.json under "
            "plugins.entries.composio.config.consumerKey"
        )

    tmin, tmax = today_window()
    tools = [
        {
            "tool_slug": "GOOGLECALENDAR_EVENTS_LIST",
            "arguments": {
                "calendarId": "primary",
                "timeMin": tmin,
                "timeMax": tmax,
                "maxResults": 25,
                "singleEvents": True,
                "orderBy": "startTime",
            },
        },
        {
            "tool_slug": "GMAIL_FETCH_EMAILS",
            "arguments": {"query": "is:unread", "max_results": 8},
        },
        {
            "tool_slug": "GITHUB_LIST_NOTIFICATIONS_FOR_THE_AUTHENTICATED_USER",
            "arguments": {"per_page": 8},
        },
    ]

    inner = call_mcp(key, tools)
    out = {}
    for r in inner.get("data", {}).get("results", []):
        slug = r.get("tool_slug")
        resp = r.get("response", {})
        out[slug] = {
            "successful": resp.get("successful"),
            "data": resp.get("data"),
            "error": resp.get("error"),
        }

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print(render(out))


if __name__ == "__main__":
    main()
