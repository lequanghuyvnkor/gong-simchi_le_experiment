# Inventory Research Hub — cổng mô phỏng, stress test và thuyết trình

Site riêng tư: <https://gong-simchi-inventory-lab.snu-chatgpt-5678.chatgpt.site>.
Đây là bản cloud mới từ app trong chat “Hình dung bốn mô hình thuật toán”; chat đó chỉ có app Streamlit cục bộ, chưa có Site được xuất bản. Mã Streamlit cũ vẫn có ba lựa chọn HQL/Meta-HQL/FQL. Website này có thêm **Mimic-QL-inspired teaching adaptation** với giới hạn công khai trong [phạm vi Mimic](../docs/mimic_teaching_scope.md).

## Sử dụng

1. Chọn mô hình, chờ bộ tính toán tải lần đầu, chọn mức hàng hoặc lượng đặt cho A/B.
2. Chạy một ngày hoặc tự chạy; xem luồng hàng, phản hồi, chi phí và số dư. Thuật toán và người dùng cùng nhận một đường nhu cầu; lệnh chốt trước khi nhu cầu được tiết lộ.
3. Mở cấu hình để đổi seed, số chu kỳ và cận minh họa/công thức. Áp dụng sẽ bắt đầu lại riêng mô hình đang chọn.
4. Dùng thanh xem lại, xem một cập nhật Q đã lưu hoặc tải CSV. Chuyển mô hình giữ lượt trong tab; tải lại trang mất phiên.
5. Tab **Sơ đồ chuyển động** có bốn MP4 24 giây, 1280×720, không âm thanh/phụ đề/quay màn hình. Các nhãn và số thuộc trace thật, không phải benchmark. Tab hướng dẫn có báo cáo trình bày và kế hoạch stress test.

HQL/Meta-HQL chỉ học từ doanh số riêng. Chế độ xem nhu cầu thật là góc nhìn người chấm sau ngày, không cấp thêm thông tin cho learner. Nếu tắt, CSV cũng chỉ xuất trường được phép quan sát. Với FQL/Mimic, nhu cầu được quan sát đầy đủ theo mô hình. Không so chi phí giữa bốn mô hình để xếp hạng chung. VND của CFO là giả định mẫu; website hiển thị đơn vị mô hình.

HQL/FQL ở đây là episode độc lập. Meta-HQL giữ kho thực liên tục. Mimic dùng H=3, FQL ảo J=6, hạn mức lệnh 2 mỗi SKU và nhu cầu thuộc 0–2; chỉ hệ ảo reset. Lệnh bù có cap, ghi rõ yêu cầu/lệnh/cờ chạm hạn mức trong CSV. Đây chưa phải replication công bố hoặc xác minh định lý.

## Từ clone sạch

Xem website không cần Python trên máy người xem: Python chạy trong Web Worker qua **Pyodide 0.27.7**, tải từ jsDelivr; NumPy được tải lúc khởi động. Cần Internet và trình duyệt hỗ trợ WebAssembly. Mã Python và dữ liệu mô phỏng nằm trong trình duyệt; Site không có tài khoản dữ liệu hay backend lưu kết quả. Không cần R.

Để kiểm tra/dựng lại trên máy phát triển, cần **Python 3.10+**, Node.js 20+, FFmpeg/ffprobe. Từ gốc repo:

```bash
python --version
python -m venv .venv-inventory
source .venv-inventory/bin/activate
python -m pip install -r inventory_site/requirements.txt
python inventory_site/tools/sync_assets.py
python inventory_site/tools/check_site.py
python -m pytest lost_sales_lab/tests/test_model.py lost_sales_lab/tests/test_hql.py lost_sales_lab/tests/test_meta_hql.py lost_sales_lab/tests/test_fql.py lost_sales_lab/tests/test_mimic_ql.py -q
```

Windows: kích hoạt `.venv-inventory\Scripts\activate`. Lõi authoritative ở `lost_sales_lab/`; `sync_assets.py` chép nguyên byte và ghi `core_manifest.json`. Adapter riêng ở `dist/assets/python/lab_api.py`. Không sửa các bản chép rồi quên đồng bộ lõi.

