# Revisiting Meta-HQL: A Computational Replication and Sensitivity Study

**Định hướng nghiên cứu D — bản tổng hợp ngày 2026-11-23.** Nền kết quả là
snapshot repo `c6ab1d8`. Các số dưới đây được đối chiếu với JSON đã lưu; phiên
cloud này chưa chạy lại gói bổ sung chính thức vì chưa có đầu vào. Benchmark
Beer–Rossmann, phân tích CFO và slide v4 vẫn chờ các archive riêng.

## Mô hình và phạm vi cài đặt

Nhánh lost-sales xét một điểm tồn kho, một sản phẩm, bổ sung ngay: chọn mức
hàng `x_t <= y_t <= M`, đặt `q_t = y_t - x_t`, quan sát doanh số bị kiểm duyệt
`S_t = min(y_t, D_t)`. Tồn dư `I_t = y_t - S_t`, thiếu hàng mất đi
`L_t = max(D_t-y_t, 0)`, chi phí `h*I_t + p*L_t`. Bộ học chỉ nhận doanh số;
chi phí thay thế `h*I_t - p*S_t` khác chi phí thật bởi `p*D_t`, nên so sánh
chính sách trên cùng đường cầu có thể dùng chênh lệch chi phí thay thế.

HQL học theo episode; Meta-HQL phối hợp các bản sao dịch pha để giữ tồn qua
chu kỳ, kể cả ngày chờ chuyển nhánh. Lưới hữu hạn, hệ số cận và bảo vệ tập ứng
viên rỗng của bản học được mô tả trong [README ứng dụng](../lost_sales_lab/README.md)
và [mã Meta-HQL](../lost_sales_lab/meta_hql.py). Notebook thí nghiệm dùng một
biến thể thực hành khác; không coi mọi nhánh là cùng một cài đặt. Nhánh FQL
backlogging nhiều sản phẩm là mô hình riêng, không phải lost-sales này.

## Ba câu hỏi nghiên cứu

1. **Mức tái lập kết quả:** gói bổ sung có tái tạo được các bảng/hình và hành vi
   báo cáo trong bài khi cố định phiên bản, dữ liệu, seed và quy ước chỉ số không?
2. **Độ phù hợp của benchmark/cài đặt:** benchmark so sánh có thực sự là cận
   hay chính sách khả thi như được gắn nhãn, và các cài đặt có cùng thông tin,
   trạng thái đầu/cuối, đơn vị thời gian, ngân sách học và phạm vi chi phí không?
3. **Độ nhạy với confidence bound:** hệ số cận hành động và cận bandit ảnh
   hưởng thế nào tới loại ứng viên/nhánh, chi phí trong lúc học, sau học và
   tính ổn định trên các seed và chân trời khác nhau?

## Kết quả đã có bằng chứng trong repo

Bảng sau trích [snapshot audit](../results/replication_audit/audit_results.json).
Chi phí là đơn vị của thí nghiệm, **không phải VND**. Các trung bình hiển thị
làm tròn; JSON giữ độ chính xác gốc.

<!-- audit-evidence:start -->
| Chỉ tiêu | Giá trị | Trường JSON nguồn |
| --- | ---: | --- |
| Synthetic: số thời điểm | 5000 | [`runs.synthetic.T`](../results/replication_audit/audit_results.json) |
| Synthetic: chi phí trung bình bộ học | 0.84214 | [`runs.synthetic.learner.mean`](../results/replication_audit/audit_results.json) |
| Synthetic: chi phí trung bình policy DP notebook | 0.64468 | [`runs.synthetic.author_DP_policy_realized_cost.mean`](../results/replication_audit/audit_results.json) |
| Synthetic: chi phí trung bình policy khả thi đối chiếu | 0.48668 | [`runs.synthetic.candidate_feasible_policy.mean`](../results/replication_audit/audit_results.json) |
| Rossmann: số thời điểm | 938 | [`runs.rossmann.T`](../results/replication_audit/audit_results.json) |
| Rossmann: tổng chi phí bộ học | 59801 | [`runs.rossmann.learner.total`](../results/replication_audit/audit_results.json) |
| Rossmann: tổng chi phí vector mang nhãn near_OPT | 44161 | [`runs.rossmann.near_OPT_vector.total`](../results/replication_audit/audit_results.json) |
| Rossmann: tổng chi phí sau đổi chỉ số episode | 59813 | [`runs.rossmann_episode_start_sensitivity.learner.total`](../results/replication_audit/audit_results.json) |
<!-- audit-evidence:end -->

