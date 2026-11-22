# Đợt 3 — Benchmark Beer–Rossmann

Đã nhận báo cáo 41 trang và README nguồn. PDF nhúng ZIP `ma_du_lieu_va_ket_qua.zip`
(SHA-256 `c47bb483fb54c63cc5401a39618656bc6befcd45e9773bd53c16ea0973df22b7`),
chứa đủ `work/` và `outputs/`. Bản gốc giữ tại
`/workspace/inputs/beer_rossmann_archive/embedded_package/`, ngoài Git.
`provenance.json` ghi hash PDF, ZIP, mã nguồn và các thay đổi để chạy đa nền tảng.

## Nội dung và giới hạn

Mã do dự án cung cấp: `research_run.py` chuẩn bị dữ liệu/khảo sát ban đầu;
`condition_study.py` thiết kế, bộ sinh, SRDQN-A thích nghi, Meta-HQL-P thích nghi,
Meta-HQL-T và baseline; `analyze_conditions.py` phân tích ghép cặp/bootstrap.
Chỉ thay gốc ghi kết quả và đường dẫn import; giữ nguyên công thức thuật toán,
seed, cấu hình và cách suy luận thống kê. Đây **không phải mã chạy nguyên gốc**
của hai bài báo. Không kèm mã tác giả Beer Game hoặc gói INFORMS.

Cả hai bản thích nghi dùng một điểm tồn kho/một sản phẩm, lost-sales, lead time 0,
giữ tồn, H=7 biết trước, lưới 0–4 bước 0.2, h=1, p∈{1,5,10}. Bộ học nhận doanh số
riêng bị kiểm duyệt, không nhận nhu cầu thật để học. SRDQN-A dùng lịch sử ba kỳ,
pha tuần, DQN NumPy và pseudo-reward được căn giữa; Meta-HQL-P đổi cận hành động/
bandit bằng hệ số chọn trên validation, loại bản sao khi chặn rỗng và giữ tập cũ
nếu đó là bản sao cuối. Các bảo vệ được đếm. Không kế thừa bảo đảm lý thuyết.

| Nhánh | Ngân sách và cài đặt | Diễn giải |
| --- | --- | --- |
| Khảo sát ban đầu | 40 chuỗi; 7,000 kỳ, pilot dài 21,000; seed 0–29; DQN khác và Meta theo cận lý thuyết, không loại được ứng viên trong chân trời này | `results/beer_rossmann/initial_survey/`; không gộp với nghiên cứu chính |
| Chính | 18 ô: a∈{0,.4,.8}, CV∈{.25,.75}, p∈{1,5,10}; 4 profile cố định; seed 1000–1029; 21,000 kỳ học, test policy đóng băng trên 1,400 kỳ mới | Chi phí học và sau học riêng; chọn 20 cấu hình mỗi thuật toán trên validation riêng |
| Dài | 6 ô chọn trước, profile 0, seed 3000–3029, 70,000 kỳ | 4 ô nghiêng rõ Meta-P, 2 chưa rõ |
| Chuyển nguồn | Beer 30 chuỗi và Rossmann 10 cửa hàng mới; p=1; học từ phân phối theo thứ năm 2013 | Beer test 2016–2017, Rossmann test 2015; không phải pilot cửa hàng |

Các giá trị trên lấy từ `config/preregistered_design.json`, cấu hình đã khóa và
các JSON/CSV trong [kết quả](../../results/beer_rossmann/). Tên “preregistered” là
dấu vết nội bộ, không phải đăng ký độc lập. Rossmann là doanh thu đại diện cầu;
không xác định lost demand thực. Baseline `Prior weekday` có lịch sử riêng được
ưu đãi, không phải cold-start như hai learner.

## Chạy từ clone sạch: không cần dữ liệu bên thứ ba

Python **3.10+**, NumPy, pandas, Matplotlib; R không thay thế được Python.

```bash
git clone https://github.com/lequanghuyvnkor/gong-simchi_le_experiment.git
cd gong-simchi_le_experiment
python --version
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r benchmarks/beer_rossmann/requirements.txt
python benchmarks/beer_rossmann/run.py snapshot --run-dir local_checks/beer_rossmann
python benchmarks/beer_rossmann/run.py smoke --run-dir local_checks/smoke
```

`snapshot` khôi phục các bảng **chỉ tiêu chính sách** từ 14 NPZ nhỏ, không pickle,
không chứa doanh số hay đường cầu nguồn. Chạy lại toàn bộ bootstrap, kiểm tra
phân rã chi phí/bounds/trùng khóa, đối chiếu sáu CSV với snapshot ở dung sai
`rtol=atol=1e-9`. Kết quả mới nằm trong run-dir; JSON ghi phiên bản Python/NumPy/
pandas. `smoke` kiểm tra ba bộ học trên 700 kỳ, hai seed, tính xác định/ghép cặp,
đồng nhất thức chi phí và phản hồi một phía; không dùng làm kết quả 18 ô.

