# Dẫn nguồn số liệu slide v4 và script tiếng Việt

Phạm vi: bản `v4_repo.pptx`, 38 slide; DOCX có lời thoại cho slide 1–31 và ghi
chú phụ lục. Số trang, lịch 60 phút và ngày trình bày là metadata/kế hoạch,
không phải kết quả thực nghiệm. Ví dụ tồn kho trên slide 3–4 là ví dụ giả định.

`check_evidence.py` đối chiếu **204 giá trị của toàn bộ 15 biểu đồ native** với
kết quả trong repo, sai số tối đa 0.00000051 vì dữ liệu chart làm tròn sáu chữ
số thập phân. Bảng và lời bình dùng cùng nguồn/công thức dưới đây; kiểm tra
chart không tự chứng nhận mọi câu diễn giải hoặc mọi con số trong bài báo.

Ký hiệu nguồn:

- **A**: [audit_results.json](../results/replication_audit/audit_results.json),
  trường `runs.synthetic`, `runs.rossmann`, `runs.rossmann_episode_start_sensitivity`;
  đây là snapshot lượt chạy trước, chưa chạy lại package INFORMS trong phiên này.
- **N**: [kết quả notebook quick](../results/five_experiments/),
  [configuration](../results/five_experiments/configuration.json),
  [manifest](../results/five_experiments/manifest.json) và
  [mã notebook](../notebooks/gong_simchi_5_experiments.ipynb).
- **B**: [benchmark thích nghi](../results/beer_rossmann/analysis_summary.json),
  [thiết kế](../benchmarks/beer_rossmann/config/preregistered_design.json),
  [mã/phạm vi CI](../benchmarks/beer_rossmann/README.md).
- **C**: [summary CFO](../results/cfo/summary.json),
  [giả định](../reports/cfo/assumptions.json), [bảng CFO](../results/cfo/).
  Tất cả VND/giá vốn/phạt thiếu hàng/chi phí hệ thống là **giả định mẫu**.
