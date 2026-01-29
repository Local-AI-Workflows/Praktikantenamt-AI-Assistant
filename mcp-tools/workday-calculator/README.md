# Workday Calculator MCP Tool

An MCP (Model Context Protocol) server for calculating working days in Germany, accounting for federal state-specific (Bundesland) public holidays.

## Features

- Calculate working days between two dates
- Bundesland-specific public holidays
- Multiple location resolution methods (PLZ, Bundesland code, address geocoding)
- Three deployment modes: **CLI**, **REST API**, and **MCP Server**
- Docker support with SSE transport for remote integration

## Quick Start

### Installation

```bash
cd mcp-tools/workday-calculator
pip install -e .
```

### CLI Usage

```bash
# Calculate workdays for Hamburg
workday-calc calculate -s 2026-03-01 -e 2026-08-31 --plz 20095

# Calculate workdays using Bundesland code
workday-calc calculate -s 2026-03-01 -e 2026-08-31 -b BY

# List holidays for Bayern in 2026
workday-calc holidays --year 2026 --bundesland BY

# List all Bundeslaender codes
workday-calc bundeslaender
```

## MCP Server Setup

The MCP server can be run in two transport modes:

| Mode | Use Case | Transport |
|------|----------|-----------|
| **stdio** | Local Claude Desktop | Standard input/output |
| **SSE** | Docker / Remote servers | HTTP Server-Sent Events |

### Option 1: Local Installation (stdio)

For local Claude Desktop integration, add to your `claude_desktop_config.json`:

**Windows:**
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

**macOS/Linux:**
```json
{
  "mcpServers": {
    "workday-calculator": {
      "command": "workday-calc-mcp",
      "args": ["--transport", "stdio"]
    }
  }
}
```

Config file locations:
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/claude/claude_desktop_config.json`

### Option 2: Docker with SSE (Recommended for Remote)

The SSE transport exposes the MCP server over HTTP, making it accessible from Docker containers or remote machines.

#### Start with Docker Compose

```bash
cd mcp-tools/workday-calculator

# Start MCP SSE server (default)
docker-compose up -d workday-mcp

# Check logs
docker-compose logs -f workday-mcp

# Health check
curl http://localhost:8080/sse
```

#### Configure Claude Desktop for SSE

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "workday-calculator": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

For remote servers, replace `localhost` with the server hostname/IP.

#### Build and Run Manually

```bash
# Build the image
docker build -t workday-calculator-mcp .

# Run with SSE transport
docker run -d -p 8080:8080 --name workday-mcp workday-calculator-mcp

# Or override to stdio mode
docker run -i --rm workday-calculator-mcp workday-calc-mcp --transport stdio
```

## Docker Compose Services

The `docker-compose.yml` provides three service profiles:

| Service | Port | Profile | Description |
|---------|------|---------|-------------|
| `workday-mcp` | 8080 | (default) | MCP SSE server for Claude Desktop |
| `workday-api` | 8000 | `api` | REST API for n8n integration |
| `workday-mcp-stdio` | - | `stdio` | MCP stdio for containerized Claude |

```bash
# Start MCP SSE server (default)
docker-compose up -d

# Start REST API alongside MCP
docker-compose --profile api up -d

# Start all services
docker-compose --profile api --profile stdio up -d
```

## REST API

For n8n and generic HTTP clients, a FastAPI REST server is available:

```bash
# Local
uvicorn workday_calculator.api:app --reload

# Docker
docker-compose --profile api up -d workday-api
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/calculate` | Calculate working days |
| `GET` | `/holidays/{year}/{bundesland}` | List holidays for year |
| `GET` | `/bundeslaender` | List all Bundeslaender |
| `GET` | `/health` | Health check |

### Example Request

```bash
curl -X POST http://localhost:8000/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-03-01",
    "end_date": "2026-08-31",
    "postal_code": "20095"
  }'
```

## MCP Tools Available

When connected via MCP, the following tools are exposed:

### `calculate_workdays`

Calculate working days between two dates for a German location.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `start_date` | string | Yes | Start date (YYYY-MM-DD) |
| `end_date` | string | Yes | End date (YYYY-MM-DD) |
| `postal_code` | string | No* | German PLZ (e.g., "20095") |
| `bundesland` | string | No* | Bundesland code (e.g., "HH", "BY") |
| `address` | string | No* | Full address for geocoding |
| `include_saturdays` | bool | No | Count Saturdays as workdays (default: false) |

*At least one location parameter required.

**Example Response:**
```json
{
  "working_days": 130,
  "calendar_days": 184,
  "weekend_days": 52,
  "holidays_count": 2,
  "holidays": [
    {"date": "2026-05-01", "name": "Tag der Arbeit", "is_national": true}
  ],
  "bundesland": "HH",
  "bundesland_name": "Hamburg"
}
```

### `get_holidays`

Get all public holidays for a year and Bundesland.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `year` | int | Yes | Year (1900-2100) |
| `bundesland` | string | Yes | Bundesland code |

### `list_bundeslaender`

List all German federal states with their codes.

## Bundesland Codes

| Code | Name |
|------|------|
| BB | Brandenburg |
| BE | Berlin |
| BW | Baden-Württemberg |
| BY | Bayern |
| HB | Bremen |
| HE | Hessen |
| HH | Hamburg |
| MV | Mecklenburg-Vorpommern |
| NI | Niedersachsen |
| NW | Nordrhein-Westfalen |
| RP | Rheinland-Pfalz |
| SH | Schleswig-Holstein |
| SL | Saarland |
| SN | Sachsen |
| ST | Sachsen-Anhalt |
| TH | Thüringen |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport mode (`stdio` or `sse`) |
| `MCP_HOST` | `0.0.0.0` | Host to bind (SSE mode) |
| `MCP_PORT` | `8080` | Port to listen (SSE mode) |
| `GEOCODING_ENABLED` | `true` | Enable address geocoding |
| `GEOCODING_TIMEOUT` | `5` | Geocoding timeout in seconds |
| `HOLIDAY_LANGUAGE` | `de` | Holiday names language |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black workday_calculator/

# Type checking
mypy workday_calculator/
```

## License

Part of the Praktikantenamt AI-Assistant project.
