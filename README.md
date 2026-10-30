# Smoked Paprika

A remote [MCP](https://modelcontextprotocol.io/) server that lets Claude search
and read your [Paprika](https://www.paprikaapp.com/) recipe collection.

It serves the latest **export** of your collection, which an iOS Shortcut
uploads from Paprika's share sheet. It never contacts Paprika's servers. Paprika's
terms forbid third-party access to them and warn that accounts doing it may be
blocked, so this project works only from files the app itself exports. See
[the design](docs/design.md#why-an-export-and-never-the-sync-api).

> **Status: scaffold.** The released image answers a health check and nothing
> more. The work is specified in [`todos/`](todos/README.md), in order.

## How it works

1. In Paprika: Settings → Export Recipes → All Recipes → Paprika Recipe Format.
2. Share the export to the *Send to smoked-paprika* Shortcut, which uploads it.
3. In Claude, with smoked-paprika added as a custom connector, ask about your
   recipes. Sign-in is through Google, restricted to the addresses you allow.

The data is as fresh as your last export, and smoked-paprika tells Claude how
old that is.

## Documentation

- [`docs/design.md`](docs/design.md): the design, and why it is shaped this way
- [`docs/releasing.md`](docs/releasing.md): how a version is made and published
- [`todos/`](todos/README.md): the work still to do
- [`AGENTS.md`](AGENTS.md): how work is done in this repository

## License

[MIT](LICENSE)
