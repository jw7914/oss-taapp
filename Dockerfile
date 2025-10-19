FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set PYTHONPATH so all internal packages are discoverable
ENV PYTHONPATH=/src/mail_client_service/src:/src/mail_client_api/src:/src/gmail_client_impl/src

# Copy uv configuration files
COPY pyproject.toml uv.lock ./

# Copy all source code and workspace dependencies
COPY src/ ./src/

# Install dependencies using uv
RUN uv sync --all-packages --extra dev

# Copy credentials and configuration files 
COPY credentials.json* ./
COPY token.json* ./
COPY .env* ./

# Expose the port that FastAPI will run on
EXPOSE 8080

# Health check to ensure the service is running
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Set the default command to run the FastAPI application with Uvicorn
CMD ["uv", "run", "uvicorn", "mail_client_service.main:app", "--host", "0.0.0.0", "--port", "8080"]
