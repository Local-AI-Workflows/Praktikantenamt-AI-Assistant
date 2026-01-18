# Phase 2: Workday Calculator Refactoring & n8n Integration

## Übersicht

Dieses Dokument beschreibt die geplante Refaktorisierung des Workday Calculators zur Nutzung externer Python-Libraries für Feiertag- und PLZ-Auflösung, sowie die theoretische Integration in den n8n Workflow.

---

## 1. Aktuelle Architektur (Status Quo)

### Workday Calculator Komponenten

```text
mcp-tools/workday-calculator/
├── workday_calculator/
│   ├── core/
│   │   ├── calculator.py        # Hauptlogik: Arbeitstage berechnen
│   │   ├── holiday_provider.py  # Feiertage via `holidays` library
│   │   └── location_resolver.py # PLZ → Bundesland Auflösung
│   ├── data/
│   │   ├── schemas.py           # Pydantic Models (Bundesland, Request/Result)
│   │   └── bundesland_data.py   # MANUELL: PLZ_RANGES, STATE_NAME_MAPPING
│   ├── api.py                   # FastAPI Endpoints für n8n
│   └── cli.py                   # CLI Tool
```

### Problem: Manuelle Datenpflege

Die aktuelle Implementierung enthält manuell gepflegte Mappings in `bundesland_data.py`:

1. **PLZ_RANGES**: 2-stellige PLZ-Präfixe → Bundesland (ungenau bei Grenzgebieten)
2. **STATE_NAME_MAPPING**: Staatsnamen → Bundesland Enum
3. **BUNDESLAND_NAMES**: Bundesland Enum → Vollständiger Name

**Nachteile:**
- PLZ-Präfix-Mapping ist ungenau (z.B. `21` → NI, obwohl einige 21xxx PLZs zu HH gehören)
- Keine automatische Aktualisierung bei Verwaltungsgebietsänderungen
- Wartungsaufwand bei neuen PLZ-Bereichen

---

## 2. Geplante Library-Integration

### 2.1 `plz-to-bundesland` für PLZ-Auflösung

