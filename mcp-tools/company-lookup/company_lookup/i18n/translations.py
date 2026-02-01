"""Translation strings for English and German."""

from typing import Dict

# Type alias for translation dictionaries
TranslationDict = Dict[str, str]

TRANSLATIONS: Dict[str, TranslationDict] = {
    "en": {
        # =============================================================================
        # MCP Server - Tool names and descriptions
        # =============================================================================
        "mcp.server_name": "Company Lookup",

        # lookup_company tool
        "mcp.lookup_company.description": "Look up a company in the whitelist/blacklist database",
        "mcp.lookup_company.details": (
            "Use this tool to check if a company is approved (whitelisted) or "
            "blocked (blacklisted) for internships. The tool uses fuzzy matching "
            "to find similar company names even with typos or variations."
        ),
        "mcp.lookup_company.param.company_name": "The name of the company to look up",
        "mcp.lookup_company.param.threshold": (
            "Minimum similarity score (0-100) for fuzzy matching. "
            "Higher values require closer matches. Default: 80"
        ),
        "mcp.lookup_company.param.max_results": (
            "Maximum number of matching companies to return. Default: 5"
        ),

        # check_company_approved tool
        "mcp.check_approved.description": "Quick check if a company is approved for internships",
        "mcp.check_approved.details": (
            "This is a simplified lookup that returns a boolean result "
            "indicating whether the company is on the whitelist"
        ),
        "mcp.check_approved.param.company_name": "The name of the company to check",
        "mcp.check_approved.param.threshold": "Minimum similarity score for matching. Default: 80",

        # check_company_blocked tool
        "mcp.check_blocked.description": "Quick check if a company is blocked from internships",
        "mcp.check_blocked.details": (
            "This is a simplified lookup that returns a boolean result "
            "indicating whether the company is on the blacklist"
        ),
        "mcp.check_blocked.param.company_name": "The name of the company to check",
        "mcp.check_blocked.param.threshold": "Minimum similarity score for matching. Default: 80",

        # list_companies tool
        "mcp.list_companies.description": "List companies in the database",
        "mcp.list_companies.param.status": (
            'Filter by status - "all", "whitelist", or "blacklist". Default: "all"'
        ),

        # get_company_stats tool
        "mcp.stats.description": "Get statistics about the company database",

        # batch_lookup tool
        "mcp.batch.description": "Look up multiple companies at once",
        "mcp.batch.details": (
            "Useful for validating a list of companies from a contract "
            "or processing multiple inquiries"
        ),
        "mcp.batch.param.company_names": "List of company names to look up",
        "mcp.batch.param.threshold": "Minimum similarity score for matching. Default: 80",

        # MCP server messages
        "mcp.error.excel_not_set": (
            "COMPANY_LOOKUP_EXCEL_FILE environment variable not set. "
            "Please set it to the path of your company list Excel file."
        ),
        "mcp.error.lookup_failed": "Lookup error: {error}",
        "mcp.error.check_approved_failed": "Check approved error: {error}",
        "mcp.error.check_blocked_failed": "Check blocked error: {error}",
        "mcp.error.list_failed": "List companies error: {error}",
        "mcp.error.stats_failed": "Get stats error: {error}",
        "mcp.error.batch_failed": "Batch lookup error: {error}",
        "mcp.info.initialized": "Initialized lookup engine with: {file}",
        "mcp.info.starting": "Starting MCP server with transport: {transport}",
        "mcp.info.sse_endpoint": "SSE endpoint: http://{host}:{port}/sse",
        "mcp.warning.excel_not_set": (
            "COMPANY_LOOKUP_EXCEL_FILE not set. The server will fail on first lookup."
        ),

        # =============================================================================
        # CLI - Commands and options
        # =============================================================================
        "cli.group.description": (
            "Company Lookup - Whitelist/Blacklist lookup with fuzzy matching.\n\n"
            "A tool for checking company names against whitelist and blacklist "
            "databases with intelligent fuzzy matching support."
        ),

        # lookup command
        "cli.lookup.description": "Look up a company name in the whitelist/blacklist.",
        "cli.lookup.option.excel": "Path to the Excel file with company lists.",
        "cli.lookup.option.query": "Company name to look up.",
        "cli.lookup.option.threshold": "Fuzzy matching threshold (0-100). Default: 80.",
        "cli.lookup.option.max_results": "Maximum number of results. Default: 5.",
        "cli.lookup.option.partial": "Include partial matches below threshold.",
        "cli.lookup.option.output": "Output file path (auto-generates if not specified).",
        "cli.lookup.option.format": "Output format. Default: console.",
        "cli.lookup.option.config": "Path to configuration file.",
        "cli.lookup.option.verbose": "Enable verbose output.",

        # list command
        "cli.list.description": "List all companies in the database.",
        "cli.list.option.status": "Filter by status. Default: all.",

        # stats command
        "cli.stats.description": "Show statistics about the company lists.",

        # create-template command
        "cli.template.description": "Create a template Excel file with the expected structure.",
        "cli.template.option.output": "Output file path. Default: company_template.xlsx.",
        "cli.template.success": "Template created: {path}",
        "cli.template.info": "Edit the file to add your company lists.",

        # batch command
        "cli.batch.description": "Perform batch lookup from a file with company names.",
        "cli.batch.option.input": "Input file with company names (one per line).",
        "cli.batch.info.processing": "Processing {count} company names...",
        "cli.batch.success.processed": "Processed {count} companies",

        # serve command
        "cli.serve.description": "Start the REST API server.",
        "cli.serve.option.host": "API server host. Default: 0.0.0.0.",
        "cli.serve.option.port": "API server port. Default: 8000.",
        "cli.serve.info.starting": "Starting API server at http://{host}:{port}",
        "cli.serve.info.excel": "Using Excel file: {file}",
        "cli.serve.error.uvicorn": "uvicorn not installed. Run: pip install uvicorn",

        # CLI messages
        "cli.success.exported": "Results exported to: {path}",
        "cli.success.companies_exported": "Companies exported to: {path}",
        "cli.error.file_not_found": "File not found: {error}",
        "cli.error.invalid_input": "Invalid input: {error}",
        "cli.error.generic": "Error: {error}",

        # =============================================================================
        # API - Descriptions and messages
        # =============================================================================
        "api.title": "Company Lookup API",
        "api.description": "REST API for company whitelist/blacklist lookup with fuzzy matching",

        # Endpoints
        "api.root.description": "API information endpoint",
        "api.health.description": "Health check endpoint",
        "api.lookup.description": (
            "Look up a company name in the whitelist/blacklist. "
            "Returns the company status (whitelisted, blacklisted, or unknown) "
            "along with confidence score and matching details."
        ),
        "api.batch.description": (
            "Look up multiple company names at once. Returns aggregated results for all companies."
        ),
        "api.list_all.description": "List all companies in the database",
        "api.list_whitelist.description": "List all whitelisted companies",
        "api.list_blacklist.description": "List all blacklisted companies",
        "api.stats.description": "Get statistics about the company lists",
        "api.upload.description": (
            "Upload an Excel file with company lists. "
            "The file should have 'Whitelist' and 'Blacklist' sheets with a 'Company Name' column."
        ),
        "api.reload.description": "Reload company data from the Excel file",

        # API messages
        "api.error.engine_not_initialized": (
            "Engine not initialized. Upload an Excel file first or set COMPANY_LOOKUP_EXCEL_FILE."
        ),
        "api.error.invalid_file_format": "Invalid file format. Expected .xlsx, .xls, or .xlsm",
        "api.error.process_failed": "Failed to process file: {error}",
        "api.error.reload_failed": "Failed to reload data: {error}",
        "api.success.upload": "File uploaded and processed successfully",
        "api.success.reload": "Data reloaded successfully",

        # =============================================================================
        # Formatter - Output labels
        # =============================================================================
        "fmt.panel.title": "Company Lookup Result",
        "fmt.query": "Query",
        "fmt.status": "Status",
        "fmt.confidence": "Confidence",
        "fmt.match.title": "Best Match",
        "fmt.matches.title": "Other Matches",
        "fmt.company": "Company",
        "fmt.score": "Score",
        "fmt.match_type": "Match Type",
        "fmt.exact_match": "Exact Match",
        "fmt.notes": "Notes",
        "fmt.field": "Field",
        "fmt.value": "Value",
        "fmt.company_name": "Company Name",
        "fmt.category": "Category",
        "fmt.stats.title": "Company List Statistics",
        "fmt.stats.total": "Total Companies",
        "fmt.stats.whitelisted": "Whitelisted",
        "fmt.stats.blacklisted": "Blacklisted",
        "fmt.stats.categories": "Categories",
        "fmt.stats.last_updated": "Last Updated",
        "fmt.stats.source_file": "Source File",
        "fmt.metric": "Metric",
        "fmt.companies_title": "Companies ({filter})",

        # =============================================================================
        # Lookup Engine - Warnings and messages
        # =============================================================================
        "engine.warning.no_matches": "No matches found above threshold",
        "engine.warning.near_threshold": "Match score is near threshold - verify manually",
        "engine.warning.conflicting": "Both whitelist and blacklist matches found - review required",
        "engine.warning.multiple_close": "Multiple close matches found - verify selection",
        "engine.warning.fuzzy_match": "Fuzzy match: '{query}' matched to '{matched}'",
        "engine.error.not_initialized": "Lookup engine not initialized. Call initialize() first.",
        "engine.error.no_excel_path": "No Excel file path provided",
        "engine.error.no_excel_configured": "No Excel file path configured",
        "engine.info.initialized": "Lookup engine initialized successfully",
        "engine.info.added_company": "Added company: {name} ({status})",

        # =============================================================================
        # Excel Reader - Messages
        # =============================================================================
        "excel.info.loading": "Loading company lists from: {path}",
        "excel.info.loaded": "Loaded {count} companies ({whitelist} whitelisted, {blacklist} blacklisted)",
        "excel.info.template_created": "Created template Excel file: {path}",
        "excel.warning.sheet_not_found": "{sheet_type} sheet '{name}' not found",
        "excel.warning.duplicate": "Duplicate company found: {name}",

        # =============================================================================
        # Status labels
        # =============================================================================
        "status.whitelisted": "Whitelisted",
        "status.blacklisted": "Blacklisted",
        "status.unknown": "Unknown",
        "status.all": "All",
    },

    "de": {
        # =============================================================================
        # MCP Server - Tool names and descriptions
        # =============================================================================
        "mcp.server_name": "Firmensuche",

        # lookup_company tool
        "mcp.lookup_company.description": "Eine Firma in der Whitelist/Blacklist-Datenbank suchen",
        "mcp.lookup_company.details": (
            "Verwenden Sie dieses Tool, um zu prüfen, ob eine Firma für Praktika "
            "zugelassen (Whitelist) oder gesperrt (Blacklist) ist. Das Tool verwendet "
            "Fuzzy-Matching, um ähnliche Firmennamen auch bei Tippfehlern oder Variationen zu finden."
        ),
        "mcp.lookup_company.param.company_name": "Der Name der zu suchenden Firma",
        "mcp.lookup_company.param.threshold": (
            "Mindestähnlichkeitswert (0-100) für Fuzzy-Matching. "
            "Höhere Werte erfordern genauere Übereinstimmungen. Standard: 80"
        ),
        "mcp.lookup_company.param.max_results": (
            "Maximale Anzahl der zurückzugebenden Treffer. Standard: 5"
        ),

        # check_company_approved tool
        "mcp.check_approved.description": "Schnellprüfung, ob eine Firma für Praktika zugelassen ist",
        "mcp.check_approved.details": (
            "Dies ist eine vereinfachte Suche, die ein boolesches Ergebnis zurückgibt, "
            "das anzeigt, ob die Firma auf der Whitelist steht"
        ),
        "mcp.check_approved.param.company_name": "Der Name der zu prüfenden Firma",
        "mcp.check_approved.param.threshold": "Mindestähnlichkeitswert für den Abgleich. Standard: 80",

        # check_company_blocked tool
        "mcp.check_blocked.description": "Schnellprüfung, ob eine Firma für Praktika gesperrt ist",
        "mcp.check_blocked.details": (
            "Dies ist eine vereinfachte Suche, die ein boolesches Ergebnis zurückgibt, "
            "das anzeigt, ob die Firma auf der Blacklist steht"
        ),
        "mcp.check_blocked.param.company_name": "Der Name der zu prüfenden Firma",
        "mcp.check_blocked.param.threshold": "Mindestähnlichkeitswert für den Abgleich. Standard: 80",

        # list_companies tool
        "mcp.list_companies.description": "Firmen in der Datenbank auflisten",
        "mcp.list_companies.param.status": (
            'Nach Status filtern - "all", "whitelist" oder "blacklist". Standard: "all"'
        ),

        # get_company_stats tool
        "mcp.stats.description": "Statistiken über die Firmendatenbank abrufen",

        # batch_lookup tool
        "mcp.batch.description": "Mehrere Firmen auf einmal suchen",
        "mcp.batch.details": (
            "Nützlich für die Validierung einer Liste von Firmen aus einem Vertrag "
            "oder die Bearbeitung mehrerer Anfragen"
        ),
        "mcp.batch.param.company_names": "Liste der zu suchenden Firmennamen",
        "mcp.batch.param.threshold": "Mindestähnlichkeitswert für den Abgleich. Standard: 80",

        # MCP server messages
        "mcp.error.excel_not_set": (
            "Umgebungsvariable COMPANY_LOOKUP_EXCEL_FILE nicht gesetzt. "
            "Bitte setzen Sie sie auf den Pfad Ihrer Firmenlisten-Excel-Datei."
        ),
        "mcp.error.lookup_failed": "Suchfehler: {error}",
        "mcp.error.check_approved_failed": "Fehler bei Genehmigungsprüfung: {error}",
        "mcp.error.check_blocked_failed": "Fehler bei Sperrungsprüfung: {error}",
        "mcp.error.list_failed": "Fehler beim Auflisten der Firmen: {error}",
        "mcp.error.stats_failed": "Fehler beim Abrufen der Statistiken: {error}",
        "mcp.error.batch_failed": "Fehler bei der Stapelsuche: {error}",
        "mcp.info.initialized": "Suchmaschine initialisiert mit: {file}",
        "mcp.info.starting": "MCP-Server wird gestartet mit Transport: {transport}",
        "mcp.info.sse_endpoint": "SSE-Endpunkt: http://{host}:{port}/sse",
        "mcp.warning.excel_not_set": (
            "COMPANY_LOOKUP_EXCEL_FILE nicht gesetzt. Der Server schlägt bei der ersten Suche fehl."
        ),

        # =============================================================================
        # CLI - Commands and options
        # =============================================================================
        "cli.group.description": (
            "Firmensuche - Whitelist/Blacklist-Suche mit Fuzzy-Matching.\n\n"
            "Ein Werkzeug zur Überprüfung von Firmennamen gegen Whitelist- und Blacklist-"
            "Datenbanken mit intelligenter Fuzzy-Matching-Unterstützung."
        ),

        # lookup command
        "cli.lookup.description": "Einen Firmennamen in der Whitelist/Blacklist suchen.",
        "cli.lookup.option.excel": "Pfad zur Excel-Datei mit den Firmenlisten.",
        "cli.lookup.option.query": "Zu suchender Firmenname.",
        "cli.lookup.option.threshold": "Fuzzy-Matching-Schwellenwert (0-100). Standard: 80.",
        "cli.lookup.option.max_results": "Maximale Anzahl der Ergebnisse. Standard: 5.",
        "cli.lookup.option.partial": "Teiltreffer unterhalb des Schwellenwerts einbeziehen.",
        "cli.lookup.option.output": "Ausgabedateipfad (wird automatisch generiert, falls nicht angegeben).",
        "cli.lookup.option.format": "Ausgabeformat. Standard: console.",
        "cli.lookup.option.config": "Pfad zur Konfigurationsdatei.",
        "cli.lookup.option.verbose": "Ausführliche Ausgabe aktivieren.",

        # list command
        "cli.list.description": "Alle Firmen in der Datenbank auflisten.",
        "cli.list.option.status": "Nach Status filtern. Standard: all.",

        # stats command
        "cli.stats.description": "Statistiken über die Firmenlisten anzeigen.",

        # create-template command
        "cli.template.description": "Eine Excel-Vorlagendatei mit der erwarteten Struktur erstellen.",
        "cli.template.option.output": "Ausgabedateipfad. Standard: company_template.xlsx.",
        "cli.template.success": "Vorlage erstellt: {path}",
        "cli.template.info": "Bearbeiten Sie die Datei, um Ihre Firmenlisten hinzuzufügen.",

        # batch command
        "cli.batch.description": "Stapelsuche aus einer Datei mit Firmennamen durchführen.",
        "cli.batch.option.input": "Eingabedatei mit Firmennamen (einer pro Zeile).",
        "cli.batch.info.processing": "{count} Firmennamen werden verarbeitet...",
        "cli.batch.success.processed": "{count} Firmen verarbeitet",

        # serve command
        "cli.serve.description": "Den REST-API-Server starten.",
        "cli.serve.option.host": "API-Server-Host. Standard: 0.0.0.0.",
        "cli.serve.option.port": "API-Server-Port. Standard: 8000.",
        "cli.serve.info.starting": "API-Server wird gestartet unter http://{host}:{port}",
        "cli.serve.info.excel": "Verwendete Excel-Datei: {file}",
        "cli.serve.error.uvicorn": "uvicorn nicht installiert. Führen Sie aus: pip install uvicorn",

        # CLI messages
        "cli.success.exported": "Ergebnisse exportiert nach: {path}",
        "cli.success.companies_exported": "Firmen exportiert nach: {path}",
        "cli.error.file_not_found": "Datei nicht gefunden: {error}",
        "cli.error.invalid_input": "Ungültige Eingabe: {error}",
        "cli.error.generic": "Fehler: {error}",

        # =============================================================================
        # API - Descriptions and messages
        # =============================================================================
        "api.title": "Firmensuche-API",
        "api.description": "REST-API für Firmen-Whitelist/Blacklist-Suche mit Fuzzy-Matching",

        # Endpoints
        "api.root.description": "API-Informationsendpunkt",
        "api.health.description": "Gesundheitsprüfungsendpunkt",
        "api.lookup.description": (
            "Einen Firmennamen in der Whitelist/Blacklist suchen. "
            "Gibt den Firmenstatus (whitelist, blacklist oder unknown) "
            "zusammen mit Konfidenzwert und Trefferdetails zurück."
        ),
        "api.batch.description": (
            "Mehrere Firmennamen auf einmal suchen. Gibt aggregierte Ergebnisse für alle Firmen zurück."
        ),
        "api.list_all.description": "Alle Firmen in der Datenbank auflisten",
        "api.list_whitelist.description": "Alle Firmen auf der Whitelist auflisten",
        "api.list_blacklist.description": "Alle Firmen auf der Blacklist auflisten",
        "api.stats.description": "Statistiken über die Firmenlisten abrufen",
        "api.upload.description": (
            "Eine Excel-Datei mit Firmenlisten hochladen. "
            "Die Datei sollte 'Whitelist'- und 'Blacklist'-Blätter mit einer 'Company Name'-Spalte haben."
        ),
        "api.reload.description": "Firmendaten aus der Excel-Datei neu laden",

        # API messages
        "api.error.engine_not_initialized": (
            "Engine nicht initialisiert. Laden Sie zuerst eine Excel-Datei hoch oder setzen Sie COMPANY_LOOKUP_EXCEL_FILE."
        ),
        "api.error.invalid_file_format": "Ungültiges Dateiformat. Erwartet wird .xlsx, .xls oder .xlsm",
        "api.error.process_failed": "Dateiverarbeitung fehlgeschlagen: {error}",
        "api.error.reload_failed": "Neuladen der Daten fehlgeschlagen: {error}",
        "api.success.upload": "Datei erfolgreich hochgeladen und verarbeitet",
        "api.success.reload": "Daten erfolgreich neu geladen",

        # =============================================================================
        # Formatter - Output labels
        # =============================================================================
        "fmt.panel.title": "Firmensuchergebnis",
        "fmt.query": "Anfrage",
        "fmt.status": "Status",
        "fmt.confidence": "Konfidenz",
        "fmt.match.title": "Bester Treffer",
        "fmt.matches.title": "Weitere Treffer",
        "fmt.company": "Firma",
        "fmt.score": "Bewertung",
        "fmt.match_type": "Trefferart",
        "fmt.exact_match": "Exakter Treffer",
        "fmt.notes": "Anmerkungen",
        "fmt.field": "Feld",
        "fmt.value": "Wert",
        "fmt.company_name": "Firmenname",
        "fmt.category": "Kategorie",
        "fmt.stats.title": "Firmenlisten-Statistiken",
        "fmt.stats.total": "Firmen gesamt",
        "fmt.stats.whitelisted": "Whitelist",
        "fmt.stats.blacklisted": "Blacklist",
        "fmt.stats.categories": "Kategorien",
        "fmt.stats.last_updated": "Zuletzt aktualisiert",
        "fmt.stats.source_file": "Quelldatei",
        "fmt.metric": "Metrik",
        "fmt.companies_title": "Firmen ({filter})",

        # =============================================================================
        # Lookup Engine - Warnings and messages
        # =============================================================================
        "engine.warning.no_matches": "Keine Treffer über dem Schwellenwert gefunden",
        "engine.warning.near_threshold": "Trefferwert liegt nahe am Schwellenwert - bitte manuell überprüfen",
        "engine.warning.conflicting": "Sowohl Whitelist- als auch Blacklist-Treffer gefunden - Überprüfung erforderlich",
        "engine.warning.multiple_close": "Mehrere ähnliche Treffer gefunden - bitte Auswahl überprüfen",
        "engine.warning.fuzzy_match": "Fuzzy-Treffer: '{query}' zugeordnet zu '{matched}'",
        "engine.error.not_initialized": "Suchmaschine nicht initialisiert. Rufen Sie zuerst initialize() auf.",
        "engine.error.no_excel_path": "Kein Excel-Dateipfad angegeben",
        "engine.error.no_excel_configured": "Kein Excel-Dateipfad konfiguriert",
        "engine.info.initialized": "Suchmaschine erfolgreich initialisiert",
        "engine.info.added_company": "Firma hinzugefügt: {name} ({status})",

        # =============================================================================
        # Excel Reader - Messages
        # =============================================================================
        "excel.info.loading": "Lade Firmenlisten aus: {path}",
        "excel.info.loaded": "{count} Firmen geladen ({whitelist} Whitelist, {blacklist} Blacklist)",
        "excel.info.template_created": "Excel-Vorlagendatei erstellt: {path}",
        "excel.warning.sheet_not_found": "{sheet_type}-Blatt '{name}' nicht gefunden",
        "excel.warning.duplicate": "Doppelte Firma gefunden: {name}",

        # =============================================================================
        # Status labels
        # =============================================================================
        "status.whitelisted": "Whitelist",
        "status.blacklisted": "Blacklist",
        "status.unknown": "Unbekannt",
        "status.all": "Alle",
    },
}


def get_translation(key: str, language: str = "en", **kwargs) -> str:
    """Get a translation for a key.

    Args:
        key: The translation key.
        language: Language code ('en' or 'de').
        **kwargs: Format arguments for the translation string.

    Returns:
        The translated string, or the key if not found.
    """
    lang_dict = TRANSLATIONS.get(language, TRANSLATIONS["en"])
    text = lang_dict.get(key, TRANSLATIONS["en"].get(key, key))

    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text
