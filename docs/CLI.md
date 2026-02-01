# CLI-Referenz

Diese Referenz beschreibt alle verfügbaren Befehle der AyAiAy CLI.

## Globale Optionen

- `--api-url`: Überschreibt die API-Basis-URL (entspricht `AYAIAY_API_URL`).
- `--version`: Gibt die Version aus.

Beispiel:

```bash
ayaiay --api-url https://api.ayaiay.org info
```

## Befehle

### `search`
Sucht Packs im Marketplace.

```bash
ayaiay search "code review"
ayaiay search --type agent
ayaiay search --tag python --tag testing
```

Optionen:
- `--type, -t`: `agent`, `instruction`, `prompt`
- `--tag, -g`: Mehrfach verwendbar
- `--limit, -l`: Anzahl Ergebnisse pro Seite
- `--page, -p`: Seitennummer

### `install`
Installiert ein Pack aus dem Marketplace.

```bash
ayaiay install acme/code-reviewer
ayaiay install acme/code-reviewer@1.0.0
ayaiay install acme/code-reviewer@latest
```

Optionen:
- `--force, -f`: Erzwingt eine Neuinstallation

### `uninstall`
Deinstalliert ein Pack.

```bash
ayaiay uninstall acme/code-reviewer
```

### `list`
Listet installierte Packs.

```bash
ayaiay list
```

### `show`
Zeigt Details zu einem Pack.

```bash
ayaiay show acme/code-reviewer
```

### `validate`
Validiert eine ayaiay.yaml Manifest-Datei.

```bash
ayaiay validate ayaiay.yaml
ayaiay validate ./my-pack/ayaiay.yaml
```

Optionen:
- `--quiet, -q`: Nur Fehlerausgabe

### `info`
Zeigt Konfiguration und API-Status.

```bash
ayaiay info
```

### `init`
Initialisiert ein ayaiay.json Lock-File.

```bash
ayaiay init
ayaiay init --path /path/to/project
```

Optionen:
- `--path, -p`: Zielordner für ayaiay.json

### `add`
Fügt ein Pack zur ayaiay.json hinzu und installiert es.

```bash
ayaiay add acme/code-reviewer
ayaiay add acme/code-reviewer@1.0.0
```

Optionen:
- `--force, -f`: Erzwingt Neuinstallation
- `--path, -p`: Zielordner für ayaiay.json

### `remove`
Entfernt ein Pack aus ayaiay.json und deinstalliert es.

```bash
ayaiay remove acme/code-reviewer
```

Optionen:
- `--path, -p`: Zielordner für ayaiay.json

### `sync`
Gleicht installierte Packs mit ayaiay.json ab.

```bash
ayaiay sync
```

Optionen:
- `--path, -p`: Zielordner für ayaiay.json

### `update`
Aktualisiert Packs auf die neuesten Versionen.

```bash
ayaiay update
ayaiay update acme/code-reviewer
```

Optionen:
- `--path, -p`: Zielordner für ayaiay.json

### `init-pack`
Initialisiert ein neues Pack mit interaktivem Assistenten.

```bash
ayaiay init-pack
ayaiay init-pack --path /path/to/new-pack
```

Optionen:
- `--path, -p`: Zielordner für das Pack

### `init-skill`
Generiert ein GitHub Copilot Agent Skill Skeleton.

```bash
ayaiay init-skill
ayaiay init-skill --name code-analyzer
ayaiay init-skill --name file-reader --path ./skills
ayaiay init-skill --name my-skill --output custom-name.md
```

Optionen:
- `--name, -n`: Skill-Name (interaktiv wenn nicht angegeben)
- `--path, -p`: Zielordner für die Skill-Datei (Standard: aktuelles Verzeichnis)
- `--output, -o`: Ausgabe-Dateiname (Standard: `<skill-name>.md`)

Skills sind spezielle Dateien, die bestimmte Fähigkeiten oder Aktionen definieren, die Agenten ausführen können. Der `init-skill` Befehl erstellt eine Skeleton-Datei im GitHub Copilot Agent Skill Format mit Abschnitten für Funktionssignatur, Parameter, Implementierungsdetails und Beispiele.

Siehe: [GitHub Copilot Agent Skills Documentation](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)

## Referenz-Format

- `publisher/name`
- `publisher/name@version`
- `publisher/name@latest`

Beispiele:
- `acme/code-reviewer`
- `acme/code-reviewer@1.2.0`
