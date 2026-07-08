# MCP Grafana

Guide for using **Grafana MCP** with **Cursor** in the HomeProd-K3s lab.

Hebrew guide: [explain-mcp-grafana-he.md](explain-mcp-grafana-he.md)

## What is this?

**MCP** (Model Context Protocol) lets Cursor (the AI in your IDE) talk to external tools.  
**Grafana MCP** (`mcp-grafana`) is a small program that connects Cursor to your **Grafana server** so the AI can:

- Create and update dashboards
- Query Prometheus and Loki
- List datasources, folders, and applications
- Search metrics and logs

You do **not** need the `grafana-mcp` Helm chart in Kubernetes for this setup. Grafana stays in the cluster; only the MCP bridge runs on your computer.

## How it works

```
┌─────────┐      MCP       ┌──────────────┐    HTTP API    ┌─────────────────┐
│ Cursor  │ ─────────────► │ mcp-grafana  │ ──────────────► │ Grafana (K3s)   │
│  (IDE)  │   (local)      │  via uvx     │                 │ + Prometheus    │
└─────────┘                └──────────────┘                 └─────────────────┘
```

| Component | Role |
|-----------|------|
| **Cursor** | Your IDE; sends requests to MCP |
| **uvx** | Downloads and runs `mcp-grafana` locally (like `npx` for Node) |
| **mcp-grafana** | MCP server; translates AI actions into Grafana API calls |
| **Grafana** | Your running instance (e.g. `grafana-k3s.spider-shlomo.com`) |
| **Service account token** | Authenticates MCP to Grafana API |

## What does `uvx` do?

`uvx` is part of **[uv](https://github.com/astral-sh/uv)** — a fast Python package runner.

When Cursor runs:

```bash
/home/shlomob/.local/bin/uvx mcp-grafana
```

1. **First run** — `uvx` downloads the `mcp-grafana` package and caches it
2. **Every run** — `uvx` starts the MCP server process
3. **Cursor** connects to that process and can call tools like `update_dashboard`, `query_prometheus`, etc.
4. **mcp-grafana** calls Grafana’s REST API using your URL and token

`uvx` does **not** install Grafana locally. It only runs the MCP bridge.

## Why use the full path to `uvx`?

In `~/.cursor/mcp.json` we use:

```json
"command": "/home/shlomob/.local/bin/uvx"
```

instead of:

```json
"command": "uvx"
```

Cursor often does not have `~/.local/bin` in its `PATH`, which causes:

```
spawn uvx ENOENT
```

The full path fixes that error.

## Configuration (`~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "grafana": {
      "command": "/home/shlomob/.local/bin/uvx",
      "args": ["mcp-grafana"],
      "env": {
        "GRAFANA_URL": "https://grafana-k3s.spider-shlomo.com",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "glsa_YOUR_TOKEN_HERE"
      }
    }
  }
}
```

| Variable | Description |
|----------|-------------|
| `GRAFANA_URL` | Your Grafana base URL (must be reachable from your PC) |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | Grafana service account token (`glsa_...`) with dashboard write permissions |

> **Security:** Do not commit the real token to Git. Keep it only in `mcp.json` (local) or a secrets manager.

## Install `uv` / `uvx` (one time)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
which uvx
```

Then **restart Cursor** or reload MCP: **Settings → MCP → grafana → Restart**.

## Verify MCP is connected

1. Open **Cursor → Settings → MCP**
2. Find **grafana** — status should be **green / connected**
3. If red, check:
   - `uvx` exists: `which uvx`
   - Grafana is reachable: open `GRAFANA_URL` in a browser
   - Token is valid and has `dashboards:create` + `dashboards:write` (or `dashboards:*`)

## Grafana MCP vs Grafana Helm chart

| | **Local MCP (`uvx mcp-grafana`)** | **Helm chart `grafana-mcp`** |
|---|-----------------------------------|------------------------------|
| Runs on | Your laptop | Inside Kubernetes |
| Used by | Cursor IDE | Any MCP client over network |
| Needs Helm chart | No | Yes |
| This project uses | **Yes** | No |

The normal **`grafana`** Helm chart (in `app-of-apps/chart-grafana/`) is Grafana itself — dashboards, UI, datasources. That is separate from MCP.

## What the AI can do via MCP (examples)

- Create dashboards (e.g. `test-shlomo-pods-up` → **pods state**, `argocd-sync-health`)
- Organize dashboards into folders (`gitops-argocd`, `pods state`)
- Run PromQL / LogQL queries to validate panels before saving
- Patch dashboard panels without manual JSON editing

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `spawn uvx ENOENT` | Install `uv`, use full path in `mcp.json`, restart Cursor |
| MCP connected but no data | Check Prometheus datasource in Grafana; verify metrics exist |
| Cannot create dashboards | Token needs write permissions; do not use `--disable-write` |
| Grafana URL unreachable | VPN, DNS, or firewall — MCP runs from your PC, not from the cluster |

## Useful links

- [Grafana MCP (GitHub)](https://github.com/grafana/mcp-grafana)
- [Grafana MCP docs](https://grafana.com/docs/grafana/latest/developer-resources/mcp/)
- [uv installer](https://github.com/astral-sh/uv)
