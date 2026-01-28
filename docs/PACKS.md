# Packs und Manifest (ayaiay.yaml)

## Pack-Typen

Ein Pack ist eine Sammlung von:

- **Agents** (`agent`)
- **Instructions** (`instruction`)
- **Prompts** (`prompt`)

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

dependencies:
  base-pack: "^1.0.0"
```

## Validierung

```bash
ayaiay validate ayaiay.yaml
```
