# Đưa đầu vào từ Windows sang cloud

Ngày 2026-11-23, chủ dự án xác nhận các đường dẫn `inputs/` là **đích đề xuất**,
chưa được tạo hoặc tải lên cloud. Nguồn hiện nằm trên máy Windows, dưới:

```text
C:\Users\PC\Desktop\SNU\SCAIM\Gong&Simchi Experiment\
```

| Đầu vào | Đường dẫn tương đối so với thư mục Windows trên | Đích cloud đề xuất |
| --- | --- | --- |
| Archive Beer–Rossmann và CFO | `luu_tru/bao_cao_beer_rossmann_srdqn_meta_hql_2026-11-16/ma_du_lieu_ket_qua_va_phan_tich_cfo.zip` | `/workspace/inputs/beer_rossmann_archive/` sau khi giải nén |
| README nguồn | `luu_tru/bao_cao_beer_rossmann_srdqn_meta_hql_2026-11-16/README.md` | `/workspace/inputs/beer_rossmann_archive/README.md` |
| Slide v4 | `outputs/academic_presentation_2026-12-04/Gong_Simchi_2024_Blue_Yonder_Academic_60min_v4.pptx` | `/workspace/inputs/presentation/Gong_Simchi_2024_Blue_Yonder_Academic_60min_v4.pptx` |
| Script tiếng Việt | `outputs/academic_presentation_2026-12-04/Gong_Simchi_2024_Script_Tieng_Viet_60_phut.docx` | `/workspace/inputs/presentation/Gong_Simchi_2024_Script_Tieng_Viet_60_phut.docx` |

Các tên/đường dẫn nguồn do chủ dự án cung cấp; chưa kiểm tra được nội dung hay
checksum của các tệp trên máy Windows. Tên thư mục có ngày là tên gốc, không
phải bằng chứng rằng slide hay báo cáo đã được kiểm tra ở ngày đó.

## Bước tiếp theo

Đính kèm bốn tệp ZIP, README, PPTX, DOCX vào chat này hoặc đưa bản sao vào
workspace cloud. Giữ nguyên các bản nguồn trên Windows. Trước khi tải lên,
có thể tính SHA-256 bằng PowerShell `Get-FileHash -Algorithm SHA256 -LiteralPath
'đường dẫn tệp'` và gửi kèm để so với bản nhận được; phiên này chưa chạy lệnh
PowerShell đó trên máy Windows.

Khi nhận ZIP, kiểm kê và đọc cấu trúc trước khi giải nén thành bản làm việc.
Không ghi đè README bên trong ZIP nếu khác README rời; giữ cả hai và ghi rõ
xuất xứ. Giữ ZIP tải lên và checksum ngoài Git. Cấu trúc đích kỳ vọng sau khi
kiểm tra là `beer_rossmann_archive/work/`, `beer_rossmann_archive/outputs/`
cùng README/checksum; nếu ZIP có thư mục bao ngoài, ghi lại ánh xạ thay vì
đoán trước cấu trúc. Từ đó chỉ đọc bản gốc trong `inputs/`; mọi sửa đổi hoặc
kết quả kiểm tra mới viết sang thư mục làm việc khác.

Python 3.10+, thư viện chuẩn, từ gốc repo sau khi có các tệp:

```bash
python tools/inspect_inputs.py --inputs-dir /workspace/inputs --require benchmark --require presentation
```

Mã thoát 0 chỉ xác nhận kiểm kê thành công. Quyền phân phối, checksum so với
nguồn Windows, mã/kết quả benchmark, CFO và nội dung trình bày vẫn cần được
kiểm tra theo hướng dẫn [đợt 3](../benchmarks/beer_rossmann/README.md),
[đợt 4](../reports/cfo/README.md) và [đợt 5](../presentation/README.md).
Không tự tải lại dữ liệu bên thứ ba để thay archive mà chưa xác định phiên bản.

Gói bổ sung chính thức là tùy chọn riêng ở `/workspace/inputs/original_supplement/`;
cách lấy và SHA-256 kỳ vọng đã có trong [hướng dẫn audit](../replication_audit/README.md)
và [mã audit](../replication_audit/run_audit.py). Không cần công bố gói đó lên Git.
