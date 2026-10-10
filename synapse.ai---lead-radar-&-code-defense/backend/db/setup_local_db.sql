-- Isolated local database for Synapse.AI. REVIEW BEFORE RUNNING; run as a PostgreSQL superuser:
--
--   export LC_ALL=en_US.UTF-8
--   psql -h localhost -d postgres -f backend/db/setup_local_db.sql
--
-- It creates ONLY a new role and a new database. It never touches other databases or roles.
-- pgvector must already be installed for this server (Homebrew: `brew install pgvector`).

CREATE ROLE synapse_app LOGIN;               -- local trust auth (Homebrew default); no password stored in the repo
CREATE DATABASE synapse_dev OWNER synapse_app;

\connect synapse_dev
CREATE EXTENSION IF NOT EXISTS vector;       -- needs the extension binaries and superuser (this script's user)