```bash
# Tạo lại video từ trace, không tải hình hoặc dữ liệu ngoài:
MPLCONFIGDIR=/tmp/gong-mpl python inventory_site/tools/build_diagram_videos.py
python inventory_site/tools/check_site.py
```

Trên Windows, đặt MPLCONFIGDIR đến thư mục ghi được hoặc bỏ biến nếu Matplotlib đã có cache. Video dùng seed 42, 24 ngày, 12 fps; cấu hình, phiên bản, hash mã/MP4/trace ở `dist/media/videos_manifest.json`. Trace đầy đủ đi kèm từng video để kiểm tra số hiển thị. Khác bản FFmpeg/font có thể đổi byte MP4 dù số mô phỏng giữ nguyên.

Để preview ngoài managed cloud, phục vụ tĩnh `inventory_site/dist/` bằng web server tin cậy trên localhost (không mở `file://`, vì Worker cần fetch). Trong managed cloud này dùng `sites-preview start <đường-dẫn-project>` theo Sites runtime. Không cần npm build: `dist/` đã là bản phân phối.

## Kiểm tra và giới hạn

`check_site.py` kiểm tra hash lõi và video, một track video không audio/subtitle, liên kết tĩnh, cú pháp JS, chạy hết bốn lượt qua Python adapter, phép tính Q, tính riêng tư của CSV và chuyển mô hình. Nó không thay thế thao tác UI trong trình duyệt. Xem `validation.json` về kiểm tra thực tế và phần bị giới hạn bởi hạ tầng preview.

Kiểm tra thêm chính distribution WebAssembly dùng trong website, không cần điều khiển trình duyệt:

```bash
npm install --prefix /tmp/gong-pyodide --cache /tmp/gong-npm-cache pyodide@0.27.7 --no-audit --no-fund
node inventory_site/tools/check_pyodide.mjs /tmp/gong-pyodide/node_modules/pyodide/pyodide.mjs
```

Đường dẫn `/tmp` dành cho Linux; trên Windows chọn thư mục tạm tương ứng. Script chạy hết bốn lượt qua Python 3.12.7/NumPy 2.0.2 trong WASM. NumPy wheel được tải từ CDN chính thức và kiểm tra theo lock Pyodide; nếu Node không tải được qua proxy, có thể lưu đúng wheel trong thư mục package sau khi xác minh SHA-256 của `pyodide-lock.json`. Kiểm tra WASM không xác nhận layout, thao tác UI hoặc việc CDN được cho phép trong trình duyệt người dùng.

## Bản cổng tổng hợp

Menu **Tổng quan** nối các phần thành một luồng: hiểu sản phẩm qua video, tự thử mô phỏng, thiết kế kiểm tra rồi trình bày bằng chứng. Trang tổng quan, video và báo cáo không chờ Python khởi động. Chỉ khi mở mô phỏng/stress mới tải bộ tính toán. Trên màn hình hẹp, sơ đồ phòng mô phỏng chuyển thành các khối dọc có nhãn đọc được.

- **Phòng mô phỏng:** giữ bốn lượt độc lập, có video riêng của mô hình đang xem, Q replay và CSV. Lỗi worker giải phóng request đang chờ; khởi động phiên mới xóa trạng thái cũ với thông báo rõ.
- **Thiết kế stress:** nhấp các khối diagram để đổi mô hình, nhu cầu, seed/ngân sách hoặc baseline. Có bảy kịch bản: native, zero, steady, peak, alternating, burst và drift. Ba kịch bản cuối được đánh dấu ngoài giả định lặp H=3. Có thể sửa/nhập/tải JSON cấu hình.
- **Chạy stress:** từng ngày hoặc tự chạy có tạm dừng; tối đa 5 seed × 20 chu kỳ × 3 ngày. Diagram trace nhận số liệu thật; xem lại không học thêm. Kết quả/CSV/JSON ghi cấu hình, Python/NumPy và SHA-256 mã. Chỉnh thiết kế sau khi chạy không ghi đè kết quả cũ cho tới khi bấm Áp dụng hợp lệ.
- **Góc thuyết trình:** outline 60/40 phút, 10 Q&A có nguồn, checklist, báo cáo và kế hoạch đọc trực tiếp bằng HTML. Tải PDF/DOCX, slide v4 bản phân phối và script tiếng Việt. Sản phẩm Streamlit có gói ZIP để chạy cục bộ; giao diện Streamlit vẫn có ba lựa chọn, website có thêm bản học Mimic.
- **Nguồn & phạm vi:** thông điệp dẫn về kết quả trong repo và ba câu hỏi nghiên cứu D. `content/presentation.json` là asset nội dung có tham chiếu nguồn, được kiểm tra khi dựng.