**Library:** [plz-to-bundesland](https://pypi.org/project/plz-to-bundesland/)

```python
from plz_to_bundesland import get_bundesland

bundesland = get_bundesland("20095")  # → "Hamburg"
bundesland = get_bundesland("21073")  # → "Hamburg" (nicht "Niedersachsen"!)
```

**Vorteile:**
- Vollständige 5-stellige PLZ-Datenbank
- Präzise Auflösung auch für Grenzgebiete
- Keine manuelle Datenpflege nötig

**Fehlerbehandlung (Human-in-the-Loop):**
```python
def resolve_plz(plz: str) -> str:
    """
    Löst PLZ zu Bundesland auf.

    Raises:
        PLZResolutionError: Wenn PLZ nicht gefunden wird.
        → Eskalation an Human-in-the-Loop erforderlich.
    """
    result = get_bundesland(plz)
    if result is None:
        raise PLZResolutionError(
            f"PLZ {plz} konnte nicht aufgelöst werden. "
            "Bitte manuell prüfen und Bundesland angeben."
        )
    return result
```

### 2.2 Dual-Library Ansatz für Feiertage

**Strategie:** Beide Libraries parallel nutzen, `feiertage-de` als primäre Quelle, mit Validierung gegen `holidays`.

| Library | Rolle | Link |
|---------|-------|------|
| `feiertage-de` | **Primär** - Deutsche Feiertage | [PyPI](https://pypi.org/project/feiertage-de/) |
| `holidays` | **Sekundär** - Validierung & Fallback | [PyPI](https://pypi.org/project/holidays/) |

**Vergleich:**

| Aspekt | `feiertage-de` (primär) | `holidays` (sekundär) |
|--------|-------------------------|----------------------|
| API | `feiertage.Holidays("HH")` | `holidays.Germany(subdiv="HH")` |
| Fokus | Nur Deutschland | International |
| Format | Liste von Dicts | Dict-like Objekt |
| Sprache | Nur Deutsch | Mehrsprachig |

**Implementierung mit Soft-Reporting:**

```python
import feiertage
import holidays
import logging
from datetime import date
from typing import Set

logger = logging.getLogger(__name__)

class DualHolidayProvider:
    """
    Verwendet feiertage-de als primäre Quelle, validiert gegen holidays library.
    Diskrepanzen werden geloggt aber nicht als Fehler behandelt.
    """

    def get_holidays(self, bundesland: str, year: int) -> Set[date]:
        """
        Holt Feiertage von beiden Libraries und meldet Unterschiede.

        Args:
            bundesland: Bundesland-Kürzel (z.B. "HH", "BY")
            year: Jahr

        Returns:
            Set von Feiertags-Daten (primär von feiertage-de)
        """
        # Primäre Quelle: feiertage-de
        primary_holidays = self._get_feiertage_de(bundesland, year)

        # Sekundäre Quelle: holidays library
        secondary_holidays = self._get_holidays_lib(bundesland, year)

        # Soft-Reporting: Diskrepanzen loggen
        self._report_discrepancies(
            bundesland, year, primary_holidays, secondary_holidays
        )

        return primary_holidays

    def _get_feiertage_de(self, bundesland: str, year: int) -> Set[date]:
        """Feiertage von feiertage-de Library."""
        result = feiertage.Holidays(bundesland, year=year).holidays
        return {h['date'] for h in result}

    def _get_holidays_lib(self, bundesland: str, year: int) -> Set[date]:
        """Feiertage von holidays Library."""
        de_holidays = holidays.Germany(subdiv=bundesland, years=year)
        return set(de_holidays.keys())

    def _report_discrepancies(
        self,
        bundesland: str,
        year: int,
        primary: Set[date],
        secondary: Set[date]
    ) -> None:
        """
        Loggt Unterschiede zwischen beiden Libraries.
        SOFT REPORTING: Warnung, kein Fehler - Workflow läuft weiter.
        """
        only_in_primary = primary - secondary
        only_in_secondary = secondary - primary

        if only_in_primary or only_in_secondary:
            logger.warning(
                f"Feiertag-Diskrepanz für {bundesland} {year}:\n"
                f"  Nur in feiertage-de: {sorted(only_in_primary)}\n"
                f"  Nur in holidays:     {sorted(only_in_secondary)}"
            )
            # Optional: Metrics/Telemetry für spätere Analyse
            # metrics.record_holiday_discrepancy(bundesland, year, ...)
        else:
            logger.debug(f"Feiertage für {bundesland} {year}: Libraries stimmen überein ✓")
```

**Vorteile des Dual-Library Ansatzes:**

1. **Validierung**: Fehler in einer Library werden durch die andere erkannt
2. **Soft-Fail**: Diskrepanzen werden geloggt, blockieren aber nicht den Workflow
3. **Audit-Trail**: Log-Einträge ermöglichen nachträgliche Analyse
4. **Zukunftssicher**: Bei Deprecation einer Library ist Fallback bereits implementiert

**Typische Diskrepanz-Szenarien:**

| Szenario | Ursache | Aktion |
|----------|---------|--------|
| Reformationstag (31.10.) | Nur in bestimmten Bundesländern | Prüfen ob Bundesland korrekt |
| Buß- und Bettag | Nur in Sachsen | Normal - bundeslandspezifisch |
| Neue Feiertage | Library-Update ausstehend | Library aktualisieren |
| Datumsabweichung | Bug in einer Library | Issue bei GitHub melden |

---

## 3. Refactored Architecture

### 3.1 Neue Dependency-Struktur

```toml
# pyproject.toml Änderungen
dependencies = [
    "holidays>=0.40",        # Sekundär: Feiertag-Validierung
    "feiertage-de",          # NEU: Primäre Feiertag-Quelle
    "plz-to-bundesland",     # NEU: Präzise PLZ-Auflösung
    # ... rest bleibt gleich
]
```

### 3.2 Refactored LocationResolver

```python
# location_resolver.py (geplante Änderungen)

from plz_to_bundesland import get_bundesland as plz_lookup
from workday_calculator.data.schemas import Bundesland, LocationResult

class PLZResolutionError(Exception):
    """Raised when PLZ cannot be resolved - requires human intervention."""
    pass

class LocationResolver:
    def _resolve_from_plz(self, plz: str) -> Optional[Bundesland]:
        """
        Resolve Bundesland from PLZ using external library.

        Raises:
            PLZResolutionError: PLZ not found in database.
        """
        bundesland_name = plz_lookup(plz)

        if bundesland_name is None:
            # CRITICAL: Stop processing and report to human
            raise PLZResolutionError(
                f"PLZ '{plz}' nicht in Datenbank gefunden. "
                f"Workflow wird angehalten - manuelle Prüfung erforderlich."
            )

        # Map full name to Bundesland enum
        return self._name_to_bundesland(bundesland_name)
```

### 3.3 Zu löschende Dateien/Code

Nach der Migration kann entfernt werden:

```python
# bundesland_data.py - diese Mappings werden obsolet:
PLZ_RANGES: dict[str, Bundesland] = { ... }  # → plz-to-bundesland übernimmt
# BUNDESLAND_NAMES und STATE_NAME_MAPPING bleiben für UI/Logging
```

---

## 4. Workflow-Integration (n8n + Human-in-the-Loop)

### 4.1 Gesamtarchitektur

```text
┌─────────────────────────────────────────────────────────────────┐
│                        E-Mail Eingang                           │
│                    (IMAP Trigger in n8n)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   1. Email Categorization                        │
│                   (ai-agents/categorization)                     │
│                                                                 │
│  Kategorien:                                                    │
│  • contract_submission → Weiter zu Schritt 2                    │
│  • international_office_question → Auto-Reply Template          │
│  • internship_postponement → Auto-Reply Template                │
│  • uncategorized → In Warteschlange für manuelles Review        │
└─────────────────────────────────────────────────────────────────┘
                                │
                   [nur contract_submission]
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   2. Contract Data Extraction                    │
│                   (ai-agents/contract-validator)                 │
│                                                                 │
│  Extrahierte Felder:                                            │
│  • student_name, matrikelnummer                                 │
│  • company_name, company_address (inkl. PLZ)                    │
│  • start_date, end_date                                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   3. Workday Calculation                         │
│                   (mcp-tools/workday-calculator)                 │
│                                                                 │
│  Input:                                                         │
│  • start_date, end_date (aus Vertrag)                          │
│  • PLZ (aus Firmenadresse)                                      │
│                                                                 │
│  Processing:                                                    │
│  1. PLZ → Bundesland (via plz-to-bundesland)                   │
│     ├─ Success → Weiter                                        │
│     └─ Failure → STOP + Human Review ⚠️                        │
│  2. Feiertage laden (via holidays library)                      │
│  3. Arbeitstage berechnen                                       │
│                                                                 │
│  Output:                                                        │
│  • working_days: int                                            │
│  • is_valid: working_days >= 95                                 │
│  • holidays_in_range: List[Holiday]                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   4. Validation Decision                         │
│                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐│
│  │  working_days >= 95 │    │      working_days < 95          ││
│  │       VALID         │    │         INVALID                 ││
│  └──────────┬──────────┘    └────────────┬────────────────────┘│
│             │                            │                      │
│             ▼                            ▼                      │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐│
│  │  Bestätigungs-Email │    │  Ablehnungs-Email mit Details:  ││
│  │  an Student senden  │    │  - Aktuelle Arbeitstage: X      ││
│  │                     │    │  - Minimum erforderlich: 95     ││
│  │  Template: formal   │    │  - Feiertage im Zeitraum        ││
│  └─────────────────────┘    │  - Empfehlung: Zeitraum ändern  ││
│                             └─────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Human-in-the-Loop Trigger Points

An folgenden Stellen wird der automatische Workflow angehalten und ein Mensch muss eingreifen:

| Trigger | Beschreibung | Aktion für Sachbearbeiter |
|---------|--------------|---------------------------|
| **PLZ nicht gefunden** | `plz-to-bundesland` kann PLZ nicht auflösen | Bundesland manuell angeben oder PLZ korrigieren |
| **Kategorie `uncategorized`** | Email konnte nicht klassifiziert werden | Email manuell kategorisieren oder individuell beantworten |
| **Extraktion unvollständig** | LLM konnte nicht alle Vertragsfelder extrahieren | Fehlende Daten manuell ergänzen |
| **Firma auf Blacklist** | Bekanntermaßen ungültige Praktikumsstelle | Entscheidung über Ablehnung/Ausnahme |
| **Confidence < 0.8** | Niedrige Konfidenz bei Kategorisierung/Extraktion | Ergebnis verifizieren |

### 4.3 n8n Workflow Nodes (Konzept)

```yaml
# n8n Workflow Struktur (Pseudocode)

nodes:
  - name: "IMAP Trigger"
    type: "n8n-nodes-base.imapTrigger"
    credentials: praktikantenamt-mailbox

  - name: "Categorize Email"
    type: "n8n-nodes-base.httpRequest"
    endpoint: "http://localhost:8001/categorize"  # categorization API

  - name: "Route by Category"
    type: "n8n-nodes-base.switch"
    conditions:
      - contract_submission → "Extract Contract"
      - international_office_question → "IO Response"
      - internship_postponement → "Postponement Response"
      - uncategorized → "Human Review Queue"

  - name: "Extract Contract"
    type: "n8n-nodes-base.httpRequest"
    endpoint: "http://localhost:8002/extract"  # contract-validator API

  - name: "Calculate Workdays"
    type: "n8n-nodes-base.httpRequest"
    endpoint: "http://localhost:8000/calculate"  # workday-calculator API
    body: |
      {
        "start_date": "{{ $json.start_date }}",
        "end_date": "{{ $json.end_date }}",
        "location": { "postal_code": "{{ $json.company_plz }}" }
      }
    errorBehavior: "stopWorkflow"  # Bei PLZ-Fehler → Human Review

  - name: "Validate Duration"
    type: "n8n-nodes-base.if"
    condition: "{{ $json.working_days >= 95 }}"

  - name: "Generate Response"
    type: "n8n-nodes-base.httpRequest"
    endpoint: "http://localhost:8003/generate"  # response-generator API
```

---

## 5. API Endpoints (Zusammenfassung)

| Service | Port | Endpoint | Beschreibung |
|---------|------|----------|--------------|
| Workday Calculator | 8000 | `POST /calculate` | Arbeitstage berechnen |
| Workday Calculator | 8000 | `GET /holidays/{year}/{bundesland}` | Feiertage abrufen |
| Categorization | 8001 | `POST /categorize` | Email kategorisieren |
| Contract Validator | 8002 | `POST /extract` | Vertragsdaten extrahieren |
| Response Generator | 8003 | `POST /generate` | Antwort generieren |

---

## 6. Error Response Format (für n8n)

Alle APIs folgen einem einheitlichen Error-Format für Human-in-the-Loop Integration:

```json
{
  "success": false,
  "error": {
    "code": "PLZ_RESOLUTION_FAILED",
    "message": "PLZ '99999' konnte nicht aufgelöst werden",
    "requires_human_review": true,
    "context": {
      "input_plz": "99999",
      "suggestion": "Bitte Bundesland manuell angeben"
    }
  },
  "original_request": { ... }
}
```

In n8n wird bei `requires_human_review: true` der Workflow angehalten und ein Eintrag in der Human Review Queue erstellt.

---

## 7. Implementierung: Nächste Schritte

### 7.1 Dependencies

- [ ] `plz-to-bundesland` hinzufügen in pyproject.toml
- [ ] `feiertage-de` hinzufügen in pyproject.toml

### 7.2 PLZ-Auflösung

- [ ] LocationResolver refactoren: `plz-to-bundesland` statt PLZ_RANGES
- [ ] PLZResolutionError: Mit n8n-kompatiblem Response Format
- [ ] bundesland_data.py aufräumen: PLZ_RANGES entfernen

### 7.3 Dual-Holiday-Provider

- [ ] DualHolidayProvider implementieren: Wrapper für beide Libraries
- [ ] Soft-Reporting: Logger für Diskrepanzen zwischen Libraries
- [ ] Bestehenden HolidayProvider ersetzen in calculator.py

### 7.4 Testing & Validation

- [ ] Unit Tests: PLZ-Grenzfälle (z.B. 21073 Hamburg vs. Niedersachsen)
- [ ] Feiertag-Vergleichstest: Alle 16 Bundesländer für 2025-2027
- [ ] Integration Tests: API Endpoints mit Fehler-Szenarien

### 7.5 Dokumentation & API

- [ ] OpenAPI Schema für n8n Integration aktualisieren
- [ ] Logging-Format: Strukturiertes JSON für Monitoring

---

## Appendix: Komponenten-Übersicht (aus Phase 1)

### A. Workday Calculator (MCP Tool)

**Pfad:** `mcp-tools/workday-calculator/`

**Commands:**
```bash
workday-calc calculate -s 2026-03-01 -e 2026-08-31 --plz 20095
workday-calc holidays --year 2026 --bundesland BY
```

### B. Contract Validator

**Pfad:** `ai-agents/contract-validator/`

**Commands:**
```bash
contract-tester generate -n 50 --seed 42
contract-tester test -p prompts/v1_extraction_baseline.txt
```

### C. Response Generator

**Pfad:** `ai-agents/response-generator/`

**Commands:**
```bash
response-gen generate -e test_data/dummy_emails.json --tone both
response-gen evaluate -t templates -d test_data/
```

---

## Status

| Komponente                   | Status      |
|------------------------------|-------------|
| Categorization Prompt Tester | ✅ Fertig    |
| Workday Calculator           | ✅ Fertig    |
| Contract Validator           | ✅ Fertig    |
| Response Generator           | ✅ Fertig    |
| PLZ Library Integration      | ⏳ Geplant   |
| n8n Workflow                 | ⏳ Geplant   |
