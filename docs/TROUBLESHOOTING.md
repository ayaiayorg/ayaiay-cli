# Fehlerbehebung

## API nicht erreichbar

Symptome:
- `Unable to connect to the API`
- `API Status: Unreachable`

Lösungen:
- Internetverbindung prüfen
- API-URL prüfen: `ayaiay info`
- API-URL setzen: `--api-url` oder `AYAIAY_API_URL`

## Authentifizierung schlägt fehl

Symptome:
- `Authentication required or invalid token`

Lösungen:
- Token setzen: `AYAIAY_TOKEN`
- Token in ~/.ayaiay/config.yaml prüfen

## Pack nicht gefunden

Symptome:
- `Pack not found` oder `Version not found`

Lösungen:
- Schreibweise prüfen
- `ayaiay search` verwenden
- Verfügbare Versionen mit `ayaiay show` prüfen

## ayaiay.json fehlt

Symptome:
- `No lock file found`

Lösungen:
- `ayaiay init` ausführen
- Alternativ `--path` verwenden

## Validierung schlägt fehl

Symptome:
- `Manifest validation failed`

Lösungen:
- `ayaiay.yaml` gemäß Schema prüfen
- Pflichtfelder (`name`, `version`, `content` etc.) ergänzen

## Weitere Hilfe

- Issues: https://github.com/ayaiayorg/ayaiay-cli/issues
- Marketplace: https://ayaiay.org
