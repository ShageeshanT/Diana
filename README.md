# Diana

A super efficient morning brief CLI that reads your Google Calendar, Gmail,
and GitHub notifications in one batched call and prints a clean stdout
summary. Powered by [Composio](https://composio.dev) MCP.

## Why

Three tabs, three loads, three contexts every morning. `brief.py` collapses
all of that into one HTTP round trip and a 30 line summary.

## Setup

1. Connect Gmail, Google Calendar, and GitHub to your Composio workspace at
   [dashboard.composio.dev](https://dashboard.composio.dev).
2. Grab your Composio consumer key (starts with `ck_`).
3. Export it:

   ```bash
   export COMPOSIO_CONSUMER_KEY=ck_xxx
   ```

## Usage

```bash
./brief.py            # pretty print
./brief.py --json     # raw JSON for scripting
```

Sample output:

```
  Diana Brief, Mon 04 May 2026
  ────────────────────────────────────────

  Calendar today (2)
    09:00    Standup
    14:30    Customer call: Acme

  Unread Gmail (3)
    GitHub                        Pull request review requested
    Stripe                        Receipt for May
    LinkedIn                      Shagee, you have 2 new messages

  GitHub notifications (1)
    ShageeshanT/diana             Bump dependency
```

## How it works

One JSON-RPC call to `https://connect.composio.dev/mcp` with
`COMPOSIO_MULTI_EXECUTE_TOOL` batching three tool slugs:

- `GOOGLECALENDAR_EVENTS_LIST` for today's events
- `GMAIL_FETCH_EMAILS` filtered by `is:unread`
- `GITHUB_LIST_NOTIFICATIONS_FOR_THE_AUTHENTICATED_USER` for active threads

The Composio MCP server fans those out to each provider in parallel and
returns a single SSE wrapped response. `brief.py` unwraps and renders.

Stdlib only, no third party Python deps.

## License

MIT.
