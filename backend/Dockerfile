FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files
COPY . .

# Default Hugging Face Spaces port is 7860
ENV PORT=7860
EXPOSE 7860

# Run multi-agent orchestrator
CMD ["python", "start_all.py"]
