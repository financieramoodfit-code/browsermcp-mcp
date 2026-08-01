# vendor/

The upstream Browser MCP repo was extracted from a private monorepo and imported
several shared workspace packages (`@repo/config`, `@repo/messaging`,
`@repo/types`, `@repo/utils`, and `@r2r/messaging`) that were never published to
npm. As shipped, that made the repo impossible to build on its own.

This directory reconstructs the small surface of those packages that the MCP
server actually uses, so the project builds and runs standalone. The
implementations mirror the behavior of the published `@browsermcp/mcp` package
(the message envelope, config values, and Zod tool schemas are taken from its
compiled output).

| Import path              | Location                     |
| ------------------------ | ---------------------------- |
| `@r2r/messaging/ws/*`    | `vendor/r2r-messaging/ws/`   |
| `@repo/messaging/types`  | `vendor/repo-messaging/`     |
| `@repo/config/*`         | `vendor/config/`             |
| `@repo/types/*`          | `vendor/types/`              |
| `@repo/utils`            | `vendor/utils/`              |

The mappings are declared under `compilerOptions.paths` in `tsconfig.json`, which
both `tsc` (typecheck) and `tsup`/esbuild (build) honor.
