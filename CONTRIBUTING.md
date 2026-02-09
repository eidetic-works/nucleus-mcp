# Contributing to Nucleus MCP

Thank you for your interest in contributing to Nucleus MCP - The Universal Brain for AI Agents.

## We're Open Source! 🎉

Nucleus is fully open source under the MIT license. We welcome contributions of all kinds:

- ✅ **Bug Reports**: Via GitHub Issues
- ✅ **Feature Requests**: Via GitHub Discussions
- ✅ **Code Contributions**: Via Pull Requests
- ✅ **Documentation**: Improvements always welcome
- ✅ **Integrations**: Add support for new AI tools

## How to Contribute

### 1. Bug Reports

Found a bug? Please open a GitHub Issue with:

- **Environment**: Python version, OS, MCP client (Claude/Cursor/Windsurf)
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

### 3. Code Contributions

#### Good First Issues

Look for issues labeled `good-first-issue` - these are ideal for new contributors:
- Documentation improvements
- Small bug fixes
- Test coverage additions
- New integration examples

#### Development Setup

```bash
# Clone the repo
git clone https://github.com/eidetic-works/nucleus-mcp.git
cd nucleus-mcp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/
```

#### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest tests/`)
6. Run linting (`ruff check src/`)
7. Commit with clear messages
8. Push to your fork
9. Open a Pull Request

#### PR Review Criteria

- [ ] Tests pass
- [ ] Code follows existing style
- [ ] Documentation updated if needed
- [ ] No breaking changes (or clearly documented)

### 4. Documentation

Documentation improvements are always welcome:

- Typo fixes
- Clarification of existing docs
- New examples or tutorials
- Integration guides for new tools

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

## Security Vulnerabilities

**Do NOT report security vulnerabilities via public GitHub Issues.**

Instead, email: security@nucleus-mcp.com

Include:
- Detailed description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes

We follow responsible disclosure and will credit researchers who report valid vulnerabilities.

## License

By contributing to Nucleus MCP, you agree that your contributions will be licensed under the MIT License.

## Questions?

- **General Questions**: GitHub Discussions
- **Bug Reports**: GitHub Issues
- **Security**: security@nucleus-mcp.com

---

*Thank you for helping make Nucleus better!*

*— The Nucleus Team*
