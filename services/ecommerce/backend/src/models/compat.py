"""
Database Compatibility Utilities

SQLite/PostgreSQL compatibility for JSON types
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB as PostgreSQL_JSONB


# Use JSON for SQLite compatibility, JSONB for PostgreSQL performance
# SQLAlchemy will automatically use the appropriate type based on the database
JSONB = JSON
