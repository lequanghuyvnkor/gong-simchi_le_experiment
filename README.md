# Gong & Simchi-Levi: học thuật toán tồn kho theo nhu cầu chu kỳ

Repo này tập hợp ứng dụng học mô hình tồn kho, website bốn mô hình, notebook thí nghiệm và hồ sơ thực nghiệm. Tài liệu, giao diện và hướng dẫn hiện viết bằng tiếng Việt.

**Mở [Inventory Lab trên cloud](https://gong-simchi-inventory-lab.snu-chatgpt-5678.chatgpt.site)** — Site riêng tư, có HQL, Meta-HQL, FQL và bản học Mimic-QL; bốn video sơ đồ hệ thống, chạy từng ngày, phát lại Q và xuất CSV. [Cách dùng, dựng lại và giới hạn](inventory_site/README.md).

Người chuẩn bị thuyết trình xem [playbook experimental tiếng Việt](reports/experimental_presenter/README.md) ([PDF](reports/experimental_presenter/experimental_presenter_playbook_vi.pdf), [DOCX](reports/experimental_presenter/experimental_presenter_playbook_vi.docx)): lộ trình 60/40 phút, lập luận từ bằng chứng, demo và phản biện. [Kế hoạch stress test](docs/stress_test_plan.md) có 32 test ID và thiết kế seed/split; đây là kế hoạch, chưa phải kết quả chạy ma trận.

## Nội dung

- [`lost_sales_lab/`](lost_sales_lab/README.md): ứng dụng Streamlit giải thích HQL, Meta-HQL và FQL; các lõi Python dùng chung với website. Mimic chỉ có trên website/lõi mới, dưới dạng [teaching adaptation](docs/mimic_teaching_scope.md), chưa phải replication công bố.
- [`inventory_site/`](inventory_site/README.md): mã nguồn Site bốn mô hình, video diagram không lời/phụ đề và trace xác định.
- [`notebooks/gong_simchi_5_experiments.ipynb`](notebooks/gong_simchi_5_experiments.ipynb): năm thí nghiệm minh họa cho bài trình bày 45 phút, gồm lợi ích nhu cầu chu kỳ, chuyển giao tồn kho, biến động, rủi ro và chi phí vốn.
- [`experiments/alpha_sensitivity/run_alpha_demo.py`](experiments/alpha_sensitivity/run_alpha_demo.py): so sánh năm công thức alpha trên năm kịch bản nhu cầu.
- [`replication_audit/`](replication_audit/README.md): công cụ chạy kiểm tra chỉ đọc trên gói bổ sung chính thức, kèm checksum và kết quả kiểm tra đã lưu.
- [`results/five_experiments/`](results/five_experiments/): cấu hình, bảng CSV và hình của lần chạy notebook chế độ nhanh.
- [`results/alpha_sensitivity/`](results/alpha_sensitivity/): cấu hình, báo cáo, bảng kết quả, hình và dấu vết mô phỏng alpha đã lưu.

## Tiến độ đợt 3–5 trong cloud

- **Đợt 3: đã đóng gói và kiểm tra phân tích kết quả lưu trữ.** ZIP nhúng trong
  PDF đã cung cấp đủ mã/cấu hình. [Benchmark Beer–Rossmann](benchmarks/beer_rossmann/README.md)
  có hai bản thích nghi, baseline, thiết kế 18 điều kiện, metric và bootstrap
  tái tạo từ clone sạch; dữ liệu nguồn ở ngoài Git. Chưa huấn luyện lại toàn bộ.
- **Đợt 4: đã đóng gói và kiểm tra CFO.** [Hướng dẫn CFO](reports/cfo/README.md)
  có mã/cấu hình chỉnh được, bảng tài chính tái tạo, báo cáo phần C và pilot
  mô phỏng 365 kỳ. Mọi số VND là giả định mẫu, không phải chi phí doanh nghiệp.
- **Đợt 5: có [slide v4 và script bản phân phối](presentation/README.md), bản
  [định hướng D](docs/research_direction_d.md) và bảng dẫn nguồn từng slide.**
  Nguyên bản giữ ngoài Git: quyền phân phối ảnh chụp bài báo chưa xác định;
  bản repo thay 22 ảnh nguồn bằng diễn giải tự soạn có dẫn nguồn.

Các thư mục đầu vào riêng và dữ liệu tải ngoài được bỏ qua bởi Git. Không đưa
gói replication chính thức, dữ liệu hoặc tài liệu bên thứ ba lên repo khi chưa
xác định quyền phân phối. Xem từng hướng dẫn để biết phần còn thiếu và cách chạy.
Đã nhận PDF, README, PPTX v4 và DOCX. PDF chứa ZIP mã/dữ liệu/kết quả; bản gốc
được giữ ngoài Git trong `/workspace/inputs/`. [Hướng dẫn đầu vào](docs/input_handoff.md)
ghi lịch sử tiếp nhận và checksum trong tài liệu từng đợt.

## Cài đặt Python

Khuyến nghị Python 3.10 trở lên. Từ thư mục gốc của repo, cài các gói cần thiết:

```powershell
python -m pip install -r lost_sales_lab/requirements.txt
python -m pip install numpy pandas matplotlib scipy ipython ipykernel jupyter
```

Nếu chỉ chạy ứng dụng, lệnh cài thứ hai không cần thiết. Có thể tạo môi trường ảo trước để tách các thư viện khỏi Python của máy.

## Chạy ứng dụng mô phỏng

Từ thư mục gốc repo:

```powershell
python -m streamlit run lost_sales_lab/app.py
```

Mở <http://127.0.0.1:8501>. Để mở một mô hình trong phiên mới, thêm `?model=hql`, `?model=meta` hoặc `?model=fql` vào địa chỉ. README riêng của ứng dụng giải thích luật tồn kho, doanh số bị kiểm duyệt, chi phí và giới hạn phép so sánh.

## Chạy notebook năm thí nghiệm

Từ thư mục gốc repo, mở notebook:

```powershell
jupyter notebook notebooks/gong_simchi_5_experiments.ipynb
```

Chọn **Run All** để chạy từ đầu. Mặc định notebook chạy chế độ `quick` và lưu kết quả vào `results/five_experiments/`. Notebook dùng nhu cầu tổng hợp, không tải dữ liệu ngoài. Máy cần các gói NumPy, pandas, Matplotlib, SciPy và IPython.

## Chạy thí nghiệm alpha

Từ thư mục gốc repo:

```powershell
python experiments/alpha_sensitivity/run_alpha_demo.py
```

Kết quả được ghi vào `results/alpha_sensitivity/`. Lần chạy mặc định dùng 1.000 chu kỳ, 30 seed, năm kịch bản nhu cầu và năm công thức alpha. Script kiểm tra phép tính theo mã HQL trong ứng dụng trước khi chạy lô.

## Chạy kiểm tra gói tái lập chính thức

Tải gói replication từ [trang Supplemental Material của INFORMS](https://pubsonline.informs.org/doi/suppl/10.1287/mnsc.2023.4947) và giải nén. Cần có `final_synthetic.ipynb`, `final_rossman.ipynb`, `rossman.csv` và `readme.pdf`. Repo không chứa bản sao các tệp này.

```powershell
python -m pip install numpy pandas matplotlib
python replication_audit/run_audit.py --package-dir "C:\path\to\extracted\package"
```

Công cụ xác minh SHA-256, chạy notebook trong namespace tách biệt, rồi lưu báo cáo vào `results/replication_audit/audit_results.json`. Xem [hướng dẫn audit](replication_audit/README.md) để hiểu kết quả benchmark và độ nhạy chỉ số episode.

## Đối chiếu tài liệu nghiên cứu

Python 3.10+, chỉ thư viện chuẩn:

```bash
python tools/check_research_brief.py
```

Lệnh kiểm tra bảng audit trong tài liệu định hướng D với snapshot JSON đã lưu,
không chạy lại gói bổ sung hoặc xác minh các định lý. Kiểm tra số liệu biểu đồ
slide bằng `python presentation/check_evidence.py` (cài dependencies trong
`presentation/requirements.txt`).

## Cách đọc kết quả

Notebook đang ở chế độ **quick**. TN1–TN3 dùng một biến thể Meta-HQL thực hành trên lưới hữu hạn; TN4–TN5 dùng quy hoạch động khi biết phân phối nhu cầu. Đây là các nhánh thí nghiệm khác nhau, không phải một lần tái lập đầy đủ các kết quả trong bài báo.

Thí nghiệm alpha dùng HQL rời rạc với lost-sales và episode độc lập. Ngưỡng tin cậy gốc có thể quá rộng để loại ứng viên trong chân trời mô phỏng. Kết quả dùng ngưỡng nhỏ hơn chỉ nhằm minh họa độ nhạy, không có bảo đảm lý thuyết của bài. Kịch bản đổi mức nhu cầu là stress test ngoài giả định phân phối lặp lại.

Ứng dụng là công cụ học tập. So sánh người dùng với thuật toán trên cùng một đường nhu cầu mang tính minh họa; riêng phép so sánh đó không ước lượng regret kỳ vọng và không chứng minh tối ưu.

Website chạy chính các lõi Python qua Pyodide trong trình duyệt. Bản học Mimic dùng FQL ảo J=6, chu kỳ nhu cầu H=3 và lệnh thực có hạn mức; kho thực giữ tồn/nợ/pipeline, chỉ hệ ảo reset. Cách giải nghĩa công thức ghép và hạn mức là điều chỉnh công khai theo nguồn luận án MIT sớm hơn bài báo cuối. Không áp dụng bảo đảm regret cho bản học. [Phạm vi và nguồn](docs/mimic_teaching_scope.md) ghi rõ phần cần tiếp tục đối chiếu.

## Nguồn và phạm vi

Các mã trong repo là cài đặt độc lập phục vụ học và thử nghiệm, lấy cảm hứng từ bài *Bandits atop Reinforcement Learning: Tackling Online Inventory Models with Cyclic Demands* của Gong và Simchi-Levi, đăng trên *Management Science* năm 2024: [DOI 10.1287/mnsc.2023.4947](https://doi.org/10.1287/mnsc.2023.4947). Repo không chứa gói tái lập của tác giả và không tuyên bố tái lập đầy đủ các kết quả đã công bố.

Kết quả đã lưu kèm cấu hình và phiên bản thư viện khi có. Chạy lại trên phiên bản Python hoặc thư viện khác có thể tạo sai khác số nhỏ.

## Giấy phép

Repo chưa chọn giấy phép. Cho đến khi có tệp LICENSE, việc sử dụng lại, phân phối hoặc tạo tác phẩm phái sinh cần sự cho phép của chủ sở hữu bản quyền. Bài báo, dữ liệu và tài liệu của bên thứ ba tuân theo điều khoản riêng.
