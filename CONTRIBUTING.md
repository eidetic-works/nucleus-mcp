# Contributing to Nucleus

Thank you for your interest in contributing to Nucleus - The Universal Brain for AI Agents.

## We're Open Source! 🎉

Nucleus is fully open source under the MIT license. We welcome contributions of all kinds:

- ✅ **Bug Reports**: Via GitHub Issues
- ✅ **Feature Requests**: Via GitHub Discussions  
- ✅ **Code Contributions**: Via Pull Requests
- ✅ **Documentation**: Improvements always welcome
- ✅ **Integrations**: Add support for new AI tools

## Start here: two commands

Run these from the **repository root** (one level above this package — the
scripts live there because they cover the whole repo, not just this directory):

```bash
bash scripts/verify.sh          # where does this repo stand, right now?
bash scripts/install_hooks.sh   # enable the commit guards (run once after cloning)
```

`verify.sh` needs nothing but this repo — no other checkout, no shared config, no
prior knowledge. It builds a clean virtualenv, installs the package, runs the
suite, and reports:

* the branch and commit it examined, so a result can never be about a tree you
  did not mean to test
* the interpreter it used, and whether it satisfies `requires-python` — it will
  look for a newer Python on your PATH before telling you to install one
* failures that are **new**, measured against `.known-failures.txt`, so you can
  tell your breakage from the ones you inherited
* three outcomes, not two: `OK`, `NOT OK`, and `INSUFFICIENT` (exit 3) when the
  environment — usually no network — stopped the run before anything was checked.
  A red result you cannot act on is worse than an honest "nothing was verified".

`install_hooks.sh` points git at this repo's own `.githooks/`. The secret scan
lives in the repo and runs for everyone. The identity scan is personal to the
maintainer and loads from outside it, so you do not need it and will not be asked
for it — the hook says so and carries on.

## Before you open a pull request

```bash
bash scripts/verify.sh                                   # must not add new failures
python3 -m pytest tests/test_split_regression_guards.py   # no absolute home paths, no sibling-repo literals
```

Two rules the tests here enforce, both learned the hard way:

* **No absolute home-directory paths in shipped code.** A clone must
  not carry paths that exist on one machine.
* **Every gate ships with the input that makes it fail.** A check that has never
  been observed failing is not known to work; roughly a third of this project's
  accumulated postmortems are a correct check pointed at the wrong object.

## How to Contribute

### 1. Bug Reports

Found a bug? Please open a GitHub Issue with:

- **Environment**: Python version, OS, MCP client
- **Steps to Reproduce**: Minimal example
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Logs**: Relevant error messages (sanitize sensitive data)

### 2. Feature Requests

Have an idea? Open a GitHub Discussion with:

- **Problem Statement**: What problem does this solve?
- **Proposed Solution**: How would you implement it?
- **Alternatives Considered**: What else did you consider?
- **Use Cases**: Who benefits from this?

### 3. Documentation

Documentation improvements are always welcome:

- Typo fixes
- Clarification of existing docs
- New examples or tutorials
- Translations

Submit a Pull Request to the `docs/` directory.

### 4. Beta Testing

We're looking for beta testers to validate new features:

- Test pre-release versions
- Provide feedback on UX
- Report edge cases
- Suggest improvements

Contact us to join the beta program.

## Code of Conduct

### Be Respectful
- Treat everyone with respect
- No harassment, discrimination, or personal attacks
- Assume good intent

### Be Constructive
- Provide actionable feedback
- Focus on the problem, not the person
- Celebrate successes

### Be Patient
- Maintainers are volunteers
- Response times may vary
- Quality over speed

## Code Contributions

### Good First Issues

Look for issues labeled `good-first-issue` - these are ideal for new contributors:
- Documentation improvements
- Small bug fixes
- Test coverage additions
- New integration examples

### Development Setup

```bash
# Clone the repo
git clone https://github.com/eidetic-works/nucleus-mcp.git
cd mcp-server-nucleus

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest tests/`)
6. Commit with clear messages
7. Push to your fork
8. Open a Pull Request

### PR Review Criteria

- [ ] Tests pass
- [ ] Code follows existing style
- [ ] Documentation updated if needed
- [ ] No breaking changes (or clearly documented)

## Enterprise Inquiries

For enterprise licensing or partnership inquiries:
- Email: partnerships@nucleusos.dev

## Security Vulnerabilities

**Do NOT report security vulnerabilities via public GitHub Issues.**

Instead, email: security@nucleusos.dev

Include:
- Detailed description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes

We follow responsible disclosure and will credit researchers who report valid vulnerabilities.

## License

By contributing to Nucleus, you agree that your contributions will be licensed under the project's license terms.

## Questions?

- **General Questions**: GitHub Discussions
- **Bug Reports**: GitHub Issues
- **Partnership**: hello@nucleusos.dev
- **Security**: hello@nucleusos.dev

---

*Thank you for helping make Nucleus better!*

*— The Nucleus Team*

## Sign your work (DCO)

Every commit in a pull request needs a `Signed-off-by` line certifying the
Developer Certificate of Origin. Add it with:

```bash
git commit -s -m "your message"
```

This appends `Signed-off-by: Your Name <you@example.com>` using the name and
email in your git config. The full certificate text is in [DCO.md](../DCO.md).

A pull request whose commits are not signed off cannot be merged.
