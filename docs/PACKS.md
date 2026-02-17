# Packs and the Manifest (ayaiay.yaml)

## Pack Types

A pack is a collection of one or more of the following artifact types:

- **Agents** (`agent`) — AI agents with system prompts and tool access
- **Instructions** (`instruction`) — Reusable instruction sets that guide agent behaviour
- **Prompts** (`prompt`) — Template prompts with variables for common tasks
- **Skills** (`skill`) — Specific capabilities agents can invoke

## Pack References

Packs are identified by `publisher/name`, optionally with a version specifier:

- `publisher/name`
- `publisher/name@version`
- `publisher/name@latest`

Examples:

- `acme/code-reviewer`
- `acme/code-reviewer@1.0.0`

## Manifest File

Every pack is described by an `ayaiay.yaml` manifest. The canonical format is
**spec-nested** (`apiVersion/kind/metadata/spec`):

```yaml
apiVersion: v1
kind: Pack
metadata:
  name: <pack-name>            # required — lowercase alphanumeric + hyphens
  version: 1.0.0
  description: <description>
  author: <author>
  license: MIT
  repository: https://github.com/you/my-pack
  tags:
    - tag-one
    - tag-two
spec:
  agents: [...]
  instructions: [...]
  prompts: [...]
  skillCategories: [...]
  skills: [...]
  dependencies:
    <pack-name>: "<version-constraint>"
```

> **Note**: `ayaiay validate` also accepts the legacy flat format
> (`name/agents/skills` at root level) for backwards compatibility.

### Field Reference

#### `metadata`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Pack name — `^[a-z0-9][a-z0-9-]*[a-z0-9]$` |
| `version` | string | no | Semantic version (default: `1.0`) |
| `description` | string | no | Short description (max 500 chars) |
| `author` | string | no | Author name |
| `license` | string | no | SPDX license identifier |
| `repository` | string | no | Repository URL |
| `tags` | string[] | no | Discovery tags (max 10, `^[a-z0-9-]+$`) |

#### `spec.agents`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Agent name |
| `description` | string | no | Short description |
| `system_prompt` | string | no | System prompt |
| `model` | string | no | Preferred model |
| `tools` | string[] | no | Required tools |

#### `spec.instructions`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Instruction name |
| `description` | string | no | Short description |
| `content` | string | no* | Inline content |

*`content` is required in flat format; use `path` to reference a file in spec-nested format.

#### `spec.prompts`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Prompt name |
| `description` | string | no | Short description |
| `template` | string | no* | Inline template |
| `variables` | string[] | no | Template variables |

#### `spec.skillCategories`

Groups skills into named categories displayed in the category sidebar on the pack detail page.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | yes | Unique identifier (`^[a-z0-9-]+$`) |
| `label` | string | yes | Full display label |
| `shortLabel` | string | no | Abbreviated label for sidebar |
| `description` | string | no | Category description |

#### `spec.skills`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Skill name |
| `display_name` | string | no | Human-readable name |
| `description` | string | no | Short description |
| `path` | string | no | Path to skill `.md` file (spec-nested format) |
| `content` | string | no | Inline skill content (flat/inline format) |
| `category` | string | no | Category slug — must match a `skillCategories` entry |
| `parameters` | string[] | no | Skill parameters |
| `tags` | string[] | no | Searchable tags |

> At least one of `path` or `content` should be provided per skill.

---

## Example Manifest

