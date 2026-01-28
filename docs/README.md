# AyAiAy CLI Dokumentation

Willkommen in der lokalen Dokumentation der AyAiAy CLI. Hier findest du alle relevanten Informationen zu Installation, Nutzung, Konfiguration und Entwicklung – gebündelt an einem Ort.

## Schnellstart

- Installation und erste Schritte: [docs/README.md](README.md#schnellstart)
- CLI-Befehle im Detail: [docs/CLI.md](CLI.md)
- Konfiguration und Umgebungsvariablen: [docs/CONFIGURATION.md](CONFIGURATION.md)
- Pack- und Manifest-Format: [docs/PACKS.md](PACKS.md)
- ayaiay.json Lock-File: [docs/LOCKFILE.md](LOCKFILE.md)
- SDK-Nutzung: [docs/SDK.md](SDK.md)
- Fehlerbehebung: [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Agent-Workflow (GitHub Actions): [docs/AGENT_WORKFLOW.md](AGENT_WORKFLOW.md)

## Schnellstart

### Installation

> Hinweis: Das Paket ist aktuell noch nicht auf PyPI veröffentlicht.

```bash
pip install git+https://github.com/ayaiayorg/ayaiay-cli.git
```

Sobald verfügbar:

```bash
pip install ayaiay
```

### Erste Schritte

```bash
# Packs suchen
ayaiay search "code review"

# Pack installieren
ayaiay install acme/code-reviewer

# Installierte Packs anzeigen
ayaiay list

# Pack-Details anzeigen
ayaiay show acme/code-reviewer
```

### Paketmanagement mit ayaiay.json

```bash
# Lock-File initialisieren
ayaiay init

# Paket hinzufügen und installieren
ayaiay add acme/code-reviewer

# Abgleich mit ayaiay.json
ayaiay sync
```

## Konzepte

- **Packs**: Sammlungen von Agenten, Instruktionen oder Prompts, veröffentlicht im AyAiAy Marketplace.
- **Manifest**: Die Datei ayaiay.yaml beschreibt Inhalt, Metadaten und Abhängigkeiten eines Packs.
- **Lock-File**: ayaiay.json hält fest, welche Packs in einem Projekt installiert sind und in welcher Version.

## Hilfe & Support

- Issues und Feature-Requests: https://github.com/ayaiayorg/ayaiay-cli/issues
- Marketplace: https://ayaiay.org
