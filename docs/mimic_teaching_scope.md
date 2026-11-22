# Phạm vi bản học Mimic-QL

Website dùng một **Mimic-QL-inspired teaching adaptation**, dựa vào phần mô tả của tác giả trong luận án MIT năm 2023, §3.3.2, tr. 62–65 và Phụ lục A.7, tr. 170–171. Đây là nguồn sơ cấp sớm hơn bài báo cuối; bản PDF gốc được giữ ngoài Git. Chưa có đủ căn cứ để gọi bản học này là replication nguyên văn của thuật toán công bố hoặc áp dụng bảo đảm regret của bài.

- [Hồ sơ MIT](https://dspace.mit.edu/entities/publication/35957b3a-1578-49a3-829e-db9aabe08995), [liên kết bền vững](https://hdl.handle.net/1721.1/151589).
- SHA-256 PDF luận án: `fed01bc73d58e6545f070c99c2f2acb653d09c5ea62c1655777ff1cbfd1c25b8`.
- Lõi minh họa: [mimic_ql.py](../lost_sales_lab/mimic_ql.py); kiểm tra hành vi: [test_mimic_ql.py](../lost_sales_lab/tests/test_mimic_ql.py).

## Hai đồng hồ và số dư

Chu kỳ nhu cầu thật là H=3. Hệ FQL ảo chạy episode dài J=6 trên website; lõi cũng cho phép J=9. J là bội của H. Cả kho thực và hệ ảo nhận cùng nhu cầu sau khi đã chốt lệnh, cùng tiến một ngày, kể cả khi chưa ghép được trạng thái. Chỉ hệ ảo khởi tạo lại tồn và pipeline sau J ngày. Kho thực giữ tồn ròng, nợ và pipeline qua mọi ranh giới.

Đặt IP = tồn ròng + pipeline. Bản học tính yêu cầu lệnh thực theo từng sản phẩm:

```text
request = max(IP_virtual + q_virtual - IP_physical, 0)
q_physical = min(order_cap, request)
```

Hệ ảo dùng FQL cùng các cập nhật theo thứ tự J,…,1. Lưới trạng thái, giá trị Q khởi tạo, alpha và cận chuẩn hóa chi phí đều mở rộng theo J, không chỉ đổi đồng hồ reset. Nhu cầu mô phỏng mỗi sản phẩm thuộc 0–2; hạn mức lệnh là 2; tồn ban đầu và pipeline bằng 0. Hạn mức nhỏ giữ bảng hữu hạn có thể chạy trong trình duyệt. Hai hệ vật lý của HQL và FQL có giả thiết khác nhau, nên không lấy chi phí bốn mô hình để xếp hạng chung.

## Những điều chỉnh và điểm cần đối chiếu

Phần văn xuôi của luận án mô tả ghép IP sau quyết định ảo, trong khi giả mã hiển thị không bao gồm rõ số hạng lệnh ảo và có chỗ dùng H/J chưa nhất quán. Bản học chọn cách hiểu ở công thức trên và công khai lựa chọn đó. Đây là vấn đề đối chiếu cách cài đặt từ phiên bản nguồn hiện có, không phải kết luận rằng định lý sai.

Sau reset ảo, IP thực có thể âm lớn. Yêu cầu bù vì vậy có thể vượt miền lệnh hữu hạn. Bản học giới hạn bằng actuator cap và ghi cả `request`, lệnh thực và cờ chạm hạn mức; không cắt tồn ròng, nợ hoặc pipeline. Điều chỉnh này chưa được chứng minh tương đương xây dựng trong bài. Không hứa ghép xong trong một ngày hoặc mọi đường nhu cầu đều ghép được.

Website giữ J cố định để dạy cơ chế. Phân tích lý thuyết chọn J phụ thuộc ngân sách T và điều kiện của mô hình; kiểm tra J=6/9 trong repo không xác minh tốc độ regret. Cần đối chiếu bản cuối và supplement chính thức, chốt miền lệnh/định nghĩa coupling, rồi mới thiết kế thí nghiệm replication. Kế hoạch đó nằm trong [stress test](stress_test_plan.md); chưa chạy ma trận nghiên cứu.
