# Publishing and Installation Guide

## Current Status

✅ **The `ayaiay` package is published on PyPI.**

## Installation Options

You can install the package using one of these methods:

### Option 1: Install from PyPI (Recommended)

```bash
pip install ayaiay
```

### Option 2: Install from GitHub

Install directly from the GitHub repository:

```bash
pip install git+https://github.com/ayaiayorg/ayaiay-cli.git
```

Install a specific tagged version:

```bash
pip install git+https://github.com/ayaiayorg/ayaiay-cli.git@v1.1.0
```

### Option 3: Install from Source

Clone the repository and install locally:

```bash
git clone https://github.com/ayaiayorg/ayaiay-cli.git
cd ayaiay-cli
pip install -e .
```

For development with all dependencies:

```bash
pip install -e ".[dev]"
```

### Option 4: Install from Wheel (Manual Build)

If you have the source code:

```bash
pip install build
python -m build
pip install dist/ayaiay-*.whl
```

## Publishing to PyPI

This section is for maintainers who want to publish the package to PyPI.

### Prerequisites

1. **PyPI Account**: Create accounts on both [PyPI](https://pypi.org) and [TestPyPI](https://test.pypi.org)

2. **Trusted Publisher Setup** (Recommended - No tokens needed):

   a. Go to PyPI → Your Account → Publishing

   b. Add a new Trusted Publisher with:
   - Owner: `ayaiayorg`
   - Repository name: `ayaiay-cli`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`

   c. Repeat for TestPyPI with environment name: `testpypi`

3. **GitHub Repository Settings**:
   - Ensure the repository has the correct environments configured:
     - `pypi` (for production PyPI)
     - `testpypi` (for test PyPI)

### Publishing Process

#### Test Publishing (TestPyPI)

Always test on TestPyPI first:

1. Go to GitHub Actions → "Publish to PyPI" workflow
2. Click "Run workflow"
3. Select `testpypi` as the target
4. Click "Run workflow"

Verify the test installation:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ayaiay
```

#### Production Publishing (PyPI)

**Method 1: Automated Release (Recommended)**

1. Update version in `pyproject.toml` and `src/ayaiay/__init__.py`
2. Commit and push changes:
   ```bash
   git add pyproject.toml src/ayaiay/__init__.py
   git commit -m "Bump version to X.Y.Z"
   git push
   ```
3. Create a GitHub Release:
   - Go to Releases → "Draft a new release"
   - Create a new tag: `vX.Y.Z` (e.g., `v1.0.0`)
   - Title: `Release vX.Y.Z`
   - Description: Release notes
   - Click "Publish release"
4. The workflow will automatically publish to PyPI

**Method 2: Manual Workflow Trigger**

1. Go to GitHub Actions → "Publish to PyPI" workflow
2. Click "Run workflow"
3. Select `pypi` as the target
4. Click "Run workflow"

### Version Management

Update the version in **both** files before publishing:

1. **`pyproject.toml`** - Update the version field:
   ```toml
   [project]
   name = "ayaiay"
   version = "X.Y.Z"  # Update this line
   description = "CLI and SDK for the AyAiAy.org AI agents marketplace"
   ```

2. **`src/ayaiay/__init__.py`** - Update the version constant:
   ```python
   __version__ = "X.Y.Z"  # Update this line
   ```

> **Note**: Both versions must match. Consider adding a pre-commit check or CI validation to ensure version consistency.

### Pre-Release Checklist

Before publishing a new version:

- [ ] Update version number in `pyproject.toml` and `src/ayaiay/__init__.py`
- [ ] Update CHANGELOG.md (if exists) with release notes
- [ ] Run tests: `pytest`
- [ ] Run linters: `black .`, `isort .`, `mypy .`, `ruff check .`
- [ ] Build locally: `python -m build`
- [ ] Test local installation: `pip install dist/*.whl`
- [ ] Test CLI: `ayaiay --version`, `ayaiay --help`
- [ ] Test on TestPyPI first
- [ ] Create Git tag: `git tag vX.Y.Z`
- [ ] Push tag: `git push origin vX.Y.Z`
- [ ] Create GitHub Release
- [ ] Verify PyPI publication
- [ ] Test installation from PyPI: `pip install ayaiay`

### Troubleshooting

**Issue**: Trusted Publisher authentication fails

**Solution**:
- Verify the Trusted Publisher is configured correctly on PyPI
- Check that the workflow name and environment name match exactly
- Ensure the workflow is running from the correct branch (usually `main`)

**Issue**: Version already exists on PyPI

**Solution**:
- PyPI doesn't allow overwriting existing versions
- Bump the version number and publish again
- Delete the version on PyPI if it's broken (must be done within 24 hours)

**Issue**: Build fails

**Solution**:
- Ensure all dependencies are specified correctly in `pyproject.toml`
- Check that `setuptools>=61.0` is available
- Verify the package structure follows Python packaging standards

## Current PyPI Installation

Confirm that installation from PyPI works:

```bash
pip install ayaiay
```

Users can install the package directly from PyPI.
