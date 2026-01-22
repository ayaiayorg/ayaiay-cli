# AyAiAy CLI

[![PyPI version](https://badge.fury.io/py/ayaiay.svg)](https://badge.fury.io/py/ayaiay)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

CLI and SDK for the [AyAiAy.org](https://ayaiay.org) AI agents marketplace - discover, install, and manage AI Agent Profiles, Instruction Packs, and Prompt Packs.

## Installation

```bash
pip install ayaiay
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

### Search for Packs

```bash
# Search by keyword
ayaiay search "code review"

# Filter by type
ayaiay search --type agent
ayaiay search --type instruction
ayaiay search --type prompt

# Filter by tags
ayaiay search --tag python --tag testing
```

### Install Packs

```bash
# Install latest version
ayaiay install acme/code-reviewer

# Install specific version
ayaiay install acme/code-reviewer@1.0.0

# Force reinstall
ayaiay install acme/code-reviewer --force
```

### Manage Installed Packs

```bash
# List installed packs
ayaiay list

# Show pack details
ayaiay show acme/code-reviewer

# Uninstall a pack
ayaiay uninstall acme/code-reviewer
```

### Validate Manifests

```bash
# Validate an ayaiay.yaml manifest
ayaiay validate ayaiay.yaml
ayaiay validate ./my-pack/ayaiay.yaml
```

### CLI Configuration

```bash
# Show current configuration and API status
ayaiay info
```

## SDK Usage

```python
from ayaiay import AyAiAyClient, validate_manifest

# Search for packs
with AyAiAyClient() as client:
    results = client.search_packs(query="code review", pack_type="agent")
    for pack in results.packs:
        print(f"{pack.full_name}: {pack.description}")

# Get pack details
with AyAiAyClient() as client:
    pack = client.get_pack("acme/code-reviewer")
    versions = client.get_pack_versions("acme/code-reviewer")

# Validate a manifest file
result = validate_manifest("ayaiay.yaml")
if result.is_valid:
    print(f"Valid manifest: {result.manifest.name}")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

## Configuration

Configuration is loaded from (in order of priority):

1. **Environment variables** (highest priority)
2. **Config file** (`~/.ayaiay/config.yaml`)
3. **Default values**

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AYAIAY_API_URL` | API base URL | `https://api.ayaiay.org` |
| `AYAIAY_REGISTRY_URL` | OCI registry URL | `ghcr.io/ayaiayorg` |
| `AYAIAY_INSTALL_DIR` | Pack installation directory | `~/.ayaiay/packs` |
| `AYAIAY_TOKEN` | Authentication token | - |

### Config File

```yaml
# ~/.ayaiay/config.yaml
api_base_url: https://api.ayaiay.org
registry_url: ghcr.io/ayaiayorg
install_dir: ~/.ayaiay/packs
cache_dir: ~/.ayaiay/cache
timeout: 30.0
```

## Creating Packs

To publish your own packs, create an `ayaiay.yaml` manifest in your repository:

```yaml
version: "1.0"
name: my-awesome-pack
description: An awesome AI pack for code review
author: Your Name
license: MIT
repository: https://github.com/you/my-awesome-pack
tags:
  - code-review
  - python

agents:
  - name: code-reviewer
    description: Reviews code for quality and best practices
    system_prompt: |
      You are an expert code reviewer. Analyze code for:
      - Best practices
      - Performance issues
      - Security vulnerabilities
    model: gpt-4
    tools:
      - read_file
      - write_file

instructions:
  - name: coding-standards
    description: Coding standards to follow
    content: |
      Follow PEP 8 for Python code.
      Use meaningful variable names.
      Write docstrings for all functions.

prompts:
  - name: review-request
    description: Template for requesting code review
    template: |
      Please review the following {language} code:

      ```{language}
      {code}
      ```

      Focus on: {focus_areas}
    variables:
      - language
      - code
      - focus_areas

dependencies:
  base-pack: "^1.0.0"
```

## Development

### Setup

```bash
git clone https://github.com/ayaiayorg/ayaiay-cli.git
cd ayaiay-cli
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
pytest --cov=ayaiay
```

### Code Quality

```bash
# Format code
black .
isort .

# Type checking
mypy .

# Linting
ruff check .
```

### Publishing to PyPI

This package uses GitHub Actions with [Trusted Publisher](https://docs.pypi.org/trusted-publishers/) (OIDC) for secure, tokenless publishing.

**Setup (one-time):**

1. Go to [PyPI](https://pypi.org) and create an account
2. Navigate to your account's "Publishing" settings
3. Add a new Trusted Publisher with:
   - Owner: `ayaiayorg`
   - Repository: `ayaiay-cli`
   - Workflow: `publish.yml`
   - Environment: `pypi`
4. Repeat for [TestPyPI](https://test.pypi.org) with environment: `testpypi`

**Publishing:**

- **Automatic:** Create a GitHub Release to publish to PyPI
- **Manual (TestPyPI):** Run the "Publish to PyPI" workflow manually, selecting `testpypi`
- **Manual (PyPI):** Run the workflow manually, selecting `pypi`

**Before releasing:**

1. Update the version in `pyproject.toml`
2. Commit and push changes
3. Create a GitHub Release with a tag matching the version (e.g., `v0.1.0`)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Links

- [AyAiAy.org](https://ayaiay.org) - Marketplace website
- [Documentation](https://github.com/ayaiayorg/ayaiay) - Full documentation
- [Issues](https://github.com/ayaiayorg/ayaiay-cli/issues) - Bug reports and feature requests