```yaml
apiVersion: v1
kind: Pack
metadata:
  name: my-awesome-pack
  version: 1.0.0
  description: A code quality pack for Python projects
  author: Your Name
  license: MIT
  repository: https://github.com/you/my-awesome-pack
  tags:
    - code-review
    - python

spec:
  agents:
    - name: code-reviewer
      description: Reviews code for quality and best practices
      system_prompt: |
        You are an expert code reviewer. Analyze code for best practices,
        performance issues, and security vulnerabilities.
      model: claude-opus-4-5
      tools:
        - read_file
        - write_file

  instructions:
    - name: coding-standards
      description: Coding standards to follow
      path: ./instructions/coding-standards.md

  prompts:
    - name: review-request
      description: Template for requesting code review
      path: ./prompts/review-request.md
      variables:
        - language
        - code
        - focus_areas

  skillCategories:
    - slug: code-quality
      label: Code Quality
      shortLabel: Quality
      description: Skills for improving and maintaining code quality.
    - slug: security
      label: Security
      description: Skills for vulnerability assessment and secure coding.

  skills:
    - name: code-analyzer
      description: Analyzes code structure and patterns
      category: code-quality
      path: ./skills/code-analyzer/SKILL.md
      tags:
        - refactoring
        - complexity
    - name: security-review
      description: Identifies security vulnerabilities and suggests fixes
      category: security
      path: ./skills/security-review/SKILL.md
      tags:
        - security
        - owasp

  dependencies:
    base-pack: "^1.0.0"
```

---

## Skill Registration

When a pack is installed, AyAiAy reads the `skills` entries from the manifest.
Each skill references a Markdown file via `path`. These files follow the
GitHub Copilot Agent skill format and are copied to platform-specific directories.

**Benefits of manifest-based skill management:**
- **Centralised definition** — Skills are declared in `ayaiay.yaml`
- **Cross-platform** — Skills are deployed to all detected AI platforms
- **Version-controlled** — Skills are part of the versioned pack manifest
- **Categorised** — `skillCategories` powers the category navigation UI

**Example of a generated skill file (`skills/code-analyzer/SKILL.md`):**

```markdown
# code-analyzer

Analyzes code structure

## Overview

This skill provides functionality for code analysis.

## Function Signature

```typescript
function code_analyzer(file_path, language): any
```

## Parameters

- **file_path** (required)
- **language** (required)

## Implementation

Analyze code for patterns and complexity.
```

---

## Validation

```bash
ayaiay validate ayaiay.yaml
```

Both spec-nested and flat format manifests are accepted.

---

## Platform Integration

When a pack is installed, AyAiAy automatically copies files to the correct
target directories based on the detected AI platforms in the project.

### Supported Platforms

| Platform | Target Directory | Detection |
| --- | --- | --- |
| GitHub Copilot | `.github/` | `.github/` folder present |
| Claude | `.claude/` | `.claude/` folder or `CLAUDE.md` present |
| Cursor | `.cursor/` | `.cursorrules` file or `.cursor/` folder |
| Windsurf | `.windsurf/` | `.windsurfrules` or `.windsurf/` folder |
| Aider | `.aider/` | `.aider.conf.yml` or `.aider/` folder |

### Pack Source Directories

Packs can contain the following directories, which are automatically copied
to the platform target directories:

- `agents/` → `<platform>/agents/`
- `prompts/` → `<platform>/prompts/`
- `instructions/` → `<platform>/` (directly in platform root)
- `skills/` → `<platform>/skills/`
- `tools/` → `<platform>/tools/`
- `workflows/` → `<platform>/workflows/`

### Example

A pack with the following structure:

```
my-pack/
├── agents/
│   └── code-reviewer.md
├── instructions/
│   └── copilot-instructions.md
├── skills/
│   └── code-analyzer/
│       └── SKILL.md
└── ayaiay.yaml
```

Installed in a project with both `.github/` and `.claude/` folders:

```
project/
├── .github/
│   ├── agents/
│   │   └── code-reviewer.md
│   ├── skills/
│   │   └── code-analyzer/
│   │       └── SKILL.md
│   └── copilot-instructions.md
├── .claude/
│   ├── agents/
│   │   └── code-reviewer.md
│   ├── skills/
│   │   └── code-analyzer/
│   │       └── SKILL.md
│   └── copilot-instructions.md
└── ayaiay.json
```

### Default Platform

If no platform is detected but `ayaiay.json` exists, **GitHub Copilot**
(`.github/`) is used as the default target.
