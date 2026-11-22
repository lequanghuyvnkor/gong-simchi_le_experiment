# Mô phỏng tồn kho: HQL, Meta-HQL và FQL

Website bốn mô hình và bốn video diagram nằm ở [Inventory Lab](../inventory_site/README.md). Streamlit trong thư mục này vẫn có ba lựa chọn ở tiêu đề. Lõi mới [mimic_ql.py](mimic_ql.py) phục vụ website là một [teaching adaptation có công khai giới hạn](../docs/mimic_teaching_scope.md), chưa phải replication Mimic-QL công bố. FQL mặc định giữ H=3; horizon J mở rộng chỉ dùng bởi hệ ảo của bản học Mimic.

Bạn đóng vai người quản lý cửa hàng: chọn tổng hàng sẵn bán sau bổ sung, chạy
một ngày và đọc giải thích về lượng bán, tồn dư, thông tin bị che khuất và chi phí.
Giao diện và giải thích dùng tiếng Việt. Bạn tự đặt hàng ở một cửa hàng; HQL
(episodic) hoặc Meta-HQL (giữ tồn) chạy ở một cửa hàng riêng với cùng tồn ban
đầu, chi phí và nhu cầu từng ngày.

FQL bổ sung bài toán **2 sản phẩm, chu kỳ 3 ngày, giao hàng 1 ngày**, có đơn
còn nợ. Mở <http://127.0.0.1:8501/?model=fql>. Các liên kết mô hình trong thanh
bên mở phiên riêng; không đặt lại lượt HQL/Meta-HQL đang chơi.

## Mở ứng dụng

Trong PowerShell, từ thư mục `lost_sales_lab`:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Mở <http://127.0.0.1:8501>. Có thể dùng lệnh sau để khởi động bằng script:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Ứng dụng chỉ nghe trên địa chỉ cục bộ và tắt thống kê sử dụng. Dừng máy chủ
bằng Ctrl+C ở cửa sổ đang chạy lệnh. Thiết lập mặc định nằm trong
`.streamlit/config.toml` và được đọc khi khởi động từ thư mục ứng dụng.

Liên kết <http://127.0.0.1:8501/?model=meta> mở một phiên Meta-HQL mới sẵn ở
chế độ giữ tồn, 12 chu kỳ (36 ngày). Tham số liên kết chỉ chọn mô hình khi phiên
mới chưa có cấu hình; không ghi đè một lượt chơi đang có.

## Bài tập bắt đầu

1. Giữ thiết lập mặc định: tồn đầu tiên 3, M = 20, phí lưu kho 1, phạt thiếu hàng 4.
2. Chọn y = 2 để xem ràng buộc y ≥ x ngăn quyết định không khả thi.
3. Chọn y = 5 và bấm **Chạy ngày 1**. Đơn bổ sung là q = y − x = 2.
4. Khi bán hết, đọc cận dưới D ≥ S. Bật **Xem góc nhìn người nghiên cứu** để xem
   nhu cầu thật và chi phí bị che khuất của ngày đã chạy.
5. Chạy đủ 3 ngày để xem bước loại bỏ tồn dư cuối chu kỳ. Mở **Lịch sử & chi phí**.
6. **Chơi lại cùng tình huống**, chọn cách đặt hàng khác. Cùng mã tình huống giữ
   nguyên nhu cầu từng ngày, độc lập với các quyết định đặt hàng.
7. Trong thanh bên, đổi sang giữ tồn qua chu kỳ rồi bấm **Áp dụng và bắt đầu lại**.

## Xem HQL và so sánh với cách tự đặt hàng

1. Chọn chế độ **Loại bỏ hết (episodic)**, giữ cận **Theo bài báo · hệ số 8**.
2. Mở **HQL từng bước** để xem kế hoạch ngày sắp chạy. Thuật toán chọn mức cao
   nhất còn trong tập ứng viên; khi tồn đang cao hơn tập đó, nó đặt thêm 0.
3. Tự chọn y và bấm **Chạy ngày**. Cả hai phía quyết định trước khi nhu cầu chung
   được sinh đúng một lần. Tồn kho của hai cửa hàng được theo dõi riêng.
