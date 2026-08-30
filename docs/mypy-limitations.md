# mypy limitations (RC3)

The following are **third-party typing** issues, not runtime defects:

1. OpenAI / Anthropic / Grok providers: `AsyncStream` vs `ChatCompletion` union on stream APIs; tool call union types lacking `.function` without narrowing.
2. Tool `execute` overrides use explicit parameter names (validated by Pydantic) while the base class uses `**kwargs` — intentional for clarity.

CI continues to run `mypy app` with `mypy.ini` isolating vendor SDK modules.
