# Signoz MCP Server

Watch Working Demo on Cursor 📽️ https://youtube.com/shorts/jxjmGyXXz7A

## Available Tools

The following tools are available via the MCP server:

- **test_connection**: Verify connectivity to your Signoz instance and configuration.
- **fetch_dashboards**: List all available dashboards from Signoz.
- **fetch_dashboard_details**: Retrieve detailed information about a specific dashboard by its ID. This information contains the metadata of the dashboard, not the live panel data.
- **fetch_dashboard_data**: Fetch all panel data for a given dashboard by name and time range.
- **fetch_apm_metrics**: Retrieve standard APM metrics (request rate, error rate, latency, apdex, etc.) for a given service and time range.
- **fetch_services**: Fetch all instrumented services from Signoz with optional time range filtering.
- **execute_clickhouse_query**: Execute custom Clickhouse SQL queries via the Signoz API with time range support.
- **execute_builder_query**: Execute Signoz builder queries for custom metrics and aggregations with time range support.
- **fetch_traces_or_logs**: Fetch traces or logs from SigNoz using ClickHouse SQL. Specify `data_type` ('traces' or 'logs'), time range, service name, and limit. Returns tabular results for traces or logs.

## 🚀 Usage & Requirements

### 1. Get Your Signoz API Endpoint & (Optional) API Key

1. Ensure you have a running Signoz instance (self-hosted or cloud).
2. (Optional) If your Signoz instance requires an API key for the health endpoint, generate or obtain it from your Signoz UI.

---

## 2. Installation & Running Options

### 2A. Install & Run with uv (Recommended for Local Development)

#### 2A.1. Install dependencies with uv

```bash
uv venv .venv
source .venv/bin/activate
uv sync
```

#### 2A.2. Run the server with uv

```bash
uv run -m src.signoz_mcp_server.mcp_server
```

- You can also use `uv` to run any other entrypoint scripts as needed.
- Make sure your `config.yaml` is in the same directory as `mcp_server.py` or set the required environment variables (see Configuration section).

---

### 2B. Run with Docker Compose (Recommended for Production/Containerized Environments)

1. Edit `src/signoz_mcp_server/config.yaml` with your Signoz details (host, API key if needed).
2. Start the server:
   ```bash
   docker-compose up -d
   ```
   - The server will run in HTTP (SSE) mode on port 8000 by default.
   - You can override configuration with environment variables (see below).

---

## 3. Configuration

The server loads configuration in the following order of precedence:

1. **Environment Variables** (recommended for Docker/CI):
   - `SIGNOZ_HOST`: Signoz instance URL (e.g. `https://your-signoz-instance.com`)
   - `SIGNOZ_API_KEY`: Signoz API key (optional)
   - `SIGNOZ_SSL_VERIFY`: `true` or `false` (default: `true`)
   - `MCP_SERVER_PORT`: Port to run the server on (default: `8000`)
   - `MCP_SERVER_DEBUG`: `true` or `false` (default: `true`)
2. **YAML file fallback** (`config.yaml`):
   ```yaml
   signoz:
     host: "https://your-signoz-instance.com"
     api_key: "your-signoz-api-key-here" # Optional
     ssl_verify: "true"
   server:
     port: 8000
     debug: true
   ```

---

## 4. Integration with AI Assistants (e.g., Claude Desktop, Cursor)

You can integrate this MCP server with any tool that supports the MCP protocol. Here are the main options:

### 4A. Using Docker Compose or Docker (with environment variables, mcp-grafana style)

```json
{
  "mcpServers": {
    "signoz": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "SIGNOZ_HOST",
        "-e",
        "SIGNOZ_API_KEY",
        "-e",
        "SIGNOZ_SSL_VERIFY",
        "drdroidlab/signoz-mcp-server",
        "-t",
        "stdio"
      ],
      "env": {
        "SIGNOZ_HOST": "https://your-signoz-instance.com",
        "SIGNOZ_API_KEY": "your-signoz-api-key-here",
        "SIGNOZ_SSL_VERIFY": "true"
      }
    }
  }
}
```

- The `-t stdio` argument is supported for compatibility with Docker MCP clients (forces stdio handshake mode).
- Adjust the volume path or environment variables as needed for your deployment.

### 4C. Connecting to an Already Running MCP Server (HTTP/SSE)

If you have an MCP server already running (e.g., on a remote host, cloud VM, or Kubernetes), you can connect your AI assistant or tool directly to its HTTP endpoint.

#### Example: Claude Desktop or Similar Tool

```json
{
  "mcpServers": {
    "signoz": {
      "url": "http://your-server-host:8000/mcp"
    }
  }
}
```

- Replace `your-server-host` with the actual host where your MCP server is running.
- **For local setup, use `localhost` as the server host (i.e., `http://localhost:8000/mcp`).**
- **Use `http` for local or unsecured deployments, and `https` for production or secured deployments.**
- Make sure the server is accessible from your client machine (check firewall, security group, etc.).

#### Example: MCP Config YAML

```yaml
mcp:
  endpoint: "http://your-server-host:8000/mcp"
  protocolVersion: "2025-06-18"
```

- Replace `your-server-host` with the actual host where your MCP server is running.
- **For local setup, use `localhost` as the server host (i.e., `http://localhost:8000/mcp`).**
- **Use `http` or `https` in the URL schema depending on how you've deployed the MCP server.**
- No need to specify `command` or `args`—just point to the HTTP endpoint.
- This works for any tool or assistant that supports MCP over HTTP.
- The server must be running in HTTP (SSE) mode (the default for this implementation).

---

## Health Check

```bash
curl http://localhost:8000/health
```

The server runs on port 8000 by default.

---

## 5. Miscellaneous:

1. Need help anywhere? Join our [Discord community](https://discord.gg/AQ3tusPtZn) and ask in the #mcp channel.
2. Want to try without setting up? Follow this [doc](https://docs.drdroid.io/getting-started/quickstart) for a quickstart on DrDroid cloud platform.
