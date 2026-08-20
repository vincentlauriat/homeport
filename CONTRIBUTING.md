# Contributing

Thanks for stopping by! Homeport is small on purpose — the bar for a change is "does it help
someone glance at their home server?".

- **Bugs / ideas**: open an issue with what you saw and what you expected.
- **Code**: fork, branch, `venv/bin/python -m pytest` green, conventional commit messages,
  PR. New behavior comes with a test (the repo is test-driven; async tests use
  `asyncio.run()`, not pytest-asyncio).
- **Translations**: copy `homeport/i18n/en.json`, translate the values, keep the keys —
  the test suite checks catalog parity.
- **Principles**: stdlib over dependencies (SQLite, no front framework), read what the
  machine already knows, degrade gracefully when a tool is missing, LAN read-only.
