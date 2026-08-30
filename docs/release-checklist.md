# Release checklist

1. pytest -q
2. ruff check app tests
3. python -m app.cli release-audit
4. python -m app.cli smoke-grok (real key)
5. Windows acceptance (docs/windows-acceptance.md)