4. HQL chỉ thu phản hồi trong ngày 1–2. Sau ngày 3, mở **HQL từng bước**, chọn
   chu kỳ rồi bấm **Bước Q tiếp**. Xem quỹ đạo giả định, điểm dừng τ, tổng thưởng,
   V tiếp nối, α, Q cũ/mới và bước loại ứng viên. Có thể kéo thanh bước để nhảy
   đến vị trí khác hoặc bấm **Xem hết chu kỳ**.
5. Phát lại chỉ đọc dấu vết đã lưu: không chạy thêm ngày, không sinh lại nhu cầu
   và không học lặp lần nữa. Có thể chọn lại quyết định hoặc chu kỳ đã chạy.
6. Mở **So sánh** để xem chi phí giả định lũy kế và chênh lệch Bạn − HQL. Bật
   góc nhìn người nghiên cứu để xem nhu cầu chung và tổng chi phí thật mỗi bên.
   Tải CSV để giữ các quyết định, chi phí, tên phiên bản và hệ số cận đã dùng.

Xem phản hồi/Q của HQL khi đang chơi có thể cung cấp thêm thông tin cho bạn.
Để tự thử mà không xem phía HQL, hãy hoàn tất quyết định thủ công trước rồi mở
các tab phân tích. Đây là so sánh mô tả trên một chuỗi nhu cầu, không phải ước
lượng regret kỳ vọng so với chính sách tối ưu biết phân phối.

### Quy ước HQL và các điều chỉnh để học

- Theo **Algorithm 1, Mục 4, trang 6146–6147** của bản gốc: Q khởi tạo bằng H;
  chọn `max(A_h)`; cập nhật cuối chu kỳ theo `h = H,…,1`; loại theo chênh lệch Q.
- Phần thưởng `r = (oM − oI + pS) / ((o+p)M)` nằm trong `[0,1]` và là biến đổi
  affine của chi phí giả định. `α_k = (H+1)/(H+k)`.
- Cận gốc `CB1 = 8 sqrt(H^5 × 9 log(AT)/(k−1))`. Chu kỳ đầu lấy cận vô hạn,
  giữ tất cả hành động, để xử lý mẫu số 0 ở k = 1.
- Bản học dùng lưới nguyên `0,…,M`, tức `A=M+1`, cùng đơn vị với thao tác thủ
  công; bài báo dùng lưới mịn phụ thuộc T. Mọi so sánh hiển thị dùng lưới của bản học.
- Tại một hành động giả định, tái dựng lượng bán bằng `min(tồn giả định, S_HQL)`.
  Nếu trạng thái ở bước sau chưa chọn được trong tập ứng viên, không đặt thêm
  và tiếp tục tới τ. Cộng thưởng từ h đến **τ−1**, rồi nối Vτ; V của bước sau dùng
  Q vừa cập nhật trong vòng lặp ngược. Tập ứng viên của chu kỳ k được giữ cố định
  để xác định điểm dừng; tập thu hẹp dùng cho chu kỳ k+1.
- Bộ học chỉ nhận `S_HQL`; không nhận D thật, chi phí thiếu hàng thật, seed,
  tham số phân phối hay lượng bán của cửa hàng thủ công.
- Với hệ số 8, trong vài chu kỳ ngắn, Q có thể thay đổi nhưng tập ứng viên vẫn
  giữ nguyên. HQL có thể tiếp tục chọn M để khám phá và có chi phí cao lúc đầu.
- Tùy chọn **Minh họa thu hẹp nhanh · hệ số 0.001** thay đổi cận để nhìn thấy
  cơ chế loại hành động sớm. Đây là biến thể minh họa, **không có đảm bảo lý
  thuyết của cận gốc**. Nhãn trên giao diện và CSV luôn ghi rõ phiên bản.
- HQL ở đây chạy cho episodic. Khi chọn nondiscarding, Meta-HQL điều phối ba
  bản sao dịch pha, dùng cùng phần lõi cập nhật Q và phản hồi bị kiểm duyệt.

## Xem Meta-HQL khi giữ tồn qua chu kỳ

