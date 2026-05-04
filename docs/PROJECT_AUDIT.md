# Project Audit

## Current Status

- The codebase originally mixed `maxbridge`, `maxbridge-client`, and `maxbridge_client`.
- Core client lifecycle logic had inconsistent reconnect and cleanup behavior.
- Group and message helpers contained payload bugs and mutable defaults.
- Examples and packaging metadata did not match the importable package layout.

## Decisions

- Keep `maxbridge-client` as the distribution name.
- Support both `maxbridge_client` and `maxbridge` import styles for developer ergonomics.
- Add a typed packet parser instead of exposing only raw WebSocket payloads.
- Treat the existing protocol surface as reverse-engineered and document it explicitly.

## Remaining Risks

- Live protocol compatibility still depends on current MAX web client behavior.
- Reconnect restoration requires user-supplied auth/session recovery logic.
- Runtime integration tests are blocked locally until `aiohttp` and `websockets` are installed.

## Next Recommended Work

- Add real integration tests with recorded packets or a mock WebSocket server.
- Add message/search/chat parser coverage for more incoming packet shapes.
- Add CI checks for linting, typing, unit tests, and packaging smoke tests.
