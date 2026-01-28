# Konfiguration

Die AyAiAy CLI lädt ihre Konfiguration in folgender Priorität (höchste zuerst):

1. Umgebungsvariablen
2. Konfigurationsdatei in ~/.ayaiay/config.yaml
3. Standardwerte

## Umgebungsvariablen

| Variable | Beschreibung | Standard |
| --- | --- | --- |
| `AYAIAY_API_URL` | API-Basis-URL | `https://api.ayaiay.org` |
| `AYAIAY_REGISTRY_URL` | OCI-Registry URL | `ghcr.io/ayaiayorg` |
| `AYAIAY_INSTALL_DIR` | Installationspfad für Packs | `~/.ayaiay/packs` |
| `AYAIAY_CACHE_DIR` | Cache-Verzeichnis | `~/.ayaiay/cache` |
| `AYAIAY_TIMEOUT` | Request-Timeout (Sek.) | `30.0` |
| `AYAIAY_TOKEN` | Auth-Token (Bearer) | — |

## Konfigurationsdatei

Standardpfad: ~/.ayaiay/config.yaml

Beispiel:

```yaml
api_base_url: https://api.ayaiay.org
registry_url: ghcr.io/ayaiayorg
install_dir: ~/.ayaiay/packs
cache_dir: ~/.ayaiay/cache
timeout: 30.0
# token: "<your-token>"
```

## Hinweise

- `api_base_url` muss mit http:// oder https:// beginnen.
- Verzeichnisse werden automatisch erstellt, falls sie fehlen.
- Das Token wird als Bearer-Token im Authorization-Header verwendet.
