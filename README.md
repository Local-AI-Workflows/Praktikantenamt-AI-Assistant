# Praktikantenamt AI-Assistant

An AI-powered email management system for a German university internship office (Praktikantenamt). Automates email categorization, contract validation, and response generation using n8n workflows and LLM-based agents.

## Projektübersicht

Entwicklung eines KI-gestützten E-Mail-Assistenten zur Automatisierung und Optimierung der E-Mail-Verwaltung für das Praktikantenamt einer Hochschule für angewandte Wissenschaften.

### Projektziel

Aufbau eines automatisierten Workflows mit KI-Unterstützung zur intelligenten Bearbeitung eingehender E-Mails, automatischen Vertragsprüfung und Verwaltung von Praktikantendaten.

### Technologie-Stack

- **Workflow-Orchestrierung**: n8n
- **E-Mail-Trigger**: n8n Email-Integration
- **KI**: Prompt Engineering, Context Engineering, Agent-basierte Systeme
- **LLM Inference**: Ollama (configurable endpoint)
- **MCP**: Model Context Protocol
- **Datenverwaltung**: MCP Tools für File Storage / DB
- **Containerisierung**: Docker mit SSE Transport
- **Benachrichtigungen**: Mattermost (optional)
- **OCR**: Für Vertragsdatenextraktion

---

## Use Cases

### Use Case 1: E-Mail-Kategorisierung und Weiterleitung

**Priorität**: Hoch (Hauptanwendungsfall)

**Beschreibung**:
Automatische Kategorisierung eingehender E-Mails und Weiterleitung an die zuständigen Stellen.

**Kategorien** (zu definieren):
- Vertragsabgaben → Weiterleitung an BFF (Frau Friedrich)
- Auslandsamtsfragen → Weiterleitung an Mevius
- Praktikumsverschiebungen → Weiterleitung an Prüfungsamt
- Weitere Kategorien nach Bedarf

**Funktionale Anforderungen**:
- KI-gestützte Klassifizierung eingehender E-Mails
- Automatische Weiterleitung basierend auf Kategorie
- Erkennung von E-Mail-Inhalten und Anhängen
- Validierung der Kategorisierung

**Workflow**:
1. E-Mail trifft im Postfach ein
2. n8n triggert Workflow
3. KI analysiert E-Mail-Inhalt
4. Kategorie wird zugewiesen (in das Postfach verschieben)
5. E-Mail wird weitergeleitet

---

### Use Case 2: Automatische Vertragsprüfung und -analyse

**Priorität**: Mittel

**Beschreibung**:
Automatische Validierung und Datenextraktion aus eingereichten Praktikumsverträgen.

**Funktionale Anforderungen**:

**Vertragserkennung**:
- Erkennung von E-Mails mit Vertragsanhängen
- Unterstützte Formate: PDF, gescannte Dokumente

**Datenextraktion** (via OCR):
- Name des Studierenden
- Matrikelnummer
- Firmenname
- Praktikumsdauer / Arbeitstage
- Praktikumszeitraum

**Validierung**:
- Berechnung der Arbeitstage (mindestens 95 Tage erforderlich)
- Abgleich mit Firmenliste (Whitelist/Blacklist)
- Vollständigkeitsprüfung der Vertragsdaten

**Praktikumsprofil**:
- Automatische Erstellung eines Praktikumsprofils
- Speicherung relevanter Daten
- Verwaltung via MCP Tools

**Workflow**:
1. Vertrag wird per E-Mail eingereicht
2. Parallel: Weiterleitung an Frau Friedrich (BFF)
3. Email wird entsprechend kategorisiert
4. Async Processing dieses Postfachs
5. OCR-Verarbeitung des Vertrags
6. Datenextraktion
7. Validierung der Daten
8. Erstellung Praktikumsprofil
9. Optional: Mattermost-Benachrichtigung bei Problemen

---

### Use Case 3: Standardantworten und Antwortvorschläge

**Priorität**: Niedrig

