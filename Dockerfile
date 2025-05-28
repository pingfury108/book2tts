FROM python:3.12-slim

# Set up a non-root user for better security
RUN adduser --disabled-password --gecos "" book2tts

WORKDIR /app

# Install system dependencies required for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libc6-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY --chown=book2tts:book2tts . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG=0
# Set CSS version using build timestamp for cache busting
ARG CSS_VERSION=1
ENV CSS_VERSION=${CSS_VERSION}

# Install dependencies from lock file
RUN uv pip install --no-cache --system -r requirements.lock

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

USER book2tts

WORKDIR /app

# Expose port
EXPOSE 8000

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 