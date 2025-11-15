# dev.py
from .base import *  # noqa

DEBUG = True
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev‐unsafe‐secret")

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]"]

TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Bangkok")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DEV_DB", "clinicflow_dev"),
        "USER": os.environ.get("POSTGRES_DEV_USER", "clinicflow_dev"),
        "PASSWORD": os.environ.get("POSTGRES_DEV_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_DEV_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_DEV_PORT", "5432"),
    }
}

INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

INTERNAL_IPS = ["127.0.0.1"]
