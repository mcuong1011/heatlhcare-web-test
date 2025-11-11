FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# OS deps for mysqlclient build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev pkg-config \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

# Dev-friendly default: migrate, collect static, runserver
CMD sh -c "python manage.py migrate \
 && python manage.py collectstatic --noinput \
 && python manage.py runserver 0.0.0.0:8000"
