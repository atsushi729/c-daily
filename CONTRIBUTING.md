# Contributing to c-daily

Contributions to c-daily are welcome!

## Development Setup

```bash
git clone https://github.com/atsushi729/c-daily
cd c-daily
uv run pytest tests/ -v
```

## Reporting Issues

Please report bugs and feature requests via [GitHub Issues](https://github.com/atsushi729/c-daily/issues).

**Please include the following when reporting a bug:**

- OS and version (output of `sw_vers`)
- Python version (`python3 --version`)
- Claude Code version
- Output of `cdl status`
- Steps to reproduce and expected behavior

## Pull Requests

1. Fork this repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Write tests and make them pass: `pytest tests/`
4. Commit using [Conventional Commits](https://www.conventionalcommits.org/) format:
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation-only change
   - `test:` adding or updating tests
   - `chore:` build, CI, etc.
5. Open a PR

## Roadmap (contributions welcome)

- [ ] Linux (systemd timer) support
- [ ] Automatic Git hook setup
- [ ] Obsidian vault output
- [ ] Weekly summary (`cdl weekly`)
- [ ] Multi-project support

## Code Guidelines

- **Shell scripts**: POSIX-compliant, pass `shellcheck`
- **Python**: standard library only (no external dependencies), type hints encouraged
- **Tests**: `pytest`, all new features must include tests
