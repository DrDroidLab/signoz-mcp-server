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
2. Run the container:
   ```bash
   docker run -d \
     -p 5002:5002 \
     -v $(pwd)/config.yaml:/app/config.yaml:ro \
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

Edit `config.yaml` to configure your Signoz instance:

```yaml
signoz:
  host: "https://your-signoz-instance.com"
  api_key: "your-signoz-api-key-here"  # Optional
  ssl_verify: "true"
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
      "env": {}
    }
  }
}
```
- Ensure your `config.yaml` is in the same directory as `mcp_server.py` or update the path accordingly.
- If you are using Windows, activate the environment with `env\\Scripts\\activate` instead of `source env/bin/activate`.

### B. Using Docker
```json
{
  "mcpServers": {
    "signoz": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v",
        "/full/path/to/config.yaml:/app/config.yaml:ro",
        "signoz-mcp-server"
      ],
      "env": {}
    }
  }
}
```
- Adjust the volume path to your actual `config.yaml` location.

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
- **test_connection**: Verify connectivity to your Signoz instance

## Health Check
```bash
curl http://localhost:5002/health
```
The server runs on port 5002 by default.

---

For more advanced integrations, refer to the [MCP protocol documentation](https://github.com/modelcontext/protocol) or your tool's documentation for MCP support. 