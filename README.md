# Signoz MCP Server

## 🚀 Usage

### 1. Get Your Signoz API Endpoint & (Optional) API Key

1. Ensure you have a running Signoz instance (self-hosted or cloud).
2. (Optional) If your Signoz instance requires an API key for the health endpoint, generate or obtain it from your Signoz UI.

### 2. Installation & Running Options

#### A. Docker Compose (Recommended)
1. Edit `config.yaml` with your Signoz details (host, API key if needed).
2. Start the server:
   ```bash
   docker-compose up -d
   ```
   - The server will run in HTTP (SSE) mode on port 5002 by default.

#### B. Docker Image (Manual)
1. Build the image:
   ```bash
   docker build -t signoz-mcp-server .
   ```
2. Run the container (YAML config fallback):
   ```bash
   docker run -d \
     -p 5002:5002 \
     -v $(pwd)/config.yaml:/app/config.yaml:ro \
     --name signoz-mcp-server \
     signoz-mcp-server
   ```
3. **Or run with environment variables (recommended for CI/Docker MCP clients):**
   ```bash
   docker run -d \
     -p 5002:5002 \
     -e SIGNOZ_HOST="https://your-signoz-instance.com" \
     -e SIGNOZ_API_KEY="your-signoz-api-key-here" \
     -e SIGNOZ_SSL_VERIFY="true" \
     -e MCP_SERVER_PORT=5002 \
     -e MCP_SERVER_DEBUG=true \
     --name signoz-mcp-server \
     signoz-mcp-server
   ```

#### C. Local Development
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   python mcp_server.py
   ```

---

## Configuration

The server loads configuration in the following order of precedence:

1. **Environment Variables** (recommended for Docker/CI):
   - `SIGNOZ_HOST`: Signoz instance URL (e.g. `https://your-signoz-instance.com`)
   - `SIGNOZ_API_KEY`: Signoz API key (optional)
   - `SIGNOZ_SSL_VERIFY`: `true` or `false` (default: `true`)
   - `MCP_SERVER_PORT`: Port to run the server on (default: `5002`)
   - `MCP_SERVER_DEBUG`: `true` or `false` (default: `true`)
2. **YAML file fallback** (`config.yaml`):
   ```yaml
   signoz:
     host: "https://your-signoz-instance.com"
     api_key: "your-signoz-api-key-here"  # Optional
     ssl_verify: "true"
   server:
     port: 5002
     debug: true
   ```

---

## Integration with AI Assistants (e.g., Claude Desktop)

You can integrate this MCP server with any tool that supports the MCP protocol. Here are the main options:

### A. Using Local Setup
Before running the server locally, create a Python virtual environment and install dependencies:

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Then add to your client configuration (e.g., `claude-desktop.json`):
```json
{
  "mcpServers": {
    "signoz": {
      "command": "python",
      "args": ["/full/path/to/mcp_server.py"],
      "env": {
        "SIGNOZ_HOST": "https://your-signoz-instance.com",
        "SIGNOZ_API_KEY": "your-signoz-api-key-here",
        "SIGNOZ_SSL_VERIFY": "true"
      }
    }
  }
}
```
- Ensure your `config.yaml` is in the same directory as `mcp_server.py` or update the path accordingly.
- If you are using Windows, activate the environment with `env\\Scripts\\activate` instead of `source env/bin/activate`.

### B. Using Docker (with environment variables, mcp-grafana style)
```json
{
  "mcpServers": {
    "signoz": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e", "SIGNOZ_HOST",
        "-e", "SIGNOZ_API_KEY",
        "-e", "SIGNOZ_SSL_VERIFY",
        "signoz-mcp-server",
        "-t", "stdio"
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

### C. Connecting to an Already Running MCP Server (HTTP/SSE)
If you have an MCP server already running (e.g., on a remote host, cloud VM, or Kubernetes), you can connect your AI assistant or tool directly to its HTTP endpoint.

#### Example: Claude Desktop or Similar Tool
```json
{
  "mcpServers": {
    "signoz": {
      "type": "http",
      "url": "http://your-server-host:5002/mcp"
    }
  }
}
```
- Replace `http://your-server-host:5002/mcp` with the actual URL of your running MCP server instance.
- Make sure the server is accessible from your client machine (check firewall, security group, etc.).

#### Example: MCP Config YAML
```yaml
mcp:
  endpoint: "http://your-server-host:5002/mcp"
  protocolVersion: "2025-06-18"
```
- No need to specify `command` or `args`—just point to the HTTP endpoint.
- This works for any tool or assistant that supports MCP over HTTP.
- The server must be running in HTTP (SSE) mode (the default for this implementation).

---

## Available Tools
The following tools are available via the MCP server:

- **test_connection**: Verify connectivity to your Signoz instance and configuration.
- **fetch_dashboards**: List all available dashboards from Signoz.
- **fetch_dashboard_details**: Retrieve detailed information about a specific dashboard by its ID. This information contains the metadata of the dashboard, not the live panel data.
- **query_metrics**: Query metrics from Signoz with a specified time range and query parameters.
- **fetch_dashboard_data**: Fetch all panel data for a given dashboard by name and time range.
- **fetch_apm_metrics**: Retrieve standard APM metrics (request rate, error rate, latency, apdex, etc.) for a given service and time range.

## Health Check
```bash
curl http://localhost:5002/health
```
The server runs on port 5002 by default.

---

For more advanced integrations, refer to the [MCP protocol documentation](https://github.com/modelcontext/protocol) or your tool's documentation for MCP support. 