1. Mở liên kết Meta-HQL ở trên, hoặc chọn **Giữ sang chu kỳ sau (nondiscarding)**
   trong thanh bên rồi **Áp dụng và bắt đầu lại**. Khoảng 12 chu kỳ giúp quan sát
   nhiều lần chuyển nhánh; chu kỳ nhu cầu vẫn luôn dài 3 ngày.
2. Chọn mức hàng thủ công và bấm **Chạy ngày**. Cả hai cửa hàng giữ toàn bộ hàng
   dư qua ngày, qua chu kỳ và cả lúc Meta-HQL đổi bản sao. Hàng không bị vứt để
   ép việc chuyển nhánh.
3. Mở **Meta-HQL từng bước**: bảng ba nhánh có thứ tự pha thực `1–2–3`, `2–3–1`,
   `3–1–2`, số tập riêng K_w, ước lượng V₁, trần bắt đầu và trạng thái chọn/loại.
4. Dòng thời gian phân biệt **Chạy HQL** với **Chờ chuyển**. Chọn một ngày, bấm
   **Bước bandit tiếp** để xem lịch phân khối, điều kiện chuyển, quyết định đặt,
   phản hồi, cập nhật Q, chặn tập, so sánh nhánh và chọn khối kế tiếp.
5. Bộ đếm thời gian thực vẫn tăng trong ngày chờ; không bản sao nào được học từ
   ngày chờ. Bản sao chỉ học khi chạy đủ tập 3 ngày nội bộ, có thể bắc qua ranh giới
   chu kỳ lịch. Tập còn dở ở cuối chân trời không được tính thành tập hoàn tất.
6. **So sánh** hiển thị Bạn và Meta-HQL trên cùng một lần sinh nhu cầu mỗi ngày,
   gồm cả chi phí ngày chờ. CSV có nhánh được chọn, pha bandit, ngày nội bộ,
   trạng thái chờ/chạy, hệ số cận và các chi phí được phép xem theo góc nhìn.
7. Có thể xem Q riêng từng bản sao hoặc các phép cập nhật của tập vừa kết thúc.
   Phát lại chỉ đọc dấu vết; đổi ngày xem, bản sao xem hoặc bước bandit không làm
   phát sinh nhu cầu mới và không huấn luyện lặp lại.

### Lịch bandit, chuyển kho và các lựa chọn triển khai

- Theo mô tả Mục 5 và Algorithm 2 (trang 6149–6150): nhánh w là bản sao coi pha
  w là ngày nội bộ 1. Ở pha bandit j = 0,1,…, mỗi nhánh còn lại được chạy thêm
  `2^j` tập. Như vậy các khối lần lượt có 1, 2, 4,… tập, không phải chọn tham lam
  nhánh điểm cao nhất từng ngày.
- Trước khi vào khối mới, đặt thêm 0 cho đến đúng pha w và tồn kho thực không
  vượt trần ngày đầu của bản sao. Trong một khối, các tập nối tiếp liên tục;
  nếu tồn cao hơn tập ứng viên thì HQL đặt thêm 0 theo quy tắc gốc.
- Bộ học episodic có reset trạng thái ảo khi kết thúc tập. Lớp Meta luôn giữ
  tồn kho thực và đồng bộ nó khi thực thi quyết định kế tiếp, nên không có
  lượng loại bỏ thật nào trong chế độ nondiscarding.
- Mỗi nhánh có Q, tập ứng viên, lịch sử và số tập riêng độc lập. Bộ học nhận
  duy nhất doanh số riêng S = min(y,D); không nhận D thật, chi phí thiếu hàng thật,
  seed, phân phối nhu cầu, hay dữ liệu cửa hàng thủ công.
- `V₁^(w) = max Q₁^(w)(y)` trên tập còn lại. Bản học xét loại ở cuối pha, khi
  các nhánh đã hoàn tất các khối được giao, theo mô tả pha trong Mục 5:
  loại nếu `V tốt nhất − V₁^(w) ≥ 2CB₂(K_w)` với
  `2CB₂(K_w) = 4 C₂ sqrt(H^7 log(T) / K_w)`. K_w đếm tập riêng đã hoàn tất.
