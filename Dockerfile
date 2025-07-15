FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and uv.lock for dependency installation
COPY uv.lock .
COPY pyproject.toml .

# Install Python dependencies using uv
RUN uv sync

# Copy application code
COPY . .

# Create a non-root user for security
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp

# Expose the port
EXPOSE 8000

# Run the application
ENTRYPOINT ["uv", "run", "mcp_server.py"]