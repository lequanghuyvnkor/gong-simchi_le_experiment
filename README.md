# Gong & Simchi-Levi: học thuật toán tồn kho theo nhu cầu chu kỳ

Repo này tập hợp một ứng dụng mô phỏng để học mô hình tồn kho, một notebook năm thí nghiệm và một thí nghiệm độ nhạy về tốc độ học alpha. Tài liệu, giao diện và hướng dẫn hiện viết bằng tiếng Việt.

## Nội dung

- [`lost_sales_lab/`](lost_sales_lab/README.md): ứng dụng Streamlit mô phỏng vận hành tồn kho và giải thích từng bước HQL, Meta-HQL và FQL. Mimic-QL chưa được cài đặt.
- [`notebooks/gong_simchi_5_experiments.ipynb`](notebooks/gong_simchi_5_experiments.ipynb): năm thí nghiệm minh họa cho bài trình bày 45 phút, gồm lợi ích nhu cầu chu kỳ, chuyển giao tồn kho, biến động, rủi ro và chi phí vốn.
- [`experiments/alpha_sensitivity/run_alpha_demo.py`](experiments/alpha_sensitivity/run_alpha_demo.py): so sánh năm công thức alpha trên năm kịch bản nhu cầu.
- [`results/five_experiments/`](results/five_experiments/): cấu hình, bảng CSV và hình của lần chạy notebook chế độ nhanh.
- [`results/alpha_sensitivity/`](results/alpha_sensitivity/): cấu hình, báo cáo, bảng kết quả, hình và dấu vết mô phỏng alpha đã lưu.

## Cài đặt

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

## Cách đọc kết quả

Notebook đang ở chế độ **quick**. TN1–TN3 dùng một biến thể Meta-HQL thực hành trên lưới hữu hạn; TN4–TN5 dùng quy hoạch động khi biết phân phối nhu cầu. Đây là các nhánh thí nghiệm khác nhau, không phải một lần tái lập đầy đủ các kết quả trong bài báo.

Thí nghiệm alpha dùng HQL rời rạc với lost-sales và episode độc lập. Ngưỡng tin cậy gốc có thể quá rộng để loại ứng viên trong chân trời mô phỏng. Kết quả dùng ngưỡng nhỏ hơn chỉ nhằm minh họa độ nhạy, không có bảo đảm lý thuyết của bài. Kịch bản đổi mức nhu cầu là stress test ngoài giả định phân phối lặp lại.

Ứng dụng là công cụ học tập. So sánh người dùng với thuật toán trên cùng một đường nhu cầu mang tính minh họa; riêng phép so sánh đó không ước lượng regret kỳ vọng và không chứng minh tối ưu.

## Nguồn và phạm vi

Các mã trong repo là cài đặt độc lập phục vụ học và thử nghiệm, lấy cảm hứng từ bài *Bandits atop Reinforcement Learning: Tackling Online Inventory Models with Cyclic Demands* của Gong và Simchi-Levi, đăng trên *Manufacturing & Service Operations Management* năm 2024: [DOI 10.1287/mnsc.2023.4947](https://doi.org/10.1287/mnsc.2023.4947). Repo không chứa gói tái lập của tác giả và không tuyên bố tái lập đầy đủ các kết quả đã công bố.

Kết quả đã lưu kèm cấu hình và phiên bản thư viện khi có. Chạy lại trên phiên bản Python hoặc thư viện khác có thể tạo sai khác số nhỏ.

## Giấy phép

Repo chưa chọn giấy phép. Cho đến khi có tệp LICENSE, việc sử dụng lại, phân phối hoặc tạo tác phẩm phái sinh cần sự cho phép của chủ sở hữu bản quyền. Bài báo, dữ liệu và tài liệu của bên thứ ba tuân theo điều khoản riêng.
