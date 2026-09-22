# GEF V108 — Treasury auction source forensic

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22

Purpose: resolve Treasury auction source provenance and schema before any alpha search.

Rules:
- zero edge trials;
- zero market-return reads;
- inspect every Treasury-auction candidate file under DataLake;
- accept only files physically bounded to <=2022 or explicit pre2023 paths;
- inspect CSV, parquet, XLS/XLSX, JSON, XML and ZIP containers when possible;
- identify auction date, issue/maturity identifier, bid-to-cover, high yield/rate, awarded/accepted amounts and other numeric fields;
- build a normalized preview only when auction_date can be parsed causally;
- canonical conservative availability remains auction_date + 1 calendar day unless a more explicit publication timestamp exists in the source;
- never read 2023+ rows into the canonical preview.

Output:
- TREASURY_SOURCE_AUDIT.csv
- TREASURY_SCHEMA_CANDIDATES.csv
- TREASURY_NORMALIZED_PREVIEW.csv if possible
- RUN_RECEIPT.json

This run must terminate cleanly even if no source is usable.
