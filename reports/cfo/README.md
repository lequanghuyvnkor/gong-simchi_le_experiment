# Đợt 4 — Phân tích CFO

Đã lấy mã, cấu hình, bảng và phần C của báo cáo từ ZIP nhúng trong PDF chủ dự
án cung cấp. Bản gốc vẫn ở `/workspace/inputs/beer_rossmann_archive/embedded_package/`.
`provenance.json` ghi hash và đường dẫn nguồn của mã. [Báo cáo CFO lưu trữ](archive_report.md)
được giữ như bản phân tích **hậu kiểm** với giả định gốc; không tự đổi số trong
báo cáo này khi dùng cấu hình mới.

**Toàn bộ giá trị VND, giá vốn, phạt thiếu hàng và phí hệ thống là giả định mẫu,
không phải chi phí quan sát hay hóa đơn của doanh nghiệp thật.** Mọi CSV được
phân phối hoặc xuất mới có cột `assumption_status=HYPOTHETICAL_NOT_STORE_ACTUALS`.

## Chạy từ clone sạch và thay giả định

Python **3.10+**, NumPy và pandas; khi chạy lại benchmark cần cả Matplotlib.
R không thay thế Python. Từ gốc repo đã clone:

```bash
python --version
python -m pip install -r benchmarks/beer_rossmann/requirements.txt
python reports/cfo/calculate.py --output-dir local_checks/cfo --verify-default
```

Lệnh tải metric nhỏ trong repo (không cần raw Beer/Rossmann), tính lại bootstrap,
phép đổi VND, bảng 18 điều kiện, ba mức p, pilot đã lưu và portfolio/TCO. Bốn
bảng lưu trữ cùng summary được so trong dung sai `rtol=1e-9, atol=1e-6`.
Kết quả nguồn ở [results/cfo](../../results/cfo/); đầu ra mới và phiên bản phần
mềm ở thư mục chỉ định. `report.md` mới ghi giả định hiệu lực, cách tính và giới
hạn; `effective_assumptions.json` giữ toàn bộ cấu hình lần chạy.

Để thay giả định, sao chép `reports/cfo/assumptions.json` sang tệp riêng rồi sửa
các giá trị và chạy:

```bash
python reports/cfo/calculate.py --assumptions /path/to/my_assumptions.json --output-dir local_checks/cfo_custom
```

Có thể đổi nhu cầu mốc, giá vốn, lãi đóng góp, giữ hàng, số kỳ/năm, chi phí setup,
vận hành hệ thống, chiết khấu và số SKU giả định. Phải giữ quan hệ:
`lost_contribution = selling_price - purchase_cost - avoidable_fulfilment`;
`p = lost_contribution / holding_cost` phải thuộc {1,5,10} đã chạy;
sức chứa vật lý = 4 × nhu cầu mốc. Lãi mất từng hàng p được ghi riêng bằng p×h.
Thay p ngoài miền, lead time, lưới/cap chuẩn hóa hoặc drift cần học/đánh giá lại,
không nhân số cũ để gọi là kết quả chính sách mới. Công cụ từ chối tỷ số không
khớp, giả định phi hữu hạn, quy mô không hợp lệ và dự báo drift không có dữ liệu.

## Phân biệt các kết quả

| Tệp | Ý nghĩa và giới hạn |
| --- | --- |
| `18_condition_financial_scenarios.csv` | Policy đóng băng sau 21,000 kỳ; nhân chi phí chuẩn hóa với m×h×số kỳ. CI ghép cặp theo seed, profile cố định, Bonferroni 18 ô |
| `p_level_financial_scenarios.csv` | Gộp cân bằng sáu ô mỗi p; CI 95% hậu kiểm, không phải cơ cấu thị trường thực |
| `pilot_financial_summary.csv` | Chi phí **trong học** tại 30/90/365 kỳ của lần học biết trước chân trời 365; không phải pilot cửa hàng hoặc lần học với chân trời 30/90 |
| `illustrative_portfolio_tco.csv` | Lợi ích **tăng thêm** so với weekday, net năm đầu, NPV ba năm và payback đơn giản; không gồm tiền vận hành giả lập khi train offline |
| `tco_components.csv` | Bảng mới tách vận hành Meta/baseline, setup, phí hệ thống, TCO năm đầu, tránh nhầm lợi ích tăng thêm với tổng chi phí |
| `summary.json` | Ngưỡng quy mô, sample B ngoài miền p và số kỳ hòa vốn online/frozen; các đơn vị khác nhau cần đọc riêng |

