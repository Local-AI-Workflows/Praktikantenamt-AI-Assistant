# Company Lookup MCP Tool

Company whitelist/blacklist lookup with fuzzy matching for validating internship contracts.

## Features

- **Fuzzy Matching** via RapidFuzz (typos, variations, partial names)
- **Excel Integration** with customizable sheet/column names
- **Multiple Interfaces**: CLI, REST API, MCP server (SSE/stdio)
- **Docker Support** with docker-compose profiles

## Quick Start

```bash
cd mcp-tools/company-lookup
pip install -e .
python create_sample_data.py  # Creates data/companies.xlsx
```

### CLI

```bash
company-lookup lookup -e data/companies.xlsx -q "Siemens AG"
company-lookup lookup -e data/companies.xlsx -q "Seimens" -t 70  # Fuzzy
company-lookup list -e data/companies.xlsx --status whitelist
company-lookup stats -e data/companies.xlsx
company-lookup serve -e data/companies.xlsx -p 8000  # REST API
```

## Docker

```bash
docker-compose up company-mcp          # MCP SSE on port 8080
docker-compose --profile api up        # REST API on port 8000
```

## Claude Desktop Integration

### Option 1: Docker SSE (Recommended)

1. Start the MCP server:

   ```bash
   docker-compose up company-mcp  # Runs on port 8080
   ```

2. Add to Claude Desktop config (`~/.claude/claude_desktop_config.json` or `%APPDATA%\Claude\claude_desktop_config.json`):

   ```json
   {
     "mcpServers": {
       "company-lookup": {
         "command": "npx",
         "args": ["-y", "mcp-remote", "http://localhost:8080/sse", "--transport", "sse-only"]
       }
     }
   }
   ```

   > **Note:** Claude Desktop doesn't natively support SSE URLs, so we use `mcp-remote` as a bridge.

### Option 2: Local stdio

```json
{
  "mcpServers": {
    "company-lookup": {
      "command": "company-lookup-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "COMPANY_LOOKUP_EXCEL_FILE": "/path/to/companies.xlsx"
      }
    }
  }
}
```

## MCP Tools

| Tool                     | Description                                   |
| ------------------------ | --------------------------------------------- |
| `lookup_company`         | Full lookup with fuzzy matching               |
| `check_company_approved` | Quick whitelist check                         |
| `check_company_blocked`  | Quick blacklist check                         |
| `list_companies`         | List companies (filter: all/whitelist/blacklist) |
| `get_company_stats`      | Database statistics                           |
| `batch_lookup`           | Look up multiple companies                    |

## REST API

| Endpoint            | Description         |
| ------------------- | ------------------- |
| `POST /lookup`      | Look up a company   |
| `POST /lookup/batch`| Batch lookup        |
| `GET /companies`    | List all companies  |
| `GET /stats`        | Get statistics      |
| `GET /health`       | Health check        |

## Excel File Format

Two sheets required: **Whitelist** and **Blacklist**

| Company Name | Category | Notes |
| ------------ | -------- | ----- |
| Siemens AG   | Technology | Major German corporation |

## Configuration

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `COMPANY_LOOKUP_EXCEL_FILE` | - | Path to Excel file |
| `COMPANY_LOOKUP_THRESHOLD` | 80.0 | Fuzzy threshold (0-100) |
| `MCP_PORT` | 8080 | MCP SSE port |

## Fuzzy Matching

Uses RapidFuzz with adaptive weighting. Normalizes company names (removes GmbH, AG, etc.) and boosts scores when query tokens are contained in target.

**Examples:**
- "BMW" → "BMW Group" = 88% (token containment)
- "Seimens" → "Siemens AG" = 77% (typo tolerance)

**Limitations:** No semantic matching ("VW" ≠ "Volkswagen")

## Testing

```bash
pip install -e ".[dev]"
pytest tests/test_quantification.py -v           # Algorithm tests
python tests/mcp_evaluation/evaluate_mcp.py -m llama3.2:3b  # LLM evaluation
```

## Architecture

```
company_lookup/
├── cli.py           # CLI interface
├── api.py           # FastAPI REST
├── mcp_server.py    # MCP server (SSE/stdio)
├── core/
│   ├── excel_reader.py
│   ├── fuzzy_matcher.py
│   └── lookup_engine.py
└── data/schemas.py  # Pydantic models
```

## License

MIT License
