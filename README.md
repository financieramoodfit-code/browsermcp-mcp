<a href="https://browsermcp.io">
  <img src="./.github/images/banner.png" alt="Browser MCP banner">
</a>

<h3 align="center">Browser MCP</h3>

<p align="center">
  Automate your browser with AI.
  <br />
  <a href="https://browsermcp.io"><strong>Website</strong></a> 
  •
  <a href="https://docs.browsermcp.io"><strong>Docs</strong></a>
</p>

## About

Browser MCP is an MCP server + Chrome extension that allows you to automate your browser using AI applications like VS Code, Claude, Cursor, and Windsurf.

## Features

- ⚡ Fast: Automation happens locally on your machine, resulting in better performance without network latency.
- 🔒 Private: Since automation happens locally, your browser activity stays on your device and isn't sent to remote servers.
- 👤 Logged In: Uses your existing browser profile, keeping you logged into all your services.
- 🥷🏼 Stealth: Avoids basic bot detection and CAPTCHAs by using your real browser fingerprint.

## Running as an MCP server

This repo builds and runs standalone. The internal monorepo packages the upstream
code depends on (`@repo/*` and `@r2r/messaging`) are reconstructed under
[`vendor/`](./vendor) and wired up through `tsconfig.json` path aliases, so no
private workspace packages are required.

```bash
npm install      # installs deps and builds dist/ via the prepare hook
npm run build    # (re)build dist/index.js
node dist/index.js
```

The server communicates over stdio using the Model Context Protocol and opens a
WebSocket server on port `9009` that the Browser MCP Chrome extension connects
to. To use it with an MCP client, register the built binary — for example:

```json
{
  "mcpServers": {
    "browsermcp": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"]
    }
  }
}
```

After installing the [Browser MCP Chrome extension](https://browsermcp.io), click
its icon and press **Connect** on the tab you want to automate.

## Contributing

This repo contains all the core MCP code for Browser MCP. It was originally
developed inside a monorepo and depended on shared `utils` and `types` packages;
those have been vendored (see [`vendor/`](./vendor)) so the project can be built
and run on its own.

## Credits

Browser MCP was adapted from the [Playwright MCP server](https://github.com/microsoft/playwright-mcp) in order to automate the user's browser rather than creating new browser instances. This allows using the user's existing browser profile to use logged-in sessions and avoid bot detection mechanisms that commonly block automated browser use.
