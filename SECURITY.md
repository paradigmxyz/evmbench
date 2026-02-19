# security

`svmbench` executes an llm-driven agent against uploaded, untrusted code in an isolated worker environment. treat the worker and anything it touches (filesystem, logs, outputs) as adversarial.

this document describes the trust boundaries and the two supported approaches for handling openai credentials.

## trust boundaries

- uploaded code is untrusted and may be intentionally malicious.
- the agent can run tools and read files in its workspace.
- the worker runtime should be treated as an untrusted environment for any secret material.

## openai credential handling

### direct byok (default)

the user provides an openai api key and the worker uses it directly (exported as `OPENAI_API_KEY` / `CODEX_API_KEY`).

this is designed for local use and straightforward self-hosting where the operator accepts that secrets are present in the worker environment.

### proxy-token mode (optional)

the worker does not receive a plaintext openai api key.

instead:

- the backend encrypts the user-provided key and places an opaque token in the secret bundle
- the worker routes requests through `oai_proxy`
- `oai_proxy` decrypts the token and forwards requests upstream

this reduces the blast radius of a compromised worker by keeping plaintext api keys out of the agent container.

## operational guidance

- run workers with minimal privileges and scoped access; do not mount host credentials or unrelated secrets.
- avoid logging request headers and environment variables in production environments.
- assume agent output is untrusted input; validate and sanitize before using it in other systems.