Sample gốc: m=100 đơn vị/ngày, h=100 VND/đơn vị/ngày, p=10, giá vốn 50,000,
giá bán 55,000, phí phục vụ tránh được 4,000, lãi mất 1,000 VND. Setup 50 triệu,
vận hành hệ thống 24 triệu/năm, chiết khấu 12%. Các giá trị được giữ tại
`assumptions.json`, không lấy từ dữ liệu Beer/Rossmann. Lợi ích policy sau học
so với weekday khoảng 60,893.87 VND/SKU/năm; với 100 SKU giống nhau độc lập,
net năm đầu khoảng −67.91 triệu VND. Xem bảng/summary để đọc số chưa làm tròn.

Học offline: chi phí tồn/thiếu trong simulator là chỉ tiêu mô hình; chỉ compute,
nhân sự, tích hợp và kiểm chứng mới có thể là khoản tiền dự án giả định. Học
khi vận hành: cần chi phí tăng thêm so với baseline trên đúng cùng kỳ; không
cộng lại khoản đã nằm trong vận hành hoặc pilot. Chi phí thực compute/giờ lao
động chưa được đo. Bảng pilot giả định VND còn chưa có phí công nghệ.

Hòa vốn sau 21,000 kỳ dùng chi phí học của cả chân trời đó chia lợi ích frozen
so với DQN; đây là chỉ tiêu mô hình, **không** phải hòa vốn đầu tư theo lịch.
Payback đầu tư dùng setup/(tiết kiệm năm trừ OPEX), chỉ có khi mẫu số dương;
ngưỡng SKU dùng giả định các SKU giống nhau độc lập. NPV ba năm dùng dòng tiền
cuối năm, không thuế/working capital/drift. Giải phóng vốn từ tồn cuối kỳ chỉ
là proxy một lần, không cộng như tiết kiệm lặp lại hàng năm.

## Chạy lại pilot và báo cáo gốc

`pilot_cost_study.py` giữ nguyên bộ sinh và cấu hình đã khóa: 18 ô × 4 profile ×
30 seed 6000–6029, ba checkpoint 30/90/365; baseline có lịch sử riêng ưu đãi.
Từ run-dir benchmark đã được khởi tạo bằng lệnh `snapshot`:

```bash
# Linux/macOS; PowerShell đặt $env:GONG_RUN_DIR trước khi gọi python.
GONG_RUN_DIR=/tmp/gong-run python reports/cfo/pilot_cost_study.py
GONG_RUN_DIR=/tmp/gong-run python reports/cfo/archive_analyze_cfo.py
```

Khởi tạo `/tmp/gong-run` trước bằng
`python benchmarks/beer_rossmann/run.py snapshot --run-dir /tmp/gong-run`.
`archive_analyze_cfo.py` luôn dùng giả định **gốc** và dựng
`work/combined_report_build/cfo_addition.md`; muốn thay giả định dùng `calculate.py`.
Không cần Pandoc/Chrome để tái tạo bảng hay Markdown CFO; xuất PDF gốc cần các
công cụ trình bày đó và không nằm trong lệnh kiểm tra mặc định.

## Đã kiểm tra và giới hạn

Đã tái tạo bốn bảng và summary từ clone sạch với Python 3.12.14, NumPy 2.3.5,
pandas 2.2.3. Đã thử cấu hình setup/OPEX bằng 0 và kiểm tra net theo phép tính,
và xác nhận cấu hình p không khớp bị từ chối. Phạm vi chạy pilot mới và so sánh
với archive được ghi tại `results/cfo/cloud_validation.json`. Không coi việc
khớp bảng là xác minh chi phí doanh nghiệp, ROI thực hoặc kết luận định lý.
