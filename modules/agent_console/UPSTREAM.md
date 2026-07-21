# Agent Console v1 upstream note

Conceptual reference only; no upstream source code was copied.

- Project: LibreChat
- Repository: https://github.com/danny-avila/LibreChat
- Files reviewed: `README.md`, `librechat.example.yaml`, `LICENSE`, and public release notes
- License: MIT, https://github.com/danny-avila/LibreChat/blob/main/LICENSE
- Patterns reimplemented locally: isolated subagent work orders, bounded recursion/steps, deferred tool
  discovery, and one-screen status/result presentation.

The implementation in this directory is original Python written for AI-Content-OS contracts. It
does not include LibreChat authentication, provider clients, database models, React components,
paid API wiring, or publishing behavior.
