import os
import mysql.connector

# Optional: load values from a local .env file (never commit .env!)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "quickfix_db"),
}

# Admin login (set real values in .env)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@quickfix.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")


def get_db_connection():
    """Returns a new MySQL connection using DB_CONFIG."""
    return mysql.connector.connect(**DB_CONFIG)
