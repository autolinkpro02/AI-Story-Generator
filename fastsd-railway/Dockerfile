FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for image processing and CUDA (if available)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-optimized and diffusers
RUN pip install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    diffusers transformers accelerate \
    fastapi uvicorn \
    pillow numpy \
    omegaconf \
    einops \
    xformers

# Copy the FastSD API server
COPY app.py /app/app.py
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
