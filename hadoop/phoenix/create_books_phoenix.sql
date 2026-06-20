DROP VIEW IF EXISTS "bookbigdata"."books_hbase" CASCADE;

CREATE SCHEMA IF NOT EXISTS "bookbigdata";

CREATE VIEW "bookbigdata"."books_hbase" (
  ROWKEY VARCHAR PRIMARY KEY,
  "info"."source" VARCHAR,
  "info"."title" VARCHAR,
  "info"."author" VARCHAR,
  "info"."publisher" VARCHAR,
  "info"."language_group" VARCHAR,
  "info"."main_category" VARCHAR,
  "info"."sub_category" VARCHAR,
  "info"."publish_year" VARCHAR,
  "info"."page_count" VARCHAR,
  "info"."url" VARCHAR,
  "price"."price" VARCHAR,
  "price"."original_price" VARCHAR,
  "price"."discount_rate" VARCHAR,
  "stat"."rating" VARCHAR,
  "stat"."review_count" VARCHAR,
  "stat"."sold_count" VARCHAR
);