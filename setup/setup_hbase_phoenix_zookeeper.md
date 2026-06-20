# Cài đặt HBase, Phoenix và ZooKeeper

Lớp này tích hợp NoSQL để minh họa luồng HDFS -> HBase -> Phoenix SQL/View.

Thiết kế:

```text
/book_project/landing/books
-> HBase shell import
-> HBase table BOOKS
-> Phoenix views và truy vấn kiểm tra
```

## Các dịch vụ

Khởi động Hadoop trước để HDFS sẵn sàng, sau đó khởi động HBase/ZooKeeper:
Lưu ý: start-all.sh or stop-all.sh chỉ áp dụng cho Spark
```bash
start-dfs.sh
start-yarn.sh
start-hbase.sh or ~/start-hbase-cluster.sh
```

Kiểm tra:

```bash
jps
```

Các Java process sẽ phải có bắt buộc để thực hiện task này:

```text
1299 ResourceManager
2422 HMaster
3223 Jps
729 DataNode
602 NameNode
973 SecondaryNameNode
1437 NodeManager
2638 HRegionServer
2222 HQuorumPeer
```

Kiểm tra HBase shell xem HBase có hoạt động sẵn sàn chưa?

```bash
hbase shell
```

Trong HBase shell:

```ruby
status
list_namespace
exit
```

`list_namespace` chỉ cần xuất hiện các namespace cơ bản như System và defaut là thành công.

## Dữ liệu đầu vào trên HDFS

Dữ liệu sạch phải tồn tại sẵn
trên HDFS tại:

```text
/book_project/landing/books
```

Kiểm tra:

```bash
hdfs dfs -ls /book_project/landing
hdfs dfs -cat /book_project/landing/books/part-m-00000
```

## Chạy pipeline HBase/Phoenix:
Chỉ dùng khi bạn muốn xóa bảng HBase cũ và import lại dữ liệu từ HDFS:
```bash
cd "/mnt/d/HK2_dot2_2025-2026/Big-data/Cuối kỳ/Book_BigDataProject"

PHOENIX_ZK=127.0.0.1:2181 \
bash scripts/ubuntu/run_hbase_phoenix.sh
```
Dùng khi HBase đã có dữ liệu rồi
```bash
cd "/mnt/d/HK2_dot2_2025-2026/Big-data/Cuối kỳ/Book_BigDataProject"

PHOENIX_ZK=127.0.0.1:2181 \
SKIP_HBASE_CREATE=true \
SKIP_HBASE_IMPORT=true \
bash scripts/ubuntu/run_hbase_phoenix.sh
```

