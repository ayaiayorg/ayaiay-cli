# Packs und Manifest (ayaiay.yaml)

## Pack-Typen

Ein Pack ist eine Sammlung von:

- **Agents** (`agent`)
- **Instructions** (`instruction`)
- **Prompts** (`prompt`)
- **Skills** (`skill`)

## Pack-Referenzen

Format:

- `publisher/name`
- `publisher/name@version`
- `publisher/name@latest`

Beispiele:

- `acme/code-reviewer`
- `acme/code-reviewer@1.0.0`

## Manifest-Datei

Ein Pack wird durch eine ayaiay.yaml beschrieben. Felder (Schema v1.0):

- `version`: Manifest-Schema (Standard: `1.0`)
- `name`: Pack-Name
- `description`: Beschreibung
- `author`: Autor
- `license`: Lizenz
- `repository`: Repository-URL
- `tags`: Liste von Tags
- `agents`: Liste von Agenten-Definitionen
- `instructions`: Liste von Instruktions-Definitionen
- `prompts`: Liste von Prompt-Definitionen
- `skills`: Liste von Skill-Definitionen
- `dependencies`: Abhängigkeiten (`name: version`)
- `metadata`: Freie Metadaten

### Agent-Definition

- `name`: Agent-Name
- `description`: Kurzbeschreibung
- `system_prompt`: System-Prompt
- `model`: bevorzugtes Modell
- `tools`: benötigte Tools

### Instruction-Definition

- `name`
- `description`
- `content`

### Prompt-Definition

- `name`
- `description`
- `template`
- `variables`

### Skill-Definition

- `name`: Skill-Name
- `description`: Kurzbeschreibung
- `content`: Skill-Implementierung/Inhalt
- `parameters`: Liste von Parametern

## Beispiel-Manifest

```yaml
version: "1.0"
name: my-awesome-pack
description: Ein tolles Pack
author: Your Name
license: MIT
repository: https://github.com/you/my-awesome-pack
tags:
  - code-review
  - python

agents:
  - name: code-reviewer
    description: Reviews code for quality
    system_prompt: |
      You are an expert code reviewer.
    model: gpt-4
    tools:
      - read_file
      - write_file

instructions:
  - name: coding-standards
    description: Coding standards to follow
    content: |
      Follow PEP 8 for Python code.

prompts:
  - name: review-request
    description: Template for requesting code review
    template: |
      Please review the following {language} code:
    variables:
      - language

skills:
  - name: code-analyzer
    description: Analyzes code structure
    content: |
      Analyze code for patterns and complexity.
    parameters:
      - file_path
      - language

dependencies:
  base-pack: "^1.0.0"
```

## Validierung

```bash
ayaiay validate ayaiay.yaml
```

## Plattform-Integration

Bei der Installation eines Packs kopiert AyAiAy die Dateien automatisch in die richtigen Zielverzeichnisse basierend auf den erkannten AI-Plattformen im Projekt.

### Unterstützte Plattformen

| Plattform | Zielverzeichnis | Erkennung |
| --- | --- | --- |
| GitHub Copilot | `.github/` | `.github/` Ordner |
| Claude | `.claude/` | `.claude/` Ordner oder `CLAUDE.md` |
| Cursor | `.cursor/` | `.cursorrules` Datei oder `.cursor/` Ordner |
| Windsurf | `.windsurf/` | `.windsurfrules` oder `.windsurf/` Ordner |
| Aider | `.aider/` | `.aider.conf.yml` oder `.aider/` Ordner |

### Pack-Quellverzeichnisse

Packs können folgende Verzeichnisse enthalten, die automatisch in die Plattform-Zielverzeichnisse kopiert werden:

- `agents/` → `<platform>/agents/`
- `prompts/` → `<platform>/prompts/`
- `instructions/` → `<platform>/` (direkt im Plattform-Root)
- `skills/` → `<platform>/skills/`
- `tools/` → `<platform>/tools/`
- `workflows/` → `<platform>/workflows/`

### Beispiel

Ein Pack mit folgender Struktur:

```
my-pack/
├── agents/
│   └── code-reviewer.md
├── instructions/
│   └── copilot-instructions.md
└── ayaiay.yaml
```

Wird in einem Projekt mit `.github/` und `.claude/` Ordnern so installiert:

```
project/
├── .github/
│   ├── agents/
│   │   └── code-reviewer.md
│   └── copilot-instructions.md
├── .claude/
│   ├── agents/
│   │   └── code-reviewer.md
│   └── copilot-instructions.md
└── ayaiay.json
```

### Standard-Plattform

Wenn keine Plattform erkannt wird, aber `ayaiay.json` existiert, wird standardmäßig **GitHub Copilot** (`.github/`) als Ziel verwendet.
