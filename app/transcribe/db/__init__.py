# Use a relative import so tests can run without installing the package
from .app_db import AppDB


DB_CONTEXT = AppDB()