Snapshot synthetic ghi seed và policy đối chiếu tại `runs.synthetic`. Trên
cùng đường cầu, policy khả thi đối chiếu có chi phí thấp hơn policy DP được
notebook tạo ra. Audit ghi nhận việc `Q_list` bị gán đè trong vòng lặp lấy mẫu;
vì vậy đối tượng gắn nhãn “Lower Bound on OPT” cần benchmark độc lập trước
khi dùng làm cận được chứng nhận. So sánh này là bằng chứng về lần chạy và
đường mã đã kiểm tra, không chứng minh vi phạm định lý hoặc thứ hạng kỳ vọng.

Snapshot Rossmann ghi nhận tổng chi phí notebook được tái tạo. Đổi chỉ số
bắt đầu episode làm thay đổi tổng trong bảng; chênh lệch nhỏ trên một lần chạy
chưa đủ để khẳng định ý nghĩa thống kê hay giá trị nghiên cứu. “near_OPT” là
nhãn biến trong notebook, chưa phải chứng nhận tối ưu. Xem [phạm vi audit và
cảnh báo](../replication_audit/README.md); phiên bản phần mềm, checksum nguồn
và các cảnh báo nằm trong JSON nguồn.

[Notebook năm thí nghiệm](../notebooks/gong_simchi_5_experiments.ipynb) có kết
quả chế độ quick với biến thể Meta-HQL thực hành và các mở rộng DP biết phân
phối; [cấu hình](../results/five_experiments/configuration.json) và
[manifest](../results/five_experiments/manifest.json) xác định phạm vi từng bảng.
[Thí nghiệm alpha](../experiments/alpha_sensitivity/run_alpha_demo.py) thay
lịch alpha của HQL rời rạc, có thiết kế đường cầu ghép cặp, cấu hình hệ số cận
và [kết quả riêng](../results/alpha_sensitivity/summary.csv). Các hệ số nhỏ là
minh họa thực nghiệm, không kế thừa bảo đảm lý thuyết. Đây chưa phải sweep đầy
đủ hệ số confidence bound của Meta-HQL trên benchmark Beer–Rossmann.

## Giả thuyết và công việc tiếp theo

**Giả thuyết cần kiểm tra:** cận lớn có thể duy trì khám phá lâu trong ngân
sách hữu hạn; cận nhỏ có thể giảm chi phí sớm nhưng tăng rủi ro loại hành động
tốt. Tác động còn phụ thuộc lưới, chân trời, alpha và lịch chuyển bản sao.
Đây là giả thuyết nghiên cứu, chưa phải kết luận từ benchmark bị thiếu.

Trước tiên chạy lại gói chính thức với checksum đã lưu; tách nhánh giữ nguyên
mã tác giả khỏi từng sửa đổi. Xây benchmark DP độc lập trên các trường hợp
nhỏ giải chính xác được, kiểm tra giá trị policy và quy ước terminal trước khi
đọc regret. Sau đó thiết kế sweep cận hành động/bandit, giữ seed ghép cặp,
công bố chi phí học và chính sách đóng băng sau học, CI theo đơn vị lặp độc lập.
Chọn tham số trên train/validation rồi đánh giá test riêng.

Khi nhận archive, kiểm tra **SRDQN-A thích nghi** và **Meta-HQL-P thích nghi cho
một điểm tồn kho/một sản phẩm**, phân biệt khảo sát ban đầu với benchmark chính
theo [hướng dẫn đợt 3](../benchmarks/beer_rossmann/README.md). Chưa có bằng chứng
để nêu thuật toán nào thắng benchmark này. [CFO](../reports/cfo/README.md) cần
giả định mẫu và dữ liệu riêng, không suy từ chi phí audit sang doanh nghiệp.

## Đối chiếu và nguồn

Python **3.10+**, chỉ thư viện chuẩn, từ clone sạch:

```bash
python --version
python tools/check_research_brief.py
```

Công cụ so bảng với JSON, kiểm tra phép chia tổng/số mẫu và cờ checksum trong
snapshot, rồi in SHA-256 JSON. Nó không chạy lại notebook, không đọc slide còn
thiếu và không xác minh chứng minh lý thuyết. Lệnh tái chạy gói gốc và dependencies
NumPy/pandas/Matplotlib ở [README audit](../replication_audit/README.md).

Nguồn bài báo: Xiao-Yue Gong và David Simchi-Levi, “Bandits atop Reinforcement
Learning: Tackling Online Inventory Models with Cyclic Demands,” *Management
Science* (2024), [DOI 10.1287/mnsc.2023.4947](https://doi.org/10.1287/mnsc.2023.4947).
Nhận định audit liên quan mã bổ sung và lựa chọn triển khai đã nêu; nghiên cứu
D chưa xác minh hoặc bác bỏ các định lý của bài báo.
