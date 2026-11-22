# Kế hoạch stress test cho bốn nhánh mô hình tồn kho

**Trạng thái: thiết kế đề xuất, chưa thực thi toàn bộ ma trận.** Ngày lập: 23/11/2026. Cấu hình máy đọc được nằm tại [experiments/stress_tests/plan.json](../experiments/stress_tests/plan.json). Tệp JSON là đặc tả công việc cho runner tương lai, không phải một lệnh đã chạy hoặc một bộ kết quả.

Mục tiêu là tìm lỗi vật lý, rò rỉ thông tin, sai cập nhật và các vùng hiệu quả kém; sau đó mới đo tính ổn định của kết luận. Kế hoạch tách kiểm tra phần mềm, thí nghiệm trong giả định và stress ngoài giả định. Không dùng một stress ngoài phạm vi lý thuyết để tuyên bố bác bỏ định lý.

## 1. Phạm vi và điều kiện vào

Các nguồn cần đọc trước khi tạo runner là [README mô phỏng](../lost_sales_lab/README.md), [model.py](../lost_sales_lab/model.py), [HQL](../lost_sales_lab/hql.py), [Meta-HQL](../lost_sales_lab/meta_hql.py), [FQL model](../lost_sales_lab/fql_model.py), [FQL](../lost_sales_lab/fql.py) và [giao thức benchmark](../benchmarks/beer_rossmann/README.md). Mọi thay đổi của bản website mới phải có bảng ánh xạ về các lõi Python này.

[Mimic teaching core](../lost_sales_lab/mimic_ql.py) dùng order cap (2,2), initial stock (0,0), demand support 0..2 và L=1. Support 0..4 của FQL mặc định không tự áp dụng cho biến thể Mimic này; fixture phải đọc đúng spec từng model.

| Nhánh | Động lực và thông tin | Oracle/baseline được phép so |
| --- | --- | --- |
| HQL | Episodic lost-sales; hàng đến ngay; chỉ thấy doanh số bị kiểm duyệt | Policy cố định/theo pha trong cùng episode; DP biết phân phối với cùng reset và terminal rule |
| Meta-HQL | Lost-sales giữ tồn; điều phối bản sao dịch pha; giữ kho vật lý cả ngày chờ | Baseline giữ tồn cùng chuỗi; DP hoặc policy reference phù hợp nondiscarding và cùng chân trời |
| FQL | Backlogging hai sản phẩm; lead time một ngày; full demand feedback; episode độc lập | Baseline có cùng pipeline/nợ/terminal rule; DP hữu hạn nhỏ cùng trạng thái–hành động |
| Mimic teaching adaptation | Nondiscarding backlogging hữu hạn; FQL ảo có J=6, true H=3; lệnh ghép theo IP rồi actuator cap | Baseline cùng vật lý và cap; tách khỏi replication nguyên gốc và khỏi policy FQL reset |