- C₂ không có giá trị số cố định trong bài. **C₂ = 1** là lựa chọn của bản học
  theo công thức, không phải khẳng định đã hiệu chỉnh hằng số lý thuyết. Tùy chọn
  C₂ = 0.001 hoặc cận hành động nhỏ chỉ để quan sát loại nhánh sớm; nhãn và CSV
  ghi rõ hệ số và chữ **minh họa**.
- Sau mỗi tập, trần các tập ứng viên ngày nội bộ 2–3 được chặn theo trần ngày đầu.
  Nếu việc chặn làm rỗng tập, dừng nhánh đó (cũng là tình huống trả tín hiệu dừng
  trong mã replication). Với nhánh cuối, bản học giữ tập ứng viên trước cập nhật
  để tiếp tục ván, ghi sự kiện bảo vệ và cảnh báo rõ. Đây là bảo vệ thực hành,
  không dùng để khẳng định đảm bảo regret của thuật toán lý thuyết.
- Hai bên cùng giới hạn tồn M, phí, tồn ban đầu và chuỗi nhu cầu; riêng trạng thái
  tồn và quyết định độc lập. Hiệu quả hiển thị mô tả chuỗi mẫu đã chạy. Xem trace
  của Meta-HQL khi đang chơi có thể cung cấp thêm thông tin cho người chơi.

Đổi số, bật góc nhìn hay xem các tab không sinh thêm nhu cầu. Chỉ nút Chạy ngày
thực hiện một bước; số ngày mặc định là 9 (3 chu kỳ). Thay đổi thiết lập áp dụng
sau khi xác nhận bắt đầu lại. Lịch sử lưu trong phiên trình duyệt; tải CSV để lưu
lâu dài. Tải lại phiên hoặc khởi động lại máy chủ có thể mất lịch sử chưa xuất.

## Quy ước mô hình lost-sales

- `x`: tồn đầu ngày; `y`: tổng hàng sau bổ sung; `q = y − x`: đặt thêm.
- `0 ≤ x ≤ y ≤ M`. Mức tồn và lượng hàng trong bản học là số nguyên.
- Hàng đến ngay; sau đó nhu cầu `D` phát sinh. `S = min(y,D)`, `I = y − S`,
  `L = max(D−y,0)`. Nhu cầu không được phục vụ rời đi, không mang nợ sang hôm sau.
- Chi phí thật `C = oI + pL`; chi phí giả định quan sát được `C̃ = oI − pS`.
  Đồng nhất thức `C − C̃ = pD` hỗ trợ so sánh chính sách dùng cùng nhu cầu.
- Bán hết, kể cả trường hợp D thật bằng y hoặc y = 0, chỉ cho biết `D ≥ y`.
  Lịch sử riêng của bạn ở góc nhìn cửa hàng không xuất các cột nhu cầu thật,
  lượng cầu mất hoặc tổng chi phí thật bị che khuất. Góc nhìn người nghiên cứu
  chỉ mở dữ liệu đã xảy ra. Tab HQL ghi rõ phản hồi riêng của cửa hàng HQL;
  xem phản hồi đó có thể cung cấp thêm thông tin cho người chơi.
- Nhu cầu Poisson độc lập; trung bình lặp theo 3 ngày, mặc định `(4,8,5)`.
  Phân phối Poisson là lựa chọn minh họa, không phải yêu cầu của bài báo.
- Mặc định episodic: sau ngày thứ 3, tính phí lưu kho trên hàng dư rồi loại bỏ,
  giá trị thanh lý 0, phí loại bỏ thêm 0, tồn đầu chu kỳ mới bằng 0.
  Nondiscarding giữ hàng dư sang chu kỳ sau.
- Chi phí mua hàng chuẩn hóa bằng 0; o và p dương, giữ cố định trong một thí nghiệm.
  Chi phí giả định có thể âm; không diễn giải nó thành lợi nhuận.

Nguồn: Gong & Simchi-Levi, *Bandits atop Reinforcement Learning: Tackling Online
Inventory Models with Cyclic Demands*, Management Science 70(9), 2024, Mục 2.
<https://doi.org/10.1287/mnsc.2023.4947>

## FQL: 2 sản phẩm, backlogging, giao hàng 1 ngày

