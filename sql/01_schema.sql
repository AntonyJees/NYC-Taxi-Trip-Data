SET ROLE taxi_pipeline;
CREATE TABLE taxi.sources (
  source_month date PRIMARY KEY,
  source_url text NOT NULL,
  sha256 text NOT NULL,
  raw_rows bigint NOT NULL,
  loaded_at timestamptz NOT NULL DEFAULT now(),
  transformed_sha256 text,
  accepted_rows bigint,
  rejected_rows bigint,
  transform_seconds double precision,
  transformed_at timestamptz
);
CREATE TABLE taxi.raw_trips (
  source_month date NOT NULL,
  source_row bigint NOT NULL,
  pickup_at timestamp,
  dropoff_at timestamp,
  trip_distance double precision,
  fare_amount double precision,
  total_amount double precision,
  passenger_count double precision,
  pickup_zone integer,
  dropoff_zone integer,
  PRIMARY KEY (source_month, source_row)
);
CREATE TABLE taxi.clean_trips (
  LIKE taxi.raw_trips INCLUDING ALL
);
CREATE TABLE taxi.rejections (
  source_month date NOT NULL,
  reason text NOT NULL,
  row_count bigint NOT NULL,
  PRIMARY KEY (source_month, reason)
);
CREATE TABLE taxi.runs (
  run_id text PRIMARY KEY,
  stage text NOT NULL,
  source_month date NOT NULL,
  finished_at timestamptz NOT NULL DEFAULT now(),
  metrics jsonb NOT NULL
);
CREATE INDEX clean_pickup_idx ON taxi.clean_trips(pickup_at);
CREATE VIEW taxi.classified AS
SELECT *, CASE
  WHEN pickup_at IS NULL OR dropoff_at IS NULL THEN 'missing_timestamp'
  WHEN pickup_at < source_month OR pickup_at >= source_month + INTERVAL '1 month' THEN 'pickup_outside_source_month'
  WHEN dropoff_at <= pickup_at OR dropoff_at > pickup_at + INTERVAL '24 hours' THEN 'invalid_duration'
  WHEN NOT COALESCE(trip_distance >= 0 AND trip_distance < 'Infinity'::float8, false) THEN 'invalid_distance'
  WHEN NOT COALESCE(fare_amount >= 0 AND fare_amount < 'Infinity'::float8, false)
    OR NOT COALESCE(total_amount >= 0 AND total_amount < 'Infinity'::float8, false) THEN 'invalid_amount'
  WHEN NOT COALESCE(pickup_zone BETWEEN 1 AND 265 AND dropoff_zone BETWEEN 1 AND 265, false) THEN 'invalid_zone'
  ELSE NULL END AS reject_reason
FROM taxi.raw_trips;
CREATE VIEW taxi.hourly_features AS
SELECT source_month, date_trunc('hour', pickup_at) AS pickup_hour, pickup_zone,
 count(*) AS trip_count, sum(trip_distance) AS total_distance_miles,
 avg(trip_distance) AS mean_distance_miles, sum(total_amount) AS total_revenue,
 avg(total_amount) AS mean_total_amount,
 avg(extract(epoch FROM (dropoff_at-pickup_at))/60.0) AS mean_duration_minutes,
 count(*) FILTER (WHERE passenger_count IS NULL OR passenger_count <= 0 OR passenger_count >= 'Infinity'::float8) AS unknown_passenger_count
FROM taxi.clean_trips GROUP BY 1,2,3;
CREATE VIEW taxi.daily_summary AS
SELECT source_month, pickup_at::date AS pickup_date, count(*) AS trip_count,
 sum(trip_distance) AS total_distance_miles, sum(total_amount) AS total_revenue
FROM taxi.clean_trips GROUP BY 1,2;
CREATE VIEW taxi.quarterly_features AS
SELECT date_trunc('quarter', pickup_at)::date AS quarter_start, pickup_zone,
 extract(hour FROM pickup_at)::integer AS hour_of_day, count(*) AS trip_count,
 avg(trip_distance) AS mean_distance_miles, avg(total_amount) AS mean_total_amount,
 avg(extract(epoch FROM (dropoff_at-pickup_at))/60.0) AS mean_duration_minutes
FROM taxi.clean_trips GROUP BY 1,2,3;
GRANT USAGE ON SCHEMA taxi TO taxi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA taxi TO taxi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA taxi GRANT SELECT ON TABLES TO taxi_reader;
RESET ROLE;
