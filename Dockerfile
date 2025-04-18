FROM python:3.12-slim

# Set up a non-root user for better security
RUN adduser --disabled-password --gecos "" book2tts

WORKDIR /app

RUN pip install uv

COPY --chown=book2tts:book2tts . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG=0

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