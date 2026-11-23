# Kiểm tra phần mềm của stress workspace

`smoke_results.json` ghi một lượt kiểm tra **28 cấu hình / 504 ngày mô phỏng** trên bốn lõi teaching và bảy kịch bản. Mỗi cấu hình dùng hai seed, ba chu kỳ/seed. Các kiểm tra gồm cân bằng hàng, mất bán/nợ/pipeline, chi phí hữu hạn, nhu cầu ghép cặp và đồng hồ thực/ảo của bản học Mimic.

Đây là smoke phần mềm, không phải 32 test nghiên cứu trong `experiments/stress_tests/plan.json`, không phải benchmark chính 18 điều kiện, kiểm tra định lý, policy sau học hoặc chứng minh thứ hạng thuật toán. Các tổng chi phí đi kèm chỉ để tái tạo/kiểm tra lượt chạy. Bản nghiên cứu và bản teaching có phạm vi khác nhau.

Python 3.10+ và NumPy, chạy từ repo:

```bash
python -m pip install -r inventory_site/requirements.txt
python inventory_site/tools/run_stress.py --smoke --output-dir local_checks/interactive_stress
```

Môi trường và SHA-256 mã Python được ghi trong JSON. Các seed 9000–9001 thuộc nhóm hiệu chuẩn đề xuất, không sử dụng locked test. Kịch bản ngoài giả định được giữ riêng và không dùng để kết luận về định lý.

`budget_bounds.json` ghi thêm bốn kiểm tra ở ngân sách UI tối đa (5 seed × 20 chu kỳ × 3 ngày/mô hình), tổng 1.200 bước. HQL/Meta dùng sức chứa 40, phí/cận ở biên giao diện; FQL/Mimic giữ spec hữu hạn riêng. Đây cũng là kiểm tra phần mềm, không phải kiểm định hiệu quả hay ma trận nghiên cứu.