Mở <http://127.0.0.1:8501/?model=fql>, hoặc chọn liên kết FQL trong thanh bên.
Khác lost-sales, nhu cầu chưa phục vụ được ghi thành **đơn còn nợ**. Nhu cầu
được quan sát đầy đủ; không cần bật góc nhìn người nghiên cứu.

1. Trong **Chạy từng ngày**, xem tồn trong kho, nợ khách, và hàng đặt hôm qua
   đang đến hôm nay. Chọn số lượng **đặt thêm** A/B, không phải mức tồn mục tiêu.
2. Bấm **Chạy ngày**. Đơn mới đến ngày mai. Hàng về hôm nay trả nợ cũ trước,
   rồi phục vụ nhu cầu mới. Hai cửa hàng chốt đơn trước cùng một lần sinh cầu.
3. Mở **Dòng hàng & chi phí** để chọn cửa hàng/ngày; xem toàn bộ số dư trước
   và sau nhận/giao hàng, tiền mua, phí đặt chung, phí lưu kho và phí chờ giao.
4. Sau đủ 3 ngày, mở **FQL từng bước**, bấm **Bước Q tiếp**. Thuật toán quét
   ngày 3 → 2 → 1. Mỗi bước cập nhật toàn bộ trạng thái và cặp đơn của ngày đó.
   Chọn một trạng thái giả định và một cặp đơn để xem C, r, V tiếp nối, α,
   Q cũ, mục tiêu và Q mới. Các nút chỉ phát lại, không huấn luyện thêm.
5. Trong **So sánh**, xem chi phí lũy kế, tồn/nợ/đang về từng sản phẩm và
   tải CSV đầy đủ. Chơi lại cùng seed giữ cùng nhu cầu để thử đơn khác.

### Vật lý và ranh giới của bản FQL

- N = 2, H = 3, L = 1 cố định. Trạng thái trước nhận hàng là
  `x=(nA,nB,pA,pB)`, trong đó `n=tồn trong kho−nợ`, `p=hàng đến hôm nay`.
  Hành động `y=(qA,qB)` trong Algorithm 3 là số lượng đặt thêm.
- Chuyển trạng thái trong episode: `n'=n+p−D`, `p'=q`. Tồn cuối `max(n',0)`,
  nợ cuối `max(−n',0)`. Không chặn nợ, không cắt ngọn tồn, không giao đơn mới
  ngay trong ngày đặt. Không có tồn dương và nợ dương đồng thời ở cùng mã hàng.
- Mặc định qA/qB nguyên từ 0–3, tồn ban đầu (1,1), tiền mua (1,1.5), lưu kho
  (0.5,0.5), chờ giao (4,5), phí đặt chung F=2. Khoản F chỉ tính một lần nếu
  đặt ít nhất một mã; tiền mua tính ngay ngày đặt. Phí chờ đánh trên toàn bộ
  nợ cuối mỗi ngày, gồm nợ cũ còn chưa phục vụ. Không có sức chứa hay ngân sách
  chung. Cả hai bên chịu cùng phí và hạn mức.
- Nhu cầu mỗi mã dùng Binomial(4,p), miền 0–4; trung bình theo ngày lần lượt
  `(A,B)=(1,2),(3,1),(2,3)`. Các mẫu độc lập; phân phối lặp theo chu kỳ.
  Đây là lựa chọn hữu hạn của bản học, không phải cắt ngọn Poisson hay điều
  kiện bắt buộc của bài báo. Bộ học chỉ biết miền và các nhu cầu đã xảy ra,
  không nhận p, trung bình, seed hoặc nhu cầu tương lai.
- Đây là các **hợp đồng 3 ngày độc lập**. Cuối ngày 3, giữ nguyên số dư tồn,
  nợ và đang về trong lịch sử, tính đủ chi phí ngày 3 rồi đặt V4=0. Các khoản
  thanh lý, thu hồi, phạt cuối hợp đồng đều đặt 0. Episode sau khởi tạo lại
  cùng tồn ban đầu, nợ 0, đang về 0. Đơn đặt ngày 3 vẫn trả tiền nhưng không
  đem lại lợi ích trong episode. Đây là quy ước terminal cụ thể của bản học,
  không diễn giải thành hủy nợ khách miễn phí trong vận hành liên tục. Mô hình
  giữ các số dư qua chu kỳ thuộc nondiscarding/Mimic-QL, chưa thêm ở đây.

