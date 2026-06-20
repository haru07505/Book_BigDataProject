-- Count all books exposed through the Phoenix view.
SELECT COUNT(*) AS TOTAL_BOOKS
FROM "bookbigdata"."books_hbase";

-- Count books by source.
SELECT "info"."source" AS SOURCE, COUNT(*) AS TOTAL_BOOKS
FROM "bookbigdata"."books_hbase"
GROUP BY "info"."source";

-- Compare category size and average price.
SELECT
  "info"."main_category" AS MAIN_CATEGORY,
  COUNT(*) AS BOOK_COUNT,
  AVG(TO_NUMBER("price"."price")) AS AVG_PRICE
FROM "bookbigdata"."books_hbase"
GROUP BY "info"."main_category"
ORDER BY BOOK_COUNT DESC
LIMIT 10;

-- Top-selling books visible through Phoenix.
SELECT
  "info"."title" AS TITLE,
  "info"."author" AS AUTHOR,
  TO_NUMBER("stat"."sold_count") AS SOLD_COUNT,
  TO_NUMBER("price"."price") AS PRICE
FROM "bookbigdata"."books_hbase"
WHERE "stat"."sold_count" IS NOT NULL
ORDER BY SOLD_COUNT DESC
LIMIT 10;