Stress dùng riêng đối tượng Lab, không thay đổi các lượt chơi. Môi trường thay bộ sinh nhu cầu trong phạm vi một bước, chốt quyết định trước khi đưa mẫu cầu vào và luôn khôi phục bộ sinh. Worker tuần tự hóa các RPC. Learner HQL vẫn chỉ nhận doanh số riêng; cột nhu cầu thật dành cho người kiểm tra. FQL/Mimic giữ support hữu hạn; tăng cường độ làm xác suất tiệm tới 1, không cắt ngọn mẫu cầu. Tham số kho/phí/confidence chỉ hiện và có hiệu lực với HQL/Meta-HQL; nhập giá trị khác mặc định cho các trường đó ở FQL/Mimic bị từ chối.

Chi phí trong workspace là **trong lúc học**, không phải policy đóng băng sau học, TCO hoặc VND. CI 95% là Student t trên chênh lệch ghép cặp giữa các seed hoàn tất (n=2–5); ít seed tạo khoảng rộng và chỉ mang tính mô tả. Không gộp với bootstrap của benchmark 18 điều kiện, không xếp hạng chéo các mô hình có vật lý khác nhau. Lõi Mimic tiếp tục là teaching adaptation.

## Kiểm tra cổng và chạy lại một thiết kế

Python 3.10+, Node.js 20+ (môi trường đã kiểm tra: Node 24); các lệnh từ gốc repo:

```bash
python -m pip install -r inventory_site/requirements.txt
python inventory_site/tools/sync_assets.py
python inventory_site/tools/check_site.py
python -m pytest lost_sales_lab/tests/test_model.py lost_sales_lab/tests/test_hql.py lost_sales_lab/tests/test_meta_hql.py lost_sales_lab/tests/test_fql.py lost_sales_lab/tests/test_mimic_ql.py inventory_site/tests/test_stress_api.py -q
npm --prefix inventory_site ci --ignore-scripts
npm --prefix inventory_site test
python inventory_site/tools/run_stress.py --config experiments/stress_tests/interactive_example.json --output-dir local_checks/selected_stress
python inventory_site/tools/run_stress.py --smoke --output-dir local_checks/interactive_stress
```

Nếu Python trong venv có tên/path riêng, đặt biến môi trường `PYTHON` cho lệnh npm test. Test DOM dùng jsdom và một worker bridge đến lõi Python thật; kiểm tra handler, cấu hình, replay, chuyển tab, export và phục hồi lỗi, **không** thay thế nghiệm thu layout trong trình duyệt. Không cài trình duyệt thay thế cho managed preview.

[Kết quả smoke](../results/interactive_stress/README.md) có 28 cấu hình / 504 bước. Đây là kiểm tra phần mềm đã chạy; [kế hoạch nghiên cứu 32 test](../experiments/stress_tests/plan.json) vẫn là thiết kế, chưa có runner đầy đủ hoặc kết quả toàn ma trận. Hướng dẫn tải và kiểm tra dữ liệu của benchmark/CFO giữ nguyên ở các thư mục tương ứng.

Site source có `.openai/hosting.json`; giữ nguyên project ID khi cập nhật. Chỉ đẩy mã/asset tự soạn, không đẩy token, dữ liệu thô hoặc tài liệu gốc bên thứ ba. Gói tĩnh để xuất bản chứa manifest và `dist/`, từ đúng commit đã push lên source repository của Site. Giữ audience riêng tư hiện tại.
