FROM python:3.13-slim

# Install system dependencies for geospatial libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gdal-bin \
    libgdal-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY .python-version ./
COPY src/ ./src/
COPY flows/ ./flows/
COPY tests/ ./tests/

# Install uv
RUN pip install uv

# Install dependencies using uv
RUN uv pip install --system -e .

# Set Python path
ENV PYTHONPATH=/app

CMD ["python", "-m", "prefect.cli", "worker", "start", "--pool", "default-pool", "--type", "process"]
