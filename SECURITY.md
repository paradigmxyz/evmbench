# Security

`evmbench` executes an LLM-driven agent against uploaded, untrusted code in an isolated worker environment. Treat the worker and anything it touches (filesystem, logs, outputs) as adversarial.

This document describes the trust boundaries and the two supported approaches for handling OpenAI credentials.

## Trust boundaries

- Uploaded code is untrusted and may be intentionally malicious.
- The agent can run tools and read files in its workspace.
- The worker runtime should be treated as an untrusted environment for any secret material.

## OpenAI credential handling

### Direct BYOK (default)

The user provides an OpenAI API key and the worker uses it directly (exported as `OPENAI_API_KEY` / `CODEX_API_KEY`).

This is designed for local use and straightforward self-hosting where the operator accepts that secrets are present in the worker environment.

### Proxy-token mode (optional)

The worker does not receive a plaintext OpenAI API key.

Instead:

- the backend encrypts the user-provided key and places an opaque token in the secret bundle
- the worker routes requests through `oai_proxy`
- `oai_proxy` decrypts the token and forwards requests upstream

This reduces the blast radius of a compromised worker by keeping plaintext API keys out of the agent container.

## Operational guidance

- Run workers with minimal privileges and scoped access; do not mount host credentials or unrelated secrets.
- Avoid logging request headers and environment variables in production environments.
- Assume agent output is untrusted input; validate and sanitize before using it in other systems.

## Local no-Docker mode (ZCode agent)

The local mode (`backend/scripts/local_dev.sh`) trades isolation for
convenience and is intended for single-user machines only:

- Workers run directly on the host — there is no container sandbox, resource
  limit or pid namespace. The audit agent executes with your user permissions
  (`ZCODE_MODE=yolo` by default, matching the Codex runner's bypass mode).
- The ZCode worker reuses the desktop app login session (no API key is
  handled by the stack). The agent process can therefore access that session
  like any process you run yourself.
- For read-only audits of less trusted code, start the stack with
  `ZCODE_MODE=plan`, which restricts the agent to non-mutating actions (at the
  cost of not being able to build or run test suites against the sources).
- Uploaded contract code is still untrusted input; audit code you would be
  comfortable running local tooling against.


