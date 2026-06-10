FROM python:3.11-slim

WORKDIR /app

# Install system utilities needed for building heavy wheels or executing health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# CRITICAL STEP: Copy ONLY requirements first to isolate the heavy installation layer
COPY requirements.txt .

# Use --no-cache-dir to prevent pip from saving duplicate download tars inside the image layer
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu  --force-reinstall -r requirements.txt

# Copy the rest of the application
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]




