# Primary technical sources

Accessed 29 October 2026. These sources were consulted to check source semantics, batched reading, Compose startup ordering and bulk database loading.

1. New York City Taxi and Limousine Commission. TLC Trip Record Data. https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
2. TLC. Yellow Taxi Trip Records Data Dictionary. https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf
3. TLC. January 2025 Yellow Taxi Parquet source. https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-01.parquet
4. Docker. Control startup and shutdown order in Compose. https://docs.docker.com/compose/how-tos/startup-order/
5. Apache Arrow. ParquetFile and iter_batches. https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html
6. PostgreSQL Global Development Group. PostgreSQL 17 COPY. https://www.postgresql.org/docs/17/sql-copy.html

TLC explains that source accuracy is not guaranteed, defines the timestamps and measured trip distance, and warns that total_amount excludes cash tips. The declared cleaning policy is specific to this project and does not represent a quality guarantee from the publisher. No claim is made that these technical documentation pages are peer-reviewed journal articles.
