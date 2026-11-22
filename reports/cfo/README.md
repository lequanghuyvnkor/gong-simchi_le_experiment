# Đợt 4 — Phân tích CFO (chưa hoàn tất)

Chưa tìm thấy `inputs/beer_rossmann_archive/` trong phiên cloud ngày 2026-11-23.
Vì vậy chưa đọc/đóng gói được mã CFO, cấu hình, bảng hay báo cáo từ archive;
chưa có kết quả VND, TCO hoặc điểm hòa vốn được xác minh ở đây. Tài liệu này
ghi quy ước cần đối chiếu khi nhận đầu vào, không thay thế phân tích CFO gốc.

Chủ dự án đã xác nhận ZIP chứa CFO còn trên Windows; xem tên tệp và đích
cloud trong [hướng dẫn chuyển đầu vào](../../docs/input_handoff.md).

## Phạm vi diễn giải

**Mọi giá trị VND, giá vốn, phạt thiếu hàng và chi phí hệ thống trong phân tích
CFO dự kiến đều là giả định mẫu**, trừ khi có nguồn doanh nghiệp riêng được
xác minh và được phép sử dụng. Hiện không có nguồn đó trong repo. Không mô tả
các giả định là chi phí quan sát của doanh nghiệp thật, hoặc suy ra lợi nhuận
thực tế từ kết quả mô phỏng tồn kho.

Các bảng notebook TN5 hiện có là thí nghiệm chi phí vốn với phân phối biết
trước; chúng không phải bảng CFO Beer–Rossmann. Kết quả audit Rossmann cũng
không phải hóa đơn VND hay bằng chứng triển khai thương mại.

## Các khoản cần tách trong báo cáo

| Khoản | Nội dung và đơn vị cần công bố | Điều cần đối chiếu trong archive |
| --- | --- | --- |
| Sau học | Chi phí vận hành của chính sách đóng băng trên kỳ đánh giá; VND/điểm tồn kho/ngày hoặc VND/kỳ | Không cập nhật tham số trên test; ghi số ngày và số điểm/SKU |
| Trong lúc học | Chi phí vận hành phát sinh khi quyết định còn dùng để học | Tách chi phí vận hành khỏi tiền compute/nhân sự dùng huấn luyện |
| Chi phí tăng thêm do học | Chi phí vận hành học trừ chi phí baseline trên cùng kỳ và đường cầu | Có thể âm; không tự chặn về 0; không cộng lại nếu đã nằm trong tổng vận hành |
| Hệ thống | Compute train/inference, tích hợp ban đầu, hạ tầng, bảo trì và nhân sự | Nêu khoản một lần, định kỳ, phạm vi phân bổ; tất cả là giả định mẫu |
| TCO | Tổng các khoản vận hành và hệ thống thuộc cùng kỳ phân tích | Ghi rõ có gồm giai đoạn học, vốn lưu động, chiết khấu và thuế không |
| Hòa vốn | Kỳ đầu lợi ích lũy kế so với baseline bù chi phí tăng thêm | Có trường hợp không hòa vốn trong chân trời phân tích |

## Quy ước tính cần kiểm tra trước khi dùng số VND

Đây là các đồng nhất thức kế toán tham chiếu, chưa phải mô tả đã xác minh của
mã CFO gốc. Khi nhận archive, cần ghi rõ mã nào thực hiện mỗi khoản và giải
thích mọi khác biệt.

Với tồn cuối `I`, thiếu hàng `L`, lượng mua `q`, chi phí vận hành mẫu có thể
được định nghĩa là `h_VND * I + p_VND * L + c_VND * q` khi cả ba khoản đều
thuộc phạm vi. Mô hình lost-sales trong [ứng dụng](../../lost_sales_lab/README.md)
hiện đặt giá mua chuẩn hóa bằng 0 và dùng `h*I + p*L`. Chi phí quan sát thay thế
`h*I - p*S` không phải tổng chi phí kế toán. Không thể tự chuyển mọi bảng sang
VND bằng một hệ số nếu giá vốn, nhu cầu, lượng mua hoặc quy ước terminal thay đổi.
Thay trọng số h/p còn có thể đổi chính sách tối ưu và đòi hỏi học/đánh giá lại.

Trên cùng kỳ phân tích và cùng phạm vi chi phí:

```text
TCO_policy = operating_cost_during_learning
           + operating_cost_after_learning
           + system_cost_once + system_cost_recurring
net_benefit = TCO_baseline - TCO_policy
```

