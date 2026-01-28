# ayaiay.json (Lock-File)

ayaiay.json dient als Lock-File für installierte Packs in einem Projekt – ähnlich zu package-lock.json oder composer.lock.

## Erstellung

```bash
ayaiay init
```

## Pakete hinzufügen/entfernen

```bash
ayaiay add acme/code-reviewer
ayaiay remove acme/code-reviewer
```

## Sync und Updates

```bash
ayaiay sync
ayaiay update
ayaiay update acme/code-reviewer
```

## Struktur

Beispiel:

```json
{
  "version": "1.0",
  "packages": {
    "acme/code-reviewer": {
      "name": "acme/code-reviewer",
      "version": "1.2.0",
      "installed_at": "2024-01-15T10:30:00+00:00",
      "digest": "sha256:abc123...",
      "dependencies": {}
    }
  },
  "updated_at": "2024-01-15T10:30:00+00:00"
}
```

## Hinweise

- Einträge werden automatisch nach Installationen/Updates aktualisiert.
- `installed_at` und `updated_at` sind ISO-8601 Zeitstempel.
- `digest` ist optional und kommt aus der Registry.
