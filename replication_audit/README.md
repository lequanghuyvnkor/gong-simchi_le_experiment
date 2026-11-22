# Kiểm tra tái lập gói Gong–Simchi-Levi

Thư mục này chứa một công cụ kiểm tra chỉ đọc cho notebook và dữ liệu bổ sung chính thức của bài báo. Repo không sao chép notebook hay dữ liệu thuộc gói của tác giả.

## Lấy đầu vào

Mở trang bổ sung của INFORMS và tải **replication files**: [Supplemental Material and replication files](https://pubsonline.informs.org/doi/suppl/10.1287/mnsc.2023.4947). Giải nén để cùng một thư mục có bốn tệp:

```text
final_synthetic.ipynb
final_rossman.ipynb
rossman.csv
readme.pdf
```

Công cụ kiểm tra SHA-256 của cả bốn tệp trước khi chạy. Nếu checksum không trùng với snapshot được kiểm tra ở đây, chương trình dừng để tránh gắn nhãn nhầm phiên bản đầu vào.

## Chạy kiểm tra

Python 3.10 trở lên cùng NumPy, pandas và Matplotlib:

```powershell
python -m pip install numpy pandas matplotlib
python replication_audit/run_audit.py --package-dir "C:\path\to\extracted\package"
```

Kết quả JSON được ghi vào `results/replication_audit/audit_results.json`. Chương trình chạy từng ô mã trong namespace mới, đặt seed 0 cho phần synthetic, tắt hiển thị/lưu hình và xác nhận checksum đầu vào trước/sau không đổi. Một lượt tốn khoảng một phút trên môi trường đã dùng; máy chậm hơn có thể cần thêm thời gian.

## Kết quả và cách hiểu

`audit_results.json` ghi số liệu chạy lại cho synthetic và Rossmann, kiểm tra độ nhạy với chỉ số thời điểm bắt đầu episode, checksum, phiên bản thư viện và thời gian chạy.

Trong phần synthetic, hàm `DP()` trong notebook gốc ghi đè biến `Q_list` bên trong vòng lặp mẫu rồi mới tính `mean`. Phép kiểm tra độc lập trên cùng chuỗi cầu cho thấy policy đó có chi phí thực tế trung bình cao hơn một policy khả thi cố định `[9, 4, 1, 0, 6]`. Vì vậy nhãn “Lower Bound on OPT” cần được xác minh thêm bằng một benchmark độc lập; kết quả này chưa kết luận về định lý của bài báo.

Trong Rossmann, phép chạy lại tái tạo được tổng chi phí notebook đã lưu. Kiểm tra đổi chỉ số episode làm thay đổi rất nhỏ kết quả trung bình; riêng chênh lệch đó chưa phải phát hiện nghiên cứu có ý nghĩa. Notebook cũng phát sinh cảnh báo NumPy về trung bình của mẫu rỗng và cảnh báo pandas về cột có kiểu hỗn hợp; các cảnh báo được giữ trong JSON để người đọc thấy được.

Đây là kiểm tra ban đầu của mã bổ sung và các lựa chọn triển khai được nêu. Nó không xác nhận đầy đủ mọi hình trong bài báo, không xác minh chứng minh lý thuyết và không hàm ý các kết luận công bố sai.

## Nguồn

Xiao-Yue Gong và David Simchi-Levi, “Bandits atop Reinforcement Learning: Tackling Online Inventory Models with Cyclic Demands,” *Management Science* 70(9), 6139–6157 (2024), [DOI](https://doi.org/10.1287/mnsc.2023.4947). Trang INFORMS liệt kê gói replication dưới Supplemental Material.
