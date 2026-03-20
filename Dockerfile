FROM python:3.12-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY main.py ./

# Install dependencies
RUN pip install --no-cache-dir -e .

# Set environment variables for MCP server
ENV BOTS_API_URL=http://localhost:8080
ENV PYTHONUNBUFFERED=1

# Run the MCP server
ENTRYPOINT ["python", "-m", "main"]
CMD []
