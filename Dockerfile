# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ app/
COPY ui/ ui/
COPY docs/ docs/
COPY streamlit_app.py .
COPY README.md .

# Expose ports
EXPOSE 8501
EXPOSE 10000

ENV PORT=8501

# Run Streamlit UI with dynamic port binding for Render / Cloud
CMD ["sh", "-c", "streamlit run streamlit_app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true"]
