#!/bin/sh
set -eu
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1 \
  --set=pipeline_password="$PIPELINE_PASSWORD" --set=reader_password="$READER_PASSWORD" <<'SQL'
CREATE ROLE taxi_pipeline LOGIN PASSWORD :'pipeline_password';
CREATE ROLE taxi_reader LOGIN PASSWORD :'reader_password';
CREATE SCHEMA taxi AUTHORIZATION taxi_pipeline;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL
