# Cài đặt Spark

Cài Apache Spark `3.5.8` bản pre-built for Hadoop 3 và bảo đảm gọi được
`spark-submit` thông qua biến `PATH`.

PySpark đã nằm trong bản phân phối Apache Spark. Pipeline Ubuntu không cần
chạy riêng `pip install pyspark` khi sử dụng `spark-submit`.

Ứng dụng Spark hiện chạy theo hướng Spark SQL + Hive Metastore:

```text
Hive Metastore/MySQL metadata
book_project.books_spark
-> PySpark with enableHiveSupport()
-> /book_project/analytics/spark
```

Trước khi chạy Spark, bảo đảm Hive Metastore đang chạy và bảng `books_spark`
do Hive ánh xạ tới `/book_project/warehouse/books_spark` đã tồn tại:

```bash
hive -e "USE book_project; SHOW TABLES;"
hive -e "SELECT COUNT(*) FROM book_project.books_spark;"
```

Spark cần đọc được `hive-site.xml`. Nếu chưa copy, chạy:

```bash
cp $HIVE_HOME/conf/hive-site.xml $SPARK_HOME/conf/
```

Chạy:

```bash
bash scripts/ubuntu/run_spark.sh
```

Có thể override database, bảng nguồn và output:

```bash
HIVE_DATABASE=book_project \
HIVE_SPARK_SOURCE_TABLE=books_spark \
HDFS_SPARK_OUTPUT=/book_project/analytics/spark \
bash scripts/ubuntu/run_spark.sh
```

Kiểm tra bảng Hive nguồn:

```bash
hive -e "SELECT COUNT(*) FROM book_project.books_spark;"
hdfs dfs -ls /book_project/warehouse/books_spark
```

Kiểm tra output analytics:

```bash
hdfs dfs -ls /book_project/analytics/spark
hdfs dfs -cat /book_project/analytics/spark/source_comparison/part-*
```

Các output Spark gồm:

```text
popular_books
potential_books
source_comparison
category_performance
price_segment
```
