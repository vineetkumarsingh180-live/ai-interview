"""
DbIngestion: external sources -> validated, deduplicated, provenance-labelled rows in PostgreSQL.

This is an ingestion package, not a backend. It owns no tables and no schema (Alembic in backend/
is the only schema authority) and it never speaks HTTP to the browser. Source-specific business
rules live in the owning backend module; this package orchestrates.
"""
