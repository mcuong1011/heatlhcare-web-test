FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (keeps builds reliable for packages with C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# If your settings don't already set this, manage.py usually does
ENV DJANGO_SETTINGS_MODULE=healthcare_system.settings

EXPOSE 8000

# Migrate then start Django dev server (for local use only)
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
