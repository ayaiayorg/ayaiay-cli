# CLI Reference

This reference describes all available commands of the AyAiAy CLI.

## Global Options

- `--api-url`: Override the API base URL (equivalent to setting `AYAIAY_API_URL`).
- `--version`: Print the CLI version and exit.

Example:

```bash
ayaiay --api-url https://api.ayaiay.org info
```

## Commands

### `search`

Search for packs in the marketplace.

```bash
ayaiay search "code review"
ayaiay search --type agent
ayaiay search --tag python --tag testing
```

Options:
- `--type, -t`: Filter by type — `agent`, `instruction`, or `prompt`
- `--tag, -g`: Filter by tag (can be used multiple times)
- `--limit, -l`: Number of results per page
- `--page, -p`: Page number

---

### `install`

Install a pack from the marketplace.

```bash
ayaiay install acme/code-reviewer
ayaiay install acme/code-reviewer@1.0.0
ayaiay install acme/code-reviewer@latest
```

Options:
- `--force, -f`: Force reinstall even if already installed

---

### `uninstall`

Uninstall a pack.

```bash
ayaiay uninstall acme/code-reviewer
```

---

### `list`

List all installed packs.

```bash
ayaiay list
```

---

### `show`

Show details for a pack.

```bash
ayaiay show acme/code-reviewer
```

---

### `validate`

Validate an `ayaiay.yaml` manifest file.

`ayaiay validate` accepts both the flat format and the canonical spec-nested format
(`apiVersion/kind/metadata/spec`). Spec-nested manifests are automatically normalised
before validation, so you can validate any pack manifest regardless of format.

```bash
ayaiay validate ayaiay.yaml
ayaiay validate ./my-pack/ayaiay.yaml
```

Options:
- `--quiet, -q`: Only output errors (suppress warnings and success message)

---

### `info`

Show CLI configuration and API connectivity status.

```bash
ayaiay info
```

---

### `init`

Initialise an `ayaiay.json` lock file in the current (or specified) directory.

```bash
ayaiay init
ayaiay init --path /path/to/project
```

Options:
- `--path, -p`: Target directory for `ayaiay.json`

---

### `add`

Add a pack to `ayaiay.json` and install it.

```bash
ayaiay add acme/code-reviewer
ayaiay add acme/code-reviewer@1.0.0
```

Options:
- `--force, -f`: Force reinstall
- `--path, -p`: Target directory for `ayaiay.json`

---

### `remove`

Remove a pack from `ayaiay.json` and uninstall it.

```bash
ayaiay remove acme/code-reviewer
```

Options:
- `--path, -p`: Target directory for `ayaiay.json`

---

### `sync`

Synchronise installed packs with `ayaiay.json` (install missing, remove extra).

```bash
ayaiay sync
```

Options:
- `--path, -p`: Target directory for `ayaiay.json`

---

### `update`

Update one or all packs to their latest versions.

```bash
ayaiay update
ayaiay update acme/code-reviewer
```

Options:
- `--path, -p`: Target directory for `ayaiay.json`

---

### `init-pack`

Initialise a new pack interactively.

The wizard prompts for basic information (name, description, author, license,
repository, tags) and lets you choose which artifact types to include (agents,
instructions, prompts, skills). It then generates an `ayaiay.yaml` manifest in
spec-nested format.

```bash
ayaiay init-pack
ayaiay init-pack --path /path/to/new-pack
```

Options:
- `--path, -p`: Target directory for the new pack

---

### `init-skill`

Generate a GitHub Copilot Agent skill skeleton file.

```bash
ayaiay init-skill
ayaiay init-skill --name code-analyzer
ayaiay init-skill --name file-reader --path ./skills
ayaiay init-skill --name my-skill --output custom-name.md
```

Options:
- `--name, -n`: Skill name (prompted interactively if omitted)
- `--path, -p`: Target directory for the skill file (default: current directory)
- `--output, -o`: Output filename (default: `<skill-name>.md`)

Skills are Markdown files that define capabilities agents can perform. The
`init-skill` command creates a skeleton in the GitHub Copilot Agent skill format
with sections for function signature, parameters, implementation details, and
examples.

See: [GitHub Copilot Agent Skills Documentation](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)

---

## Pack Reference Format

Packs are referenced by `publisher/name`, optionally with a version specifier:

- `publisher/name`
- `publisher/name@version`
- `publisher/name@latest`

Examples:
- `acme/code-reviewer`
- `acme/code-reviewer@1.2.0`
- `acme/code-reviewer@latest`