### Cơ chế FQL và phạm vi đối chiếu bài báo

- Theo Mục 7.1, **Algorithm 3, trang 6154** của bản gốc: Q khởi tạo bằng H,
  chọn cặp đơn khả thi có Q cao nhất; khi hòa lấy nhỏ nhất theo A rồi B.
  Đợi hết episode, cập nhật ngược với `αk=(H+1)/(H+k)`.
- Với mỗi ngày h, dùng đúng nhu cầu đã thấy ở h để tái tính `r(x,y)` và x' cho
  **mọi trạng thái tới được và mọi hành động**, bao gồm các ô chưa được ghé.
  `Qh=(1−α)Qh+α[r+max Qh+1(x',y')]`, dùng Q ngày sau vừa cập nhật. Không
  bandit, không loại ứng viên, không cần thăm hết từng ô để nhận phản hồi.
- Chuẩn hóa cố định `r=1−C/Cmax` nằm trong [0,1]. Cmax là cận an toàn trên toàn
  miền tới được: phí đặt tối đa + tiền mua tối đa + với mỗi mã, lấy lớn hơn
  giữa phí lưu tối đa và phí chờ tối đa. Tối đa tổng r tương đương tối thiểu
  tổng C trong các episode dài bằng nhau. Đây không phải lợi nhuận.
- Liệt kê toàn bộ trạng thái tới được từ trạng thái đầu với giới hạn cầu/đơn
  đã công bố; mặc định có **43 280 ô Q**. Đây là rút miền chính xác cho MDP
  hữu hạn này, không phải xấp xỉ hay gom trạng thái. Các phép quét được vector
  hóa; lưu dấu vết bất biến để phát lại từng ngày và xem từng ô.
- Chưa đưa ra đảm bảo regret cho các quy ước của bản học. So sánh một chuỗi mẫu
  với người chơi không phải phép ước lượng regret so với chính sách biết phân
  phối. FQL có thể tốn hơn lúc đầu; xem Q trước khi chốt có thể gợi ý cho bạn.

Phần này dùng các mô-đun `fql_model.py`, `fql.py`, `fql_experiment.py` và
`fql_ui.py`, tách trạng thái khỏi HQL/Meta-HQL để bảo toàn các lượt đang chơi.

## Kiểm tra

```powershell
python -m pytest tests -q
```

Cần `pytest` để chạy kiểm tra. Các kiểm tra bao gồm bảo toàn hàng, kiểm duyệt
nhu cầu, thời điểm chuyển chu kỳ, đồng nhất thức chi phí, tái lập chuỗi nhu cầu
và các luồng tương tác bằng Streamlit AppTest. Phần HQL còn kiểm tra cập nhật
ngược bằng ví dụ tính tay, điểm dừng trễ, một mẫu nhu cầu chung mỗi ngày,
độc lập với thông tin bị che khuất và quyết định của người dùng, tính thuần đọc
của bộ phát lại, cùng hiển thị/đặt lại trạng thái trên giao diện. Meta-HQL được
kiểm tra thêm ánh xạ pha, lịch khối 1–2–4, chờ pha/chờ tồn, không học trong ngày
chờ, giữ tồn thực qua tập ảo, đếm tập hoàn tất, công thức loại nhánh, các bảo vệ
tập rỗng và so sánh tính đủ chi phí của mọi ngày thực.

FQL được kiểm tra thêm độ trễ một ngày, ưu tiên trả nợ cũ, bảo toàn hàng và nợ,
phí đặt chung, sổ cuối episode, miền trạng thái đóng dưới mọi chuyển tiếp,
cập nhật mọi ô Q đối chiếu phép tính Bellman độc lập, Q ngày sau vừa cập nhật,
ví dụ tính tay, chuẩn hóa thưởng, chỉ một lần sinh cầu/ngày, độc lập với đơn
thủ công, phát lại chỉ đọc và bảo toàn phiên HQL khi mở/đóng giao diện FQL.
