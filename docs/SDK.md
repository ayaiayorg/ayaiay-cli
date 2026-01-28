# SDK-Nutzung

Die AyAiAy CLI bringt eine kleine Python-SDK mit. Damit kannst du Packs suchen, Details abrufen oder Manifeste validieren.

## Client

```python
from ayaiay import AyAiAyClient

with AyAiAyClient() as client:
    results = client.search_packs(query="code review", pack_type="agent")
    for pack in results.packs:
        print(pack.full_name, pack.latest_version)
```

## Pack-Details und Versionen

```python
from ayaiay import AyAiAyClient

with AyAiAyClient() as client:
    pack = client.get_pack("acme/code-reviewer")
    versions = client.get_pack_versions("acme/code-reviewer")
```

## Manifest-Validierung

```python
from ayaiay import validate_manifest

result = validate_manifest("ayaiay.yaml")
if result.is_valid:
    print("OK")
else:
    print(result.errors)
```

## Fehlerklassen

- `AyAiAyError`: Basisfehler
- `APIError`: Fehlerhafte API-Antwort
- `NotFoundError`: Ressource nicht gefunden
- `AuthenticationError`: Token fehlt oder ungültig
