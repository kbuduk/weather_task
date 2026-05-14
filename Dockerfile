# Use an official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (required for some Pandas operations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY main.py .

# Expose the port FastAPI runs on
EXPOSE 8080

# Command to run the application
# Cloud Run passes the PORT environment variable, so we bind to it
CMD ["sh", "-c", "uvicorn main.py:app --host 0.0.0.0 --port ${PORT:-8080}"]