Phân tích chính: trước hết lấy trung bình trên bốn profile cố định theo seed,
rồi bootstrap ghép cặp 30 seed, 20,000 mẫu. Effect = 100(S−M)/((S+M)/2).
CI percentile dùng alpha=.05/18 và quy tắc thực hành ±5%; CI vượt +5% mới
kết luận nghiêng Meta-P. Nhánh dài dùng .05/6; kiểm tra nguồn dùng .05/2,
bootstrap chéo cửa hàng và seed, item Beer gộp trong cửa hàng. Không coi ngày,
profile hoặc item cùng cửa hàng là các lần lặp độc lập.

Đối chiếu lưu trữ xác nhận Meta-P nghiêng rõ ở 18/18 ô **sau học**; SRDQN-A
nghiêng rõ ở 18/18 ô **trong học**. Không diễn giải thành thứ hạng phổ quát.

## Dữ liệu ngoài Git và chạy học đầy đủ

Chưa xác định quyền phân phối CSV nguồn: không đưa CSV, phân phối thực nghiệm,
đường cầu lấy mẫu, ZIP/PDF có dữ liệu nhúng hoặc hình của bên thứ ba lên repo.
Nguồn tải theo báo cáo (không khẳng định quyền tải lại/phân phối):

- Beer: [Kaggle](https://www.kaggle.com/competitions/demand-forecasting-kernels-only/data),
  bản dùng từ [mirror tại commit cố định](https://github.com/nimanov/Demand-Forecasting-using-LightGBM/blob/1cd0e8ec5446fb09e421f2ac68cb801738a7bf8c/train.csv).
- Rossmann: [Kaggle](https://www.kaggle.com/competitions/rossmann-store-sales/data),
  [mirror được báo cáo](https://github.com/juniorcl/rossman-store-sales/tree/main/databases).
  Mirror chưa có commit khóa; dùng checksum để nhận đúng snapshot.

| Tên nối vào run-dir | Cấu trúc | SHA-256 |
| --- | --- | --- |
| `outputs/datasets/store_item_demand_train.csv` | date,store,item,sales; 913000 dòng | `84cd0e7e8f1d2bddfa0b5f184c64ea8ec9cca0878e35b0aae8c9b719db853a2d` |
| `outputs/datasets/rossmann_train.csv` | Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday; 1017209 dòng | `608e4d8ff855465c1ff4f95874b9a35da40c6bedacd7d1f308fe37dba675a39e` |

Có thể lấy đúng snapshot từ ZIP nhúng trong PDF được chủ dự án cấp riêng:

```bash
python -m pip install pypdf
python benchmarks/beer_rossmann/extract_inputs.py --pdf /path/to/bao_cao_tong_hop_du_lieu_va_thuat_toan.pdf --destination /tmp/gong-inputs
python benchmarks/beer_rossmann/link_data.py --beer /tmp/gong-inputs/outputs/datasets/store_item_demand_train.csv --rossmann /tmp/gong-inputs/outputs/datasets/rossmann_train.csv --run-dir local_checks/full
python benchmarks/beer_rossmann/run.py prepare-data --run-dir local_checks/full
python benchmarks/beer_rossmann/run.py core --block 0 --run-dir local_checks/full
```

Lặp `core --block N` cho N=0..5; tương tự `long --block N`; chạy `source-beer`,
`source-ross`. Cấu hình khóa được nối tự động từ `config/`. Muốn tái tuning,
dùng run-dir mới và `tune-dqn`, `tune-meta`, `gate-selected`; kết quả này là lần
chọn mới, không tự mang nhãn cấu hình khóa cũ. Khảo sát ban đầu có CLI riêng:
đặt biến `GONG_RUN_DIR` trỏ run-dir rồi chạy `research_run.py prepare`, `tune`,
`synthetic`, `long`, `historical`, `check`, `direct`, `sensitivity` theo thứ tự
phụ thuộc; không cộng kết quả với nghiên cứu chính.

## Xác minh trong cloud

Đã tái phân tích các metric lưu trữ và đối chiếu bảng chính. Manifest archive
có một hash `qa_report.json` không khớp nội dung nhận được; ghi đầy đủ trong
`provenance.json`, không chứng nhận toàn bộ archive nguyên vẹn. Hai đường dẫn
`datasets/` của manifest được giải theo `outputs/` và khớp checksum. Các bảng
chỉ tiêu, cấu hình khóa, phép phân rã và kết quả bootstrap được kiểm tra riêng.
Chưa huấn luyện lại toàn bộ 83,160,000 tương tác mỗi thuật toán. Xem
`results/beer_rossmann/cloud_validation.json` cho phạm vi chạy thực tế.

Sau khi đủ cả 6 block core, 6 block dài và 2 nguồn, phân tích lần học mới bằng
`python benchmarks/beer_rossmann/run.py analyze --run-dir local_checks/full`.
Lệnh `snapshot` luôn dùng metric lưu sẵn; dùng run-dir riêng để không ghi đè
metric của một lần huấn luyện mới.