**Hai trạng thái Mimic phải tách riêng.** Bản website mới triển khai **Mimic-QL-inspired teaching adaptation**, theo ý tưởng inventory-position trong [luận án MIT của Gong (2023)](https://hdl.handle.net/1721.1/151589), trang 62–65 và 170–171. Bản dạy dùng true H=3 và cycle ảo J=6; cả đồng hồ thực/ảo cùng tiến với mỗi nhu cầu. Yêu cầu q=max(IP_ảo+q_ảo−IP_thực,0), lệnh thực=min(cap,yêu cầu); phải ghi cap-binding và gap. IP là tồn ròng cộng pipeline, không chỉ on-hand. Đây là lựa chọn hữu hạn minh bạch, không phải một replication nguyên gốc có theorem guarantee. Full text cuối cùng và chi tiết feasibility/reset của thuật toán công bố vẫn là source gate cho nhánh **published replication**. Các test teaching có thể chạy theo contract đã công bố; chúng không đóng source gate của nhánh published, và kết quả cũ không tự trở thành kết quả Mimic. Không suy rằng bỏ reset của FQL là đủ. Không diễn giải khác biệt ký hiệu/feasibility trong nguồn sớm như kết luận định lý sai.

## 2. Các mức kiểm tra và thứ tự làm

| Mức | Mục đích | Điều kiện chuyển mức | Ngân sách đề xuất |
| --- | --- | --- | --- |
| P0 — Bất biến và hợp đồng | Tính đúng vật lý/thông tin/cập nhật | Không còn lỗi accounting, action feasibility, future leakage, replay hoặc NaN | Một lượt hiệu chuẩn trên miền nhỏ; mục tiêu trong khoảng 10 phút, chưa đo |
| P1 — Smoke và tính xác định | Chạy qua reset/chuyển nhánh/hàng về trên nhiều seed | Chạy lại cùng cấu hình cho cùng trace; đổi chính sách không đổi đường cầu chung | 5 seed hiệu chuẩn; mục tiêu dưới 30 phút sau khi có runner, chưa đo |
| P2 — Trong giả định | Đo chi phí học, policy sau học và độ ổn định | Validation kết thúc, cấu hình và tiêu chí khóa trước test | 30 seed test mỗi ô; bắt đầu bằng ma trận lõi nhỏ |
| P3 — Ngoài giả định | Tìm vùng suy giảm/đổ vỡ khi drift, sai chu kỳ, tương quan | Mỗi vi phạm giả định được gắn nhãn; không gộp với bảng primary | Mở từng nhóm sau P2, dừng theo ngân sách nguồn lực |
| P4 — Website và video | Trải nghiệm, phản hồi, replay/export và tính trung thực diagram | Luồng chính, bàn phím/mobile, trạng thái độc lập và video khớp mô hình | Chạy kiểm tra hồi quy khi UI/core hoặc artifact đổi |

Các con số ngân sách là **mục tiêu lập kế hoạch**, chưa phải benchmark tốc độ. Trước P2, đo một ô đại diện, ghi wall time/peak memory và ngoại suy khoảng thời gian theo số model, không cam kết “chạy qua đêm” chỉ bằng số seed. Không khởi chạy toàn bộ ma trận dài khi chưa có kiểm soát dừng.

Để phát hành công cụ học, chạy P0 → P1 → P4 trước; P4 được chạy lại khi giao diện hoặc core đổi. P2 → P3 là tuyến nghiên cứu tiếp theo, không phải điều kiện phải hoàn thành cả ma trận dài mới kiểm tra được nút bấm/video.

## 3. P0: hợp đồng vật lý, thông tin và cập nhật

| ID | Nhánh | Trường hợp cần tạo | Điều kiện đạt |
| --- | --- | --- | --- |
| PHY-LS-01 | HQL/Meta | D=0, D<y, D=y, D>y; tồn đầu bằng/trên mục tiêu đề xuất | q≥0; y=max(x,B); s=min(y,D); I=y−s; lost=D−s; không tạo hoặc làm mất hàng ngoài quy ước terminal |
| PHY-LS-02 | HQL/Meta | Tồn 0/M, đặt 0, bán hết 0 hàng | 0≤x≤y≤M; equality vẫn là quan sát bị kiểm duyệt; không chia cho 0 |
| COST-LS-01 | HQL/Meta | Nhiều h/p dương; mọi mức lưới nhỏ | C−pseudo=pD; chênh lệch hai policy trên cùng D nhất quán; pseudo âm không bị gọi là lợi nhuận |
| INFO-LS-01 | HQL/Meta | Hai nhu cầu thật khác nhau nhưng cho cùng chuỗi sales quan sát ở policy đang xét | Trạng thái learner và cập nhật giống nhau; không nhận D thật, lost cost, seed phân phối hoặc quyết định của người chơi |
| INFO-ALL-01 | Tất cả | Sửa nhu cầu tương lai sau thời điểm t; giữ lịch sử hiện tại | Quyết định tới t không thay đổi; mỗi ngày chỉ sinh một nhu cầu chung sau khi hai quyết định được chốt |
| END-HQL-01 | HQL | Ngày cuối episode còn hàng | Tính chi phí ngày cuối trước reset; tồn sau reset bằng 0; chỉ cập nhật một lần |
| UPD-HQL-01 | HQL | Ví dụ tính tay có stopping time trễ và không trễ | Reward sum/continuation/Q theo đúng thứ tự; tập dùng để xác định stopping time không bị sửa sớm; Q ngày sau theo quy ước mã đã công bố |
| META-01 | Meta | Vào bản sao khác pha, tồn cao; điều kiện cùng đúng hoặc cùng sai | Kho vật lý giữ nguyên, không đặt khi chờ; chi phí ngày chờ được tính; không học từ ngày chờ |
| META-02 | Meta | Khối hoàn tất/còn dở, loại nhánh, chặn tập rỗng | Đếm episode nội bộ đúng; không tính episode dở thành hoàn tất; lịch khối và xử lý bảo vệ được ghi; không âm thầm khởi tạo lại kho |
| PHY-BK-01 | FQL/Mimic | Có nợ cũ và hàng đang về; nhu cầu mới cùng ngày | Hàng đến trả nợ cũ trước, sau đó phục vụ cầu mới; net_next=net+arrival−D; pipeline_next=order với L=1 |
| COST-BK-01 | FQL/Mimic | Chỉ đặt A, chỉ B, cả hai, không đặt | Phí joint order tính đúng một lần nếu có đơn dương; mua/giữ/nợ được tách, cộng đủ; không giữ tồn dương và nợ dương đồng thời cho cùng SKU |
| END-FQL-01 | FQL | Ngày cuối còn tồn/nợ/pipeline và có đơn mới | Ghi đầy đủ số dư, chi phí và quy ước V_terminal; episode mới độc lập đúng cấu hình; không diễn giải reset thành miễn phí xóa nợ của vận hành thật |
| UPD-FQL-01 | FQL | Miền trạng thái nhỏ liệt kê hết; mẫu D hợp lệ | So toàn bộ Q với Bellman scalar độc lập; cập nhật mọi ô cần thiết bằng full feedback; dùng đúng Q ngày sau vừa cập nhật |
| MIMIC-01 | Mimic teaching | Bắt đầu/end cycle ảo; hệ thực đang dư hàng hoặc nợ | Cả hai đồng hồ cùng tiến với cùng D; chỉ reset hệ ảo; không xóa kho/nợ/pipeline thật để ép khớp |
| MIMIC-02 | Mimic teaching | IP thực âm tại boundary; yêu cầu ghép vượt order cap | Lệnh thực khả thi; lưu cả requested/executed, cap-binding và gap; cap-binding được công bố là diagnostic của bản dạy, không bị che hoặc tự gán synchronized |
| MIMIC-03 | Mimic teaching | IP khớp nhưng pipeline chưa khớp; chi phí thực vượt bound episode ảo | Phân biệt IP/full-state match; đo thời gian ghép thực tế, không hứa luôn ≤L; không clip chi phí/nợ thực để giữ normalization của hệ ảo |
| NUM-01 | Tất cả | Phí rất nhỏ/lớn nhưng hữu hạn, bounds đầu episode, tie Q | Không NaN/Inf trong trường cần hữu hạn; bound vô hạn đầu episode có nhãn/serialization rõ; tie-break ổn định |
| REPLAY-01 | Tất cả | Tua đi/lùi, đổi tab, mở giải thích, xem Q/video | Hash trạng thái learner, số ngày, RNG và chi phí không thay đổi do thao tác chỉ đọc |

Phân biệt kiểm tra invalid input với stress hợp lệ. Trong bản FQL hiện tại, D có support công bố 0..4; D>4 phải bị từ chối hoặc đi qua một biến thể có support/cận chi phí được xây lại, không được cắt ngọn rồi gọi là cùng thí nghiệm. Ở lost-sales, D có thể vượt cap tồn; việc thiếu hàng lúc đó là hành vi hợp lệ, không phải lý do clip D.

## 4. Ma trận P1: các quỹ đạo tối thiểu

Mỗi trường hợp dưới đây dùng một đường cầu được lưu, chạy lại cùng seed và chạy với quyết định người chơi khác để kiểm tra policy independence của bộ sinh. Các đường giả định là fixture, không phải dữ liệu doanh nghiệp.

| ID | Lost-sales | Backlogging | Mục tiêu |
| --- | --- | --- | --- |
| PATH-00 | Cầu luôn 0 | Cả hai SKU luôn 0 | Tồn dư, không có doanh số, phí đặt/mua không được biến mất |
| PATH-01 | Cầu nhỏ đều | Cầu từng SKU nhỏ trong support | Quá trình học ổn định và xử lý tie |
| PATH-02 | Cầu bằng lượng hàng ở ranh giới | Cầu vừa hết lượng có thể giao | Censoring equality; backlog và tồn cùng SKU không đồng thời dương |
| PATH-03 | Cầu vượt cap nhiều ngày | Cầu tối đa support nhiều ngày | Thiếu hàng hoặc nợ kéo dài, không mất số dư |
| PATH-04 | Pha thấp–cao–thấp | A cao khi B thấp rồi đổi vai | Căn pha, hàng đang về và trạng thái joint order |
| PATH-05 | Burst rồi khoảng cầu 0 | Burst tạo nợ rồi hàng đến | Tồn/nợ/pipeline và chi phí tích lũy |
| PATH-06 | Trùng thời điểm đổi bản sao | Ranh giới cycle ảo/episode và hàng đến | Không lệch một ngày, không cập nhật hai lần |

Khởi tạo ở các góc miền đã hỗ trợ, gồm tồn đầu 0 và tồn đầu cap cho lost-sales; FQL dùng các cấu hình hợp lệ trong FQLSpec. Không đưa một trạng thái ngoài reachable grid vào learner rồi giải thích exception như hiệu quả kinh tế kém; đó là kiểm tra hợp đồng hoặc yêu cầu mở rộng miền.

## 5. P2: ma trận trong giả định và sensitivity có kiểm soát

### 5.1 Panel nhu cầu hợp lệ

Lost-sales giữ nhu cầu độc lập theo ngày và phân phối lặp đúng H. Bắt đầu từ các profile mean của bản học: đều, thấp–cao–thấp và cao–thấp–cao, kèm cầu 0 hợp lệ khi mục đích là accounting. Khi muốn thay CV độc lập với mean, dùng một bộ sinh integer đã đặc tả và kiểm tra moment/support, không gọi thay mean Poisson là “chỉ thay độ biến động”.

FQL giữ hai sản phẩm, L=1 và demand support đã công bố. Dùng mean theo pha 0, mức giữa và cap, cùng profile đảo pha giữa A/B. Thí nghiệm phụ thuộc chéo SKU hoặc tương quan theo thời gian phải được gắn nhãn riêng nếu làm khác giả định nguồn; không tự gộp vào panel primary.

Không so chi phí HQL reset với Meta giữ tồn như hai policy cạnh tranh trên cùng một mô hình. Tương tự, không xếp FQL và Mimic chỉ bằng cùng seed khi terminal rule/chu kỳ nhân tạo khác nhau. Tạo baseline tương ứng cho từng mô hình, rồi mới so sensitivity bên trong mỗi mô hình.

Oracle nhỏ phải được đối chiếu bằng Bellman scalar/liệt kê độc lập trước khi chấm learner. Ghi oracle biết phân phối hay biết tương lai; phương án hindsight chỉ là reference riêng. Chi phí chênh trên một đường cầu so với reference không tự là regret kỳ vọng trong định lý. Khi chưa có oracle được xác minh cho nondiscarding/backlogging, báo cáo cost difference với baseline khả thi, không đổi nhãn thành “optimality gap”.

### 5.2 Các yếu tố quét

| Yếu tố | Mức đề xuất | Quy tắc khóa |
| --- | --- | --- |
| Confidence action HQL/Meta | Multiplier quanh công thức đã định nghĩa: 0.25, 0.5, 1, 2, 4 | Một hệ số là baseline 1 theo cùng công thức/thang reward; không đồng nhất số tuyệt đối với action_scale của benchmark khác |
| Confidence bandit Meta | 0.5, 1, 2 | Giữ action bound cố định khi đo hiệu ứng chính, rồi mới chạy tương tác có giới hạn |
| Alpha | Công thức chuẩn và các lịch đối chiếu đã đặc tả | Tách tác động alpha khỏi cận; không đổi đồng thời mà gán nguyên nhân cho một biến |
| Cap/lưới lost-sales | Miền nhỏ để có oracle; thêm cap 5/10/20 theo đơn vị bản học | Khi thay grid, ghi A, độ phân giải và chuẩn hóa reward; đảm bảo cùng feasible actions cho đối thủ |
| Chân trời học | Các bội của H tăng dần, ví dụ 30/100/500 episode cho nghiên cứu mới | Các mốc này là thiết kế đề xuất; không tự đồng nhất với main benchmark 21000 kỳ |
| Chi phí giữ/thiếu hoặc giữ/nợ | Tỷ số 1/5/10 cho panel lõi; mức khác ở phần phụ | Giữ đơn vị nhất quán; nếu thay cost bound hay mục tiêu, cập nhật nhãn phiên bản |
| FQL độ lớn miền | Order cap 1/2/3, demand cap trong support 1..4 | Kiểm tra grid đóng và cost bound lại; ước lượng RAM trước khi cấp phát bảng Q |
| Mimic cycle nhân tạo | J=6 của bản dạy; J=9 chỉ nếu triển khai/nguồn lực cho phép | True H=3 và J khác nhau; tổng quát hóa grid, alpha và reward bound cùng nhau; các J nhỏ này không phải cách chọn asymptotic theo T của định lý |
| Khởi tạo | Tồn thấp/cao; nợ/pipeline nếu model contract cho phép | Baseline và learner bắt đầu từ cùng điều kiện vật lý được công bố |

Không chạy tích Descartes của mọi hàng ngay từ đầu. Chọn một panel lõi nhỏ để đo từng hiệu ứng, sau đó một số ô tương tác đã nêu lý do. Mọi cấu hình bổ sung sau khi nhìn test phải được gắn nhãn exploratory và dùng một tập test mới nếu muốn xác nhận.

### 5.3 Chỉ tiêu phải lưu

- Chi phí thật trong học, chi phí policy đóng băng sau học, decomposition giữ/thiếu/mua/joint fee/nợ theo đúng model.
- Fill rate theo lượng, tồn bình quân, backlog bình quân/tối đa, ngày có nợ, hàng đang về, tần suất đặt; định nghĩa fill rate khi demand tổng bằng 0 phải rõ (NA hoặc quy ước đã công bố), không âm thầm chia 0.
- Running-set size, loại nhầm hành động tối ưu trên bài toán nhỏ biết oracle, arm còn lại, số ngày chờ theo nguyên nhân, số episode hoàn tất/còn dở, số lần bảo vệ tập rỗng.
- Với Mimic teaching: IP gap, full-state gap, thời gian ghép, requested/executed order, cap-binding, vi phạm khả thi của lệnh thực và chi phí thực/ảo riêng. Cap-binding đã công bố là diagnostic; lệnh thực vượt cap mới là invariant failure. Với delta=IP_thực−IP_ảo≥0, kiểm tra công thức delta_next=max(delta−q_ảo,0) trong contract L=1; nhánh delta<0 phải giữ gap/cap-binding thay vì cam kết ghép ngay.
- Wall time, CPU time nếu đo được, peak memory, số entry Q/trace, thời gian render phản hồi, kích thước CSV/JSON/video và phiên bản phần mềm.

“Frozen policy” cần một contract riêng: khóa Q, tập ứng viên, tham số chuẩn hóa và quy tắc chọn/điều phối trước test; cấm cập nhật bằng test. Nếu lấy argmax-Q khác với policy đang chạy max(Running Set), ghi đúng biến thể deployment. Không tự dùng tên policy sau học cho một thuật toán vẫn đang loại ứng viên hoặc học trên test.

## 6. Thiết kế ngẫu nhiên và suy luận

### Seed và split mới đề xuất

- Hiệu chuẩn nguồn lực: seed 9000–9004.
- Validation/chọn cấu hình mới: seed 10000–10009.
- Test đã khóa: seed 20000–20029.
- Tập xác nhận mở rộng dự phòng: seed 30000–30099, chưa dùng để điều chỉnh thiết kế.

Đây là các dải seed **mới được đề xuất**, không phải các seed đã chạy trong benchmark cũ. Runner phải có namespace experiment/condition/split để tránh vô tình chia sẻ cùng stream giữa các mục đích. Trong một phép so sánh ghép cặp, các policy dùng cùng đường cầu; RNG của learner nếu có được tách khỏi RNG nhu cầu. Lưu hash đường cầu hoặc đặc tả sinh lại, không nhất thiết công bố dữ liệu bên thứ ba.

Đơn vị lặp chính cho synthetic là đường chạy theo seed độc lập. Nếu profile là panel cố định, lấy trung bình trên profile trong mỗi seed hoặc mô hình hóa block đúng như thiết kế; không tăng n bằng số ngày. Với nhiều store/SKU thực nghiệm, xác định cluster và phụ thuộc chéo trước khi bootstrap; không dùng bootstrap i.i.d. từng hàng doanh số.

Chọn một outcome primary và một family các phép so sánh trước test. Đề xuất báo cáo paired absolute mean difference cùng CI 95%; nếu giữ quy tắc relative effect/±5% của benchmark cũ, áp dụng đúng định nghĩa, multiplicity và thang chi phí, nêu đây là tiêu chí nghiên cứu cụ thể. Khi cả hai cost mean bằng 0 hoặc mẫu số gần 0, relative effect không ổn định/không xác định: báo cáo absolute difference, không gán 0% để tuyên bố tương đương.

Khóa chiều hiệu ứng là cost(learner)−cost(baseline), nên số âm thuận lợi cho learner; bảng dùng quy ước khác phải ghi ngay cạnh cột. CI mô tả ngẫu nhiên theo thiết kế đã chọn, không tự bao gồm sai mô hình hoặc bất định đơn giá kinh doanh.

Khóa quy tắc Holm hoặc Bonferroni cho family primary; ghi phương pháp đã chọn trong config, không chọn lại vì phương pháp cho nhiều “win” hơn. Các bảng secondary/exploratory phải có nhãn. Với tail risk/CVaR, cần đủ mẫu đuôi và phương pháp CI phù hợp; số mẫu lớn trong mỗi policy không thay thế được các lần học độc lập nếu câu hỏi nói về learner.

## 7. P3: stress ngoài giả định

| ID | Vi phạm được tạo có chủ đích | Cách đọc kết quả |
| --- | --- | --- |
| OOD-DRIFT | Đổi mức hoặc profile cầu tại điểm thời gian đã khóa | Đo chi phí chuyển tiếp và hồi phục; không áp bảo đảm fixed cyclic distribution |
| OOD-H | Cấu hình learner biết sai chu kỳ, thay đổi pha hoặc chu kỳ thật | Đánh giá sai mô hình; không gọi là cùng thiết lập H biết trước |
| OOD-CORR | Tự tương quan theo thời gian hoặc đồng biến giữa SKU | Kiểm tra độ nhạy với phụ thuộc; giữ moment và công bố cách sinh để tách nguyên nhân |
| OOD-BURST | Rare burst/heavy tail trong một model hỗ trợ; kiểm tra bound hợp lệ | Lost-sales có thể nhận D>cap; FQL cần support/cost bound mới hoặc phải từ chối, không clip |
| OOD-OPS | Ngày đóng cửa, gián đoạn giao hàng, đổi lead time, MOQ/cap chung | Đây là biến thể model; chưa được chấm như triển khai nguyên gốc nếu thiếu action/state/oracle phù hợp |
| OOD-COST | Đổi tỷ số chi phí ngoài panel hoặc giá vốn/phí cố định đáng kể | Policy cần học/đánh giá lại; không chỉ đổi tiền trên policy cũ rồi gọi là tối ưu mới |

Mỗi nhóm có một baseline cố định và một điều kiện đối chứng không vi phạm, cùng stream ngẫu nhiên gốc khi cách coupling cho phép. Không gộp kết quả OOD vào tỷ lệ thắng primary. Nếu một biến thể chưa có physics hoặc benchmark đúng, kết quả đầu tiên là “chưa hỗ trợ”, không phải một điểm performance.

## 8. P4: website, replay, xuất dữ liệu và video

| ID | Luồng | Tiêu chí chấp nhận đề xuất |
| --- | --- | --- |
| UI-START | Người mới mở một model và chọn ví dụ | Chỉ một hành động chính rõ; model/giả định và trạng thái sẵn sàng hiển thị; không cần đọc mã |
| UI-STATE | Chuyển model/tab, reset, autoplay/pause, bấm nhanh | Không nhân đôi ngày/cập nhật; trạng thái các lượt độc lập; reset có phạm vi rõ |
| UI-INPUT | Giá trị âm, số lẻ khi cần nguyên, NaN, quá cap, rỗng | Từ chối trước khi thay trạng thái; thông báo nêu điều kiện hợp lệ |
| UI-READ | Mở giải thích Q, scrub timeline, đổi chế độ xem | Thao tác chỉ đọc không học lại hoặc sinh cầu mới |
| UI-EXPORT | CSV Unicode, comma/quote, hàng thiếu demand, tải lại | Header/đơn vị/cấu hình rõ; dữ liệu cửa hàng lost-sales không xuất D/lost cost bị che; researcher chỉ thấy ngày đã xảy ra |
| UI-ACCESS | Bàn phím, màn hình nhỏ, zoom, reduced motion | Điều khiển dùng được; chữ không bị che; không dựa vào màu đơn độc; animation có cách dừng |
| UI-RESOURCE | Mô hình Q lớn nhất được UI cho phép; nhiều reset liên tục | Giới hạn cấu hình trước cấp phát; không treo vô hạn; thông báo tải rõ; bộ nhớ trace được kiểm soát |
| VIDEO-01 | Bốn diagram động | Node/luồng đúng model, số ngày/episode và sự kiện khớp trace hoặc mô tả nguồn; không phụ đề/voice; không dùng cảnh quảng cáo thay cơ chế |
| VIDEO-02 | Hàng về và thông tin phản hồi | Pipeline không tới sớm; nợ không biến mất; learner không nhận hidden demand; virtual/physical tách rõ ở Mimic |

Đề xuất mục tiêu trải nghiệm để đo sau hiệu chuẩn: phản hồi sau một bước có cache p95 dưới 1 giây trên máy tham chiếu; khởi tạo lạnh được đo riêng vì có thể tải runtime. Các mục tiêu là tiêu chí thiết kế, chưa phải cam kết tốc độ. Ghi thiết bị, trình duyệt, CPU/RAM, mạng và trạng thái cache. Không so một cold load với một warm step để báo cáo “tăng tốc”.

Test nguồn lực bắt đầu một process/model, giới hạn mềm 2 GiB cho runner nghiên cứu và mức cấu hình UI nhỏ được hỗ trợ. Sau hiệu chuẩn có thể hạ/tăng giới hạn theo thiết bị mục tiêu; mọi lần chạm giới hạn được ghi như failure/resource result. Không mở rộng bảng Q theo J hoặc số SKU một cách không có ước lượng trước, vì reachable state/action có thể tăng rất nhanh.

## 9. Dừng, failure và điều kiện sẵn sàng báo cáo

Dừng ô thử nghiệm ngay khi có sai accounting, action không khả thi, future leakage, cập nhật hai lần, NaN không được phép hoặc state ngoài contract. Lưu cấu hình, seed, bước đầu tiên lỗi, traceback và trace tối thiểu; không tự bỏ seed lỗi rồi tính lại mean trên phần còn lại.

Nếu timeout/OOM, đánh dấu cell là resource failure, giữ số lần thử và môi trường; không đổi grid âm thầm để lấy một con số. Nếu chỉ tiêu performance xấu nhưng invariants vẫn đúng, lưu nguyên kết quả; đó có thể là phát hiện cần hiểu thêm.

Được gọi một đợt “đã kiểm tra” khi có config/hash, lệnh đã chạy, phiên bản, số lần lặp thành công/thất bại, bảng metric, đối chiếu và báo cáo giới hạn. Không dùng trạng thái “passed” cho các cell chưa chạy hoặc nhánh Mimic published đang bị chặn bởi source gate. Một bộ test đạt cho teaching adaptation không chứng nhận bản công bố.

## 10. Artifact contract cho runner tương lai

```text
run_directory/
  design.json                 # config đã khóa, nhãn hypothesis/family
  environment.json            # Python/OS/CPU/package/git hashes
  input_manifest.json         # nguồn và SHA-256; không sao chép raw vào Git
  jobs.jsonl                  # pending/running/succeeded/failed/blocked
  metrics.csv                 # một hàng cho model/case/seed/regime/checkpoint
  failures.jsonl              # invariant/resource failures, không bỏ mẫu im lặng
  traces/                     # trace tối thiểu cho case lỗi và demo đại diện
  analysis/                   # paired effects, CI, multiplicity, plots
  report.md                   # đã chạy, chưa chạy, lý do và giới hạn
```

Một hàng metric tối thiểu cần `experiment_id, model_variant, physics, case_id, split, seed, checkpoint, evaluation_regime, unit, cost_components, service_metrics, learning_diagnostics, wall_time, peak_memory, status`. Mean gộp phải giữ trọng số và số mẫu. Nhu cầu thật ở evaluator được đánh dấu để không đi vào export cửa hàng.

Python 3.10+ là nền chạy dự kiến. Dùng dependency đúng mô-đun; R không thay thế Python. Giữ bản gốc `inputs/` chỉ đọc, ghi output vào run-directory riêng. Bản kế hoạch này chưa bổ sung runner CLI hay thực thi ma trận dài; parent task có thể thêm các kiểm tra nhỏ cho những thay đổi mã thực tế, nhưng phải ghi phạm vi ấy riêng.

## 11. Đâu là bằng chứng đã có, đâu là công việc mới

Bằng chứng cloud đã lưu trước kế hoạch: tái phân tích sáu bảng benchmark, smoke 700 kỳ của ba bộ học benchmark, chuẩn bị dữ liệu theo checksum; CFO tái tạo bảng và mô phỏng lại pilot; kiểm tra 204 điểm biểu đồ trong slide. Nguồn: [benchmark validation](../results/beer_rossmann/cloud_validation.json), [CFO validation](../results/cfo/cloud_validation.json), [slide validation](../presentation/cloud_validation.json).

Các bằng chứng đó không đồng nghĩa đã chạy mọi test ID hoặc ma trận trong tài liệu này. Việc đầu tiên khi thực thi kế hoạch là tạo run manifest mới và cập nhật trạng thái từng test. Báo cáo kết quả phải giữ nhãn model gốc/thích nghi/thực hành, điều kiện hợp lệ/OOD và giả định tài chính.
