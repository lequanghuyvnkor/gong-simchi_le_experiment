# Gong & Simchi-Levi: học thuật toán tồn kho theo nhu cầu chu kỳ

Repo này tập hợp một ứng dụng mô phỏng để học mô hình tồn kho, một notebook năm thí nghiệm và một thí nghiệm độ nhạy về tốc độ học alpha. Tài liệu, giao diện và hướng dẫn hiện viết bằng tiếng Việt.

## Nội dung

- [`lost_sales_lab/`](lost_sales_lab/README.md): ứng dụng Streamlit mô phỏng vận hành tồn kho và giải thích từng bước HQL, Meta-HQL và FQL. Mimic-QL chưa được cài đặt.
- [`notebooks/gong_simchi_5_experiments.ipynb`](notebooks/gong_simchi_5_experiments.ipynb): năm thí nghiệm minh họa cho bài trình bày 45 phút, gồm lợi ích nhu cầu chu kỳ, chuyển giao tồn kho, biến động, rủi ro và chi phí vốn.
- [`experiments/alpha_sensitivity/run_alpha_demo.py`](experiments/alpha_sensitivity/run_alpha_demo.py): so sánh năm công thức alpha trên năm kịch bản nhu cầu.
- [`replication_audit/`](replication_audit/README.md): công cụ chạy kiểm tra chỉ đọc trên gói bổ sung chính thức, kèm checksum và kết quả kiểm tra đã lưu.
- [`results/five_experiments/`](results/five_experiments/): cấu hình, bảng CSV và hình của lần chạy notebook chế độ nhanh.
- [`results/alpha_sensitivity/`](results/alpha_sensitivity/): cấu hình, báo cáo, bảng kết quả, hình và dấu vết mô phỏng alpha đã lưu.

## Tiến độ đợt 3–5 trong cloud

- **Đợt 3: chuẩn bị một phần, chưa hoàn tất.** Có công cụ kiểm kê SHA-256 chỉ đọc
  và [hướng dẫn tiếp nhận benchmark](benchmarks/beer_rossmann/README.md).
  Chưa thấy `inputs/beer_rossmann_archive/` trong cloud ngày 2026-11-23; chưa có
  mã/kết quả benchmark chính 18 điều kiện được nhập hoặc chạy lại.
- **Đợt 4: chuẩn bị tài liệu, chưa hoàn tất.** [Hướng dẫn CFO](reports/cfo/README.md)
  nêu phạm vi giả định VND, cách tách học/sau học, TCO và hòa vốn. Chưa có
  mã, cấu hình, bảng hay báo cáo CFO từ archive để chạy và đối chiếu.
- **Đợt 5: có [tổng hợp định hướng D](docs/research_direction_d.md), chưa hoàn tất.**
  Có bảng audit dẫn tới JSON và công cụ đối chiếu số liệu; chưa có slide v4 và
  script ở `inputs/presentation/`. Xem [hướng dẫn trình bày](presentation/README.md).

Các thư mục đầu vào riêng và dữ liệu tải ngoài được bỏ qua bởi Git. Không đưa
gói replication chính thức, dữ liệu hoặc tài liệu bên thứ ba lên repo khi chưa
xác định quyền phân phối. Xem từng hướng dẫn để biết phần còn thiếu và cách chạy.
Chủ dự án xác nhận các đầu vào còn trên Windows; [hướng dẫn chuyển đầu vào](docs/input_handoff.md)
ghi tên ZIP, README, PPTX v4 và DOCX cần đưa vào cloud.

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

Lệnh kiểm tra bảng trong tài liệu định hướng D với snapshot JSON đã lưu, không
chạy lại gói bổ sung hoặc xác minh các định lý. Đợt 3–5 vẫn chờ đầu vào riêng.

## Cách đọc kết quả

Notebook đang ở chế độ **quick**. TN1–TN3 dùng một biến thể Meta-HQL thực hành trên lưới hữu hạn; TN4–TN5 dùng quy hoạch động khi biết phân phối nhu cầu. Đây là các nhánh thí nghiệm khác nhau, không phải một lần tái lập đầy đủ các kết quả trong bài báo.

Thí nghiệm alpha dùng HQL rời rạc với lost-sales và episode độc lập. Ngưỡng tin cậy gốc có thể quá rộng để loại ứng viên trong chân trời mô phỏng. Kết quả dùng ngưỡng nhỏ hơn chỉ nhằm minh họa độ nhạy, không có bảo đảm lý thuyết của bài. Kịch bản đổi mức nhu cầu là stress test ngoài giả định phân phối lặp lại.

Ứng dụng là công cụ học tập. So sánh người dùng với thuật toán trên cùng một đường nhu cầu mang tính minh họa; riêng phép so sánh đó không ước lượng regret kỳ vọng và không chứng minh tối ưu.

## Nguồn và phạm vi

Các mã trong repo là cài đặt độc lập phục vụ học và thử nghiệm, lấy cảm hứng từ bài *Bandits atop Reinforcement Learning: Tackling Online Inventory Models with Cyclic Demands* của Gong và Simchi-Levi, đăng trên *Management Science* năm 2024: [DOI 10.1287/mnsc.2023.4947](https://doi.org/10.1287/mnsc.2023.4947). Repo không chứa gói tái lập của tác giả và không tuyên bố tái lập đầy đủ các kết quả đã công bố.

Kết quả đã lưu kèm cấu hình và phiên bản thư viện khi có. Chạy lại trên phiên bản Python hoặc thư viện khác có thể tạo sai khác số nhỏ.

## Giấy phép

Repo chưa chọn giấy phép. Cho đến khi có tệp LICENSE, việc sử dụng lại, phân phối hoặc tạo tác phẩm phái sinh cần sự cho phép của chủ sở hữu bản quyền. Bài báo, dữ liệu và tài liệu của bên thứ ba tuân theo điều khoản riêng.