- **P**: Gong & Simchi-Levi (2024), Management Science 70(9), 6139–6157,
  [DOI](https://doi.org/10.1287/mnsc.2023.4947).
  Gói notebook chính thức từ [Supplemental Material](https://pubsonline.informs.org/doi/suppl/10.1287/mnsc.2023.4947),
  phiên bản nhận diện bằng SHA-256 trong [mã audit](../replication_audit/run_audit.py).
  Các cài đặt chỉ có trong notebook nguồn được dẫn tới gói này; không coi chúng
  là trường metadata đã được công cụ audit hiện tại lưu lại hoặc vừa xác minh.

| Slide / mục script | Loại số/nhận định | Nguồn và phép đối chiếu |
| --- | --- | --- |
| 1 | Tác giả, năm, tập/số/trang; ngày trình bày | P, thư mục tài liệu gốc; ngày 4/12/2026 là lịch tác giả đặt |
| 2 | Ba câu hỏi hướng D | [Định hướng D](../docs/research_direction_d.md); câu hỏi nghiên cứu, không phải kết quả |
| 3 | Công thức, ví dụ 6/10/12/8 | P §2 p.6142; [model.py](../lost_sales_lab/model.py); ví dụ minh họa q=max(B−x,0) |
| 4 | Stock/sales 10, counterfactual 8/15 | P §2 p.6143; đồng nhất thức true−pseudo=pD; ví dụ giả định, không phải mẫu dữ liệu |
| 5 | Alpha và cơ chế cập nhật/chuyển nhánh | P Algorithm 1 p.6146 và Algorithm 2 p.6150; tóm tắt tự soạn, không sao chép ảnh thuật toán |
| 6 | Định nghĩa regret và phạm vi bảo đảm | P §§2/5; không đưa cận số từ thí nghiệm thành định lý |
| 7 | H=5/7, T=5000/938; grid/threshold/preprocessing | A ghi H/T; P §6.1 p.6151 và các notebook `final_synthetic.ipynb`, `final_rossman.ipynb` có hash trong mã audit cho grid/threshold/Store 2; các chi tiết này chưa chạy lại ở phiên cloud hiện tại |
| 8 | Chuẩn benchmark | P §6.1, A findings; phân biệt policy khả thi, oracle DP và cận được chứng nhận |
| 9 | Tổng 59801/56470, seed 0 | A `runs.rossmann.learner.total`, `expert_advice.total`, `runs.synthetic.seed`; stored-output agreement theo báo cáo audit, không xác nhận mọi hình bài báo |
| 10 | 63.754/60.203/47.080/92.167; 30.8% | A `.mean` của learner/advice/near_OPT_vector/best_iid; giảm %=(best_iid−learner)/best_iid |
| 11 | Advice 5.6% | A `(learner.mean−expert_advice.mean)/learner.mean`; cùng 938 thời điểm |
| 12 | 0.64468/0.48668; [9,4,1,0,6] | A synthetic policy costs/targets; findings ghi lỗi container mẫu; chẩn đoán cùng đường cầu, không phải kết luận định lý |
| 13 | H7, cap32, h1, p4, 6 seed, 500 cycles, scales .05 | N `configuration.json`; khác cấu hình benchmark B |
| 14 | Curves, 6.524/7.399/3.696 | N `tn1_learning_curves.csv` và `summary_tn1_base.csv`; chart lấy ngày=7×cycle; trung bình trên 6 đường học |
| 15 | Ba biên độ; lợi ích .875, 11.8%, CI [.607,1.142] | N `tn1_independent_runs.csv` nhóm amplitude/policy; `tn1_cyclic_advantage.csv` tại amplitude=1: lợi ích=−gap, CI=−gap±ci95; % chia chi phí constant |
| 16 | Số ứng viên/bản sao, 33→3, 7→3 | N `tn2_trace_seed0.csv`; sample ngày=7×cycle, điểm cuối dùng ngày 3499 được gắn cycle499; không nhầm với đầu cycle499 |
| 17 | 35.8 switches, 51.8 waiting, 1.48%, high-stock1 | N `tn2_handoff_metrics.csv` lấy trung bình 6 seed; share=mean(waiting_days)/3500; chart x/y ngày138–159 trong trace seed0 |
| 18 | v=.1/.35/.65, cost và oracle gap, waiting | N `tn3_online_runs.csv` lọc penalty=4, nhóm volatility; các số waiting là trung bình theo seed |
| 19 | 18 ô, 4 profiles, 30 seeds, 21000/1400, 20 cấu hình | B thiết kế và selected configs; không gộp khảo sát 40 chuỗi ban đầu |
| 20 | 1.327/2.570 trong học; 1.209/.807 sau học; 18/18; 4/6 dài | B `core_means`, `online_counts`, `primary_counts`, `long_counts`; quyết định CI theo README benchmark |
| 21 | .815723/.806871, 1.1%, fill 87.0/88.7/88.0 | B `core_means`; giảm %=(weekday−MetaP)/weekday; fill=100×frozen_fill; point estimate không xác nhận tương đương từng ô |
| 22 | 100 SKU, 6.09/50/24/−67.91 triệu VND | C p=10: gain×100/1e6; setup/OPEX từ giả định; net=gross−setup−OPEX. Số lượng, giá vốn, h và lãi mất đều giả định |
| 23 | 5000 paths, 28 ngày, CVaR95 | N cấu hình `eval_paths`, `eval_horizon`; objective entropic trong notebook. Chow et al. (2015), [arXiv](https://arxiv.org/abs/1506.02188) là nguồn bối cảnh CVaR |
| 24 | Theta, mean/CVaR/fill, +3.45%/−7.56% | N `tn4_entropic_policies.csv`; % so theta .08 với0; fill trong cùng bảng, mục tiêu không phải tối ưu CVaR |
| 25 | r=0/.1/.2/.3, v=1000, K0/8 | N mã TN5 và `tn5_capital_policy_metrics.csv`; vốn là proxy trên tồn cuối ngày |
| 26 | Tồn 3.33/.89 và3.62/1.30, order79.53/90.06% | N `tn5_capital_policy_metrics.csv` theo fixed_cost, annual_rate; order_frequency×100 |
| 27 | Tồn13→14 và12→13; phase5/week2/K8 | N `tn5_action_value_gaps.csv` và mã TN5; đổi dấu delta giữa inventory liên tiếp ở r=0/.3, không phải stopping time ngẫu nhiên |
| 28 | Phạm vi bốn nhánh bằng chứng | A/N/B/C, các README tương ứng; không có số field-trial mới |
| 29 | Hướng nghiên cứu | P + [định hướng D](../docs/research_direction_d.md); các đề xuất chưa chạy |
| 30 | Bibliography và năm issue/online-first | DOI P; Beer [DOI](https://doi.org/10.1287/msom.2020.0939); Chow arXiv ở trên; bibliography không phải dữ liệu thực nghiệm |
| 31 | Kết luận phạm vi | A/N/B/C; ngày trình bày là metadata |
| 32 | Mô hình/đơn vị từng nhánh | A/N/B và mã mô hình, không trộn DP biết phân phối với learner |
| 33 | Algorithms1–2 | P pp.6146/6150; tóm tắt tự soạn thay ảnh chụp |
| 34 | Grid0–4/.2/H7,20 configs,21000; quick cap32/6/.05 | B thiết kế; N cấu hình; hai tham số hóa cận khác nhau |
| 35 | 63.753731/63.766525/+0.012794 | A Rossmann và episode-start sensitivity; lấy hiệu hai mean chưa làm tròn rồi làm tròn6 chữ số |
| 36 | Các hệ số .25/.5/1/2/4 và .5/1/2 | **Thiết kế đề xuất**, không phải kết quả đã chạy; validation/test độc lập |
| 37 | Phạm vi cận regret | P Table1 p.6142 và định lý đầy đủ; ảnh bảng không phân phối khi quyền chưa rõ; không suy từ audit về tính đúng định lý |
| 38 | Nguồn, 938 ngày, seed0 | A metadata; đường dẫn repo N/B/C đã cập nhật; hash bản gốc và bản phân phối trong `release_manifest.json` |

Thời lượng DOCX là lịch luyện tập do tác giả đề xuất, chưa được đo qua một buổi
thuyết trình. Các câu hỏi nghiên cứu, multiplier đề xuất và ví dụ giả định không
được tính như kết quả đã xác minh. Slide v4 nguyên bản có 22 ảnh nguồn; repo
chỉ chứa bản đã thay ảnh bằng diễn giải tự soạn có dẫn nguồn. Bản gốc giữ riêng.