**Beschreibung**:
KI-generierte Antwortvorschläge für häufige Anfragen mit Human-in-the-Loop-Ansatz.

**Funktionale Anforderungen**:
- Analyse der E-Mail-Anfrage
- Generierung kontextbezogener Antwortvorschläge
- Präsentation der Vorschläge an Sachbearbeiter
- Möglichkeit zur Anpassung vor dem Versand
- Lernen aus genehmigten Antworten

**Human-in-the-Loop**:
- Review-Prozess für vorgeschlagene Antworten
- Freigabe durch Sachbearbeiter (Oliver)
- Feedback-Mechanismus zur Verbesserung

---

### Use Case 4: Verwaltung und Administration

**Priorität**: Mittel

**Beschreibung**:
Zentrale Verwaltung aller Praktikantendaten und System-Administration.

**Funktionale Anforderungen**:
- Verwaltung aller Praktikanten via File Storage (MCP Tools)
- Dashboard zur Übersicht
- Suchfunktion für Praktikanten und Verträge
- Statistiken und Reports
- Systemkonfiguration

**Mögliche Schnittstellen**:
- Web-Interface (n8n)
- Mattermost-Integration
- Admin-Dashboard

---

## Technische Anforderungen

### KI/ML-Komponenten

- **Prompt Engineering**: Optimierung der KI-Prompts für präzise Kategorisierung
- **Context Engineering**: Bereitstellung relevanter Kontextinformationen über das Praktikantenamt
- ?**Agent-basierte Architektur**: Modulare Agents für verschiedene Aufgaben?
- **Datengenerierung**: Erstellung von Testdaten für Entwicklung und Validierung

### Infrastruktur

- **E-Mail-Setup**:
  - Dummy-Postfach für Weiterleitungen
  - n8n E-Mail-Trigger-Konfiguration

- **Datenbank/Storage**:
  - File Storage für Praktikantendaten
  - MCP Tools Integration
  - Firmenliste (Whitelist/Blacklist)?

- **Workflow-Engine**:
  - n8n-Installation und -Konfiguration
  - Workflow-Definitionen für alle Use Cases

### MCP (Model Context Protocol) Integration

**Mögliche Anwendungsfälle**:
- Verwaltung von Praktikantendaten im File Storage
- Zugriff auf strukturierte Firmenlisten
- Verwaltung von Templates und Standardantworten
- Historische Datenanalyse

---

## Offene Fragen und TODOs

### Infrastruktur
- [x] Repository anlegen ✅ 2025-12-04
- [x] Dummy-Postfach einrichten
- [x] n8n-Umgebung aufsetzen

### Daten
- [ ] Beispielverträge sammeln/erstellen
- [x] Kategorien für E-Mails definieren

### Entwicklung
- [ ] Use Cases detailliert ausformulieren
- [ ] n8n Email-Trigger konfigurieren
- [ ] OCR-Lösung evaluieren und integrieren
- [ ] MCP Tools für File Storage implementieren

### Konzeption
- [ ] Human-in-the-Loop-Konzept ausarbeiten
- [ ] Praktikantenamt-Kontext dokumentieren

---

## Projektstruktur

