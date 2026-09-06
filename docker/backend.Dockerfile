FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fluidsynth && rm -rf /var/lib/apt/lists/*
COPY audio-engine /app/audio-engine
COPY backend /app/backend
RUN pip install --no-cache-dir -e /app/audio-engine -e /app/backend
EXPOSE 8000
CMD ["uvicorn", "tunemorph_backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