Nếu học offline, không gán chi phí vận hành giả lập trong train thành khoản
tiền đã chi thật: ghi nó như chỉ tiêu mô phỏng riêng; chi phí compute train
vẫn có thể được giả định trong TCO. Nếu học khi vận hành, công bố cả kỳ học
của policy lẫn baseline cùng kỳ. Tiền compute đã tính trong hệ thống không
được cộng thêm lần nữa dưới nhãn “chi phí học”.

Hòa vốn trong trường hợp dòng tiền không đều là kỳ đầu mà `TCO_baseline(t) -
TCO_policy(t) >= 0`, xét từ khi bắt đầu dự án có khoản đầu tư. Nêu rõ cách xử
lý trường hợp bằng 0 trước đầu tư, chênh lệch quay lại âm và chiết khấu nếu có.
Công thức rút gọn `t = F / s` chỉ dùng khi F là toàn bộ chi phí tăng thêm ban
đầu, s là tiết kiệm ròng cố định mỗi kỳ sau đó và `s > 0`; phải nêu quy tắc
làm tròn kỳ và kỳ bắt đầu. Không biến khoảng tin cậy chi phí thành CI cho
`F/s` bằng phép chia trực tiếp, nhất là khi s gần hoặc đi qua 0.

Giữ bảng theo điều kiện và seed/đường cầu ghép cặp trước khi gộp. Chi phí VND,
TCO và hòa vốn cần ánh xạ về đúng benchmark và ngân sách học; không gộp khảo
sát ban đầu với benchmark chính. Phương pháp CI phải theo thiết kế và mã gốc
được kiểm tra; chưa có dữ liệu để chọn hoặc khẳng định một phương pháp ở đây.

## Đầu vào cần bổ sung và cách chạy từ clone sạch

Cần nguyên `inputs/beer_rossmann_archive/`, gồm README, checksum, mã/cấu hình CFO
trong `work/`, bảng và báo cáo tương ứng trong `outputs/`. Chưa biết tên tệp CFO
cụ thể trước khi đọc archive. Giữ bản gốc ngoài Git và không chỉnh sửa nó.

Python **3.10+**. Phần tiếp nhận hiện có chỉ dùng thư viện chuẩn:

```bash
git clone https://github.com/lequanghuyvnkor/gong-simchi_le_experiment.git
cd gong-simchi_le_experiment
python --version
python tools/inspect_inputs.py --inputs-dir /workspace/inputs --require benchmark
```

Thay đường dẫn theo nơi lưu thực tế. Mã thoát 2 khi chưa có archive là tình
trạng bị chặn, không phải CFO đã tái tạo thành công. Công cụ không chạy mã CFO.
Chưa xác định dependencies, tệp cấu hình hoặc lệnh chạy CFO thực tế; không
giả định cài R là đủ, và không đưa lệnh pipeline phỏng đoán vào hướng dẫn.

Khi có đầu vào, cần đóng gói các tệp được phép phân phối và hoàn tất quy trình:

1. Lập bảng ánh xạ từng bảng báo cáo tới mã, cấu hình, kết quả benchmark nguồn,
   checksum và phiên bản Python/thư viện đã dùng.
2. Tập trung giả định vào cấu hình chỉnh được: đơn vị VND, giá vốn, h/p,
   số điểm/SKU/ngày, ngân sách học, chi phí hệ thống, kỳ phân tích/chiết khấu.
   Nhãn **giả định mẫu** phải hiện trong bảng xuất, không chỉ trong README.
3. Ghi rõ tham số nào chỉ cần tính lại kế toán và tham số nào buộc chạy lại
   policy; lưu cấu hình đã thay cùng bảng kết quả mới.
4. Từ clone sạch: cài dependencies Python, nối dữ liệu ngoài Git sau khi xác
   minh checksum, chạy cấu hình gốc ra thư mục riêng và đối chiếu các bảng
   trong archive với dung sai công bố. Sau đó chạy một cấu hình đổi giả định
   để xác nhận bảng được tái tạo theo thay đổi đó.
5. Kiểm tra TCO không đếm trùng, baseline cùng kỳ, hòa vốn có/không đạt, giới
   hạn dữ liệu và cách ước lượng độ bất định trước khi đánh dấu hoàn tất.

## Kiểm tra phần tài liệu

Ngày 2026-11-23: kiểm tra đường dẫn liên kết và chạy lệnh tiếp nhận trên clone
sạch áp bản diff tài liệu, Python 3.12.14, thư viện chuẩn. Đầu vào cloud chưa
có nên công cụ trả mã 2. Chưa chạy tính CFO, tái tạo bảng, thay cấu hình thực tế
hoặc kiểm tra dependencies CFO; đợt 4 vẫn chưa hoàn tất.