```
praktikantenamt-ai-assistant/
├── ai-agents/
│   ├── categorization/              # ✅ Email-Kategorisierung Prompt Testing
│   │   ├── prompt_tester/           # CLI Tool (prompt-tester)
│   │   ├── prompts/                 # Prompt Templates (v1-v4)
│   │   ├── test_data/               # 20 Dummy-Emails mit Ground Truth
│   │   └── results/                 # Vergleichsergebnisse
│   │
│   ├── contract-validator/          # ✅ Vertragsdaten-Extraktion Testing
│   │   ├── contract_validator/      # CLI Tool (contract-tester)
│   │   ├── prompts/                 # Extraktions-Prompts
│   │   └── test_data/               # 50 Dummy-Verträge, Firmenlisten
│   │
│   ├── response-generator/          # ✅ Antwort-Generierung
│   │   ├── response_generator/      # CLI Tool (response-gen)
│   │   └── templates/               # 8 Templates (4 Kategorien × 2 Töne)
│   │
│   └── email-workflow-validator/    # ✅ End-to-End Workflow Testing
│       ├── workflow_validator/      # CLI Tool
│       └── results/                 # Validierungsergebnisse
│
├── mcp-tools/
│   └── workday-calculator/          # ✅ Arbeitstage-Berechnung (MCP Tool)
│       ├── workday_calculator/      # Package
│       │   ├── api.py               # FastAPI REST Endpoints
│       │   ├── cli.py               # CLI Tool (workday-calc)
│       │   └── mcp_server.py        # MCP Server (stdio/SSE)
│       ├── Dockerfile               # Container Support
│       ├── docker-compose.yml       # MCP SSE + REST API Services
│       └── tests/                   # Unit Tests + MCP Evaluation
│
├── n8n-workflows/                   # Workflow Definitionen (Placeholder)
│   ├── email-categorization.json
│   ├── contract-validation.json
│   └── response-generation.json
│
├── docs/
│   ├── requirements.md
│   └── PHASE2_IMPLEMENTATION.md     # Phase 2 Planungsdokument
│
└── CLAUDE.md                        # Claude Code Instruktionen
```

---

## Implementierungs-Status

### Phase 1 - Setup ✅

- [x] Repository angelegt
- [x] Dummy-Postfach eingerichtet
- [x] n8n-Umgebung aufgesetzt
- [x] Kategorien für E-Mails definiert

### Phase 2 - AI Agents & MCP Tools (aktuell)

**Fertiggestellt:**

- [x] Categorization Prompt Tester - CLI Tool für Prompt-Testing
- [x] Contract Validator - Vertragsdaten-Extraktion Testing
- [x] Response Generator - Template-basierte Antworten
- [x] Workday Calculator MCP Tool - Arbeitstage-Berechnung
- [x] Email Workflow Validator - End-to-End Testing

**Offene Issues ([GitHub](../../issues)):**

- [ ] #8 MCP: Workday Calculator mit Quantifizierung
- [ ] #9 MCP: Company Lookup mit Quantifizierung
- [ ] #10 Workflow: Vertragsprüfung mit OCR und MCPs
- [ ] #11 Workflow: Automatische Weiterleitung Mevius
- [ ] #12 Workflow: Allgemeine Antwortvorschläge in Drafts
- [ ] #13 Prompt: Automatische Antwortvorschläge & RAG

### Phase 3-5 (geplant)

3. **Vertragsprüfung**: n8n Workflow mit OCR Integration
4. **Antwortgenerierung**: Human-in-the-Loop Prozess
5. **Administration**: Dashboard und MCP File Storage

---

## MCP Tool Setup

### Workday Calculator

Das MCP Tool berechnet Arbeitstage unter Berücksichtigung bundeslandspezifischer Feiertage.

#### CLI Usage

```bash
cd mcp-tools/workday-calculator
pip install -e .

# Arbeitstage berechnen
workday-calc calculate -s 2026-03-01 -e 2026-08-31 --plz 20095

# Feiertage auflisten
workday-calc holidays --year 2026 --bundesland BY
```

#### Docker Deployment (SSE Transport)

```bash
cd mcp-tools/workday-calculator

# MCP SSE Server starten (für Remote-Zugriff)
docker-compose up -d workday-mcp

# REST API starten (für n8n)
docker-compose --profile api up -d
```

#### Claude Desktop Integration

Für **lokale Installation** (stdio):

```json
{
  "mcpServers": {
    "workday-calculator": {
      "command": "python",
      "args": ["-m", "workday_calculator.mcp_server"],
      "cwd": "C:\\path\\to\\mcp-tools\\workday-calculator"
    }
  }
}
```

Für **Docker/Remote** (SSE):

```json
{
  "mcpServers": {
    "workday-calculator": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Siehe [Workday Calculator README](mcp-tools/workday-calculator/README.md) für Details.

---
