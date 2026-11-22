# Báo cáo CFO lưu trữ — giả định mẫu, không phải chi phí doanh nghiệp thật

Trích phần C của báo cáo chủ dự án cung cấp. Các bảng dẫn chiếu ở phần B nằm trong [benchmark](../../benchmarks/beer_rossmann/README.md). Các số trong phần C được kiểm tra lại tại [kết quả CFO](../../results/cfo/). Nguồn tài chính [6–8] được liệt kê cuối tệp; chỉ dẫn để giải thích, không xác nhận đơn giá.

## C1 Đọc phản biện dưới góc độ quyết định đầu tư

Phản biện của người hướng dẫn yêu cầu thu hẹp kết luận và kiểm tra lợi ích so với phương án đơn giản trước khi chọn công nghệ. Phần C phân tích lại kết quả đã có và bổ sung mô phỏng học ngắn 365 kỳ. Cả hai là phân tích hậu kiểm, không thuộc thiết kế chính đã khóa. Các số VND là sample do nghiên cứu giả định theo yêu cầu của người dùng, chưa phải chi phí thực của Beer, Rossmann hay một cửa hàng được khảo sát.

| Nhận định cần xử lý | Cách diễn giải và việc còn cần làm |
|---|---|
| Môi trường thuận lợi cho HQL | Giới hạn kết luận vào miền cyclic, biết H, lead time 0; cần thử tự tương quan, drift và sai H |
| Meta-HQL-P đã đổi ngưỡng và xử lý tập rỗng | Dùng đúng tên bản hiệu chỉnh; cần phân tích độ nhạy và ablation trước khi gán lợi ích cho từng cơ chế |
| DQN có thể học chưa tốt | Cần so mục tiêu chi phí bình quân, ngân sách tuning và chẩn đoán; tồn kho cao không tự chứng minh có lỗi mã |
| Baseline theo thứ gần bằng Meta | CFO phải so với chính sách khả thi tốt nhất và tính chi phí tăng thêm |
| Chi phí học có thể đảo kết luận | Phải xác định học trong mô phỏng hay học bằng hàng thật |

HQL khai thác phản hồi suy ra cho các mức tồn kho thấp hơn là một lợi thế cấu trúc của thuật toán. Khi cả hai được phép dùng cùng thông tin gốc, lợi thế đó không tự tạo vi phạm công bằng. Một ablation DQN có bổ sung mẫu suy ra sẽ giúp xác định lợi ích đến từ xử lý phản hồi hay từ cách cập nhật giá trị.

Prior weekday có bước ước lượng phân vị từ lịch sử 2013; nó không phải chính sách hoàn toàn không học. Nó không cập nhật bằng RL trong vận hành. Với doanh nghiệp có lịch sử đầy đủ, đây là phương án đối chứng thực dụng cần vượt.

Không suy từ bảng hòa vốn sau 21 000 kỳ rằng DQN luôn thắng ở mọi thời hạn thực tế. Bảng đó dùng toàn bộ chi phí học ở chân trời đã chạy; nó không đo riêng 30, 90 hoặc 365 ngày học trực tiếp ban đầu. Cần ghi chi phí theo từng mốc thử nghiệm mới trước khi phát biểu về các thời hạn ấy.

## C2 Chi phí CFO cần đo và đơn vị tiền

Chi phí benchmark chỉ gồm giữ hàng và mất bán trên nhu cầu đã chuẩn hóa. Nó chưa bao gồm hóa đơn máy tính, lao động, triển khai, giấy phép, đặt hàng cố định, vận chuyển hoặc dữ liệu. Không thể đọc chi phí 0,807 thành 0,807 đồng hay doanh thu tiết kiệm 80,7%.

| Khoản cần đo | Cách xác định và giới hạn |
|---|---|
| Giữ hàng h | VND trên đơn vị hàng và kỳ; tách chi phí vốn, kho, bảo quản và rủi ro |
| Thiếu hàng l | Lãi đóng góp thực mất sau xét mua bù và thay thế; không mặc định bằng giá bán |
| Đặt và nhận hàng | Chi phí cố định mỗi đơn, vận tải, xử lý, MOQ và lead time |
| Đầu tư hệ thống | Tích hợp, dữ liệu, phát triển, kiểm chứng và thử nghiệm thực tế |
| Vận hành hệ thống | Nhân sự, máy tính, giám sát, tái huấn luyện và sự cố |
| Vốn lưu động | Hàng trong kho, hàng đi đường, phải thu và phải trả; cần ghi riêng với chi phí kỳ |

Gọi v là giá vốn một đơn vị, i là tỷ lệ chi phí vốn năm và h khác là phần chi phí giữ hàng còn lại. Với một kỳ là một ngày, có thể lập giả định ban đầu:

$$h=vi/365+h_{\mathrm{other}},\qquad p=\ell/h.$$

ACCA trình bày chi phí giữ và đặt hàng như các khoản cần cân đối trong quản trị tồn kho [6]. Đơn giá tại đây cần lấy từ doanh nghiệp; không dùng một tỷ lệ ngành chưa được xác minh.

Lãi đóng góp mất được tính từ doanh thu mất trừ những chi phí biến đổi tránh được. Nếu đã dùng đại lượng này để tính mất bán thì không cộng thêm toàn bộ doanh thu mất lần nữa. Nếu dùng báo cáo dòng tiền, phải tính bán, mua và hàng tồn cuối kỳ theo cùng một cơ sở.

Theo IAS 2, giá trị hàng tồn và việc ghi nhận thành chi phí khi bán hàng là hai thời điểm khác nhau [7]. Khoản giải phóng vốn tồn kho không phải khoản tiết kiệm chi phí được lặp lại mỗi năm. Tồn cuối kỳ trong mô phỏng cũng chỉ là đại diện một phần cho vốn lưu động, vì chưa đo hàng trong ngày hoặc đi đường.

## C3 Hai sample và cách đổi chi phí chuẩn hóa sang VND

Sample A được chọn để khớp miền p đã chạy. Sample B kiểm tra một cấu hình tài chính khác có còn nằm trong miền kết luận hay không. Cả hai là giả định minh họa; không phải bảng giá thị trường hoặc số liệu cửa hàng thật.

| Tham số | Sample A dùng quy đổi | Sample B để kiểm tra miền áp dụng |
|---|---|---|
| Nhu cầu mốc một SKU | 100 đơn vị mỗi ngày | 100 đơn vị mỗi ngày |
| Giá vốn | 50 000 VND mỗi đơn vị | 50 000 VND mỗi đơn vị |
| Lãi đóng góp mất | 1 000 VND mỗi đơn vị | 20 000 VND mỗi đơn vị |
| Giữ hàng mỗi ngày | 100 VND mỗi đơn vị | Chỉ giả định 25% giá vốn mỗi năm |
| Tỷ số l chia h | 10 | 584 |
| Được bao phủ bởi p đã chạy | Có ở p bằng 10 với giả định mô hình giữ nguyên | Chưa; phải chạy lại với đơn giá mới |

Trong sample A, giá bán giả định 55 000, giá vốn 50 000 và chi phí phục vụ biến đổi tránh được 4 000 tạo lãi đóng góp 1 000 VND. Giữ hàng 100 VND là giả định chi phí bằng tiền, chưa cộng chi phí cơ hội của vốn; vốn lưu động được xét riêng. Đơn giá này không được suy ra từ hai bộ dữ liệu. Với bảng 18 điều kiện, giữ h bằng 100 và thay l thành 100, 500, 1 000 tương ứng p bằng 1, 5, 10; các hàng p bằng 1 và 5 là hai kịch bản biên lợi nhuận khác sample A.

Nếu xấp xỉ hàng thật bằng m lần lượng chuẩn hóa và giữ nguyên p, sức chứa 4 tương ứng 400 đơn vị, bước hành động 0,2 tương ứng 20 đơn vị. Khi ấy:

$$C_{j,\mathrm{VND/period}}=hm\,\bar C_j,\qquad C_{j,\mathrm{year}}=365hm\,\bar C_j.$$

Một điểm chi phí chuẩn hóa trong sample A bằng 10 000 VND mỗi ngày. Phép đổi đúng khi giữ cùng mô hình và tỷ số l chia h. Nếu đổi p, lead time, sức chứa theo nhu cầu hoặc ràng buộc phục vụ, không nhân chi phí cũ để khẳng định chính sách tối ưu mới. Rossmann là doanh thu tổng hợp nên chưa có m theo đơn vị SKU để quy đổi như cửa hàng vật lý.

## C4 Học offline và học trực tiếp có hai bài toán chi phí

Khi học offline trên mô phỏng, các khoản giữ hàng và thiếu hàng của 21 000 bước là chỉ số mô phỏng. Chi phí thật gồm dữ liệu, xây dựng môi trường, máy tính, nhân sự, kiểm chứng và thử nghiệm triển khai. Ngân sách 21 000 quan sát không đòi hỏi chờ 21 000 ngày kinh doanh.

$$TC_j^{\mathrm{offline}}(K)=F_j+C_{j,\mathrm{compute}}+C_{j,\mathrm{pilot}}+K\big(hm\bar C_{j,\mathrm{deploy}}+o_j\big).$$

F là chi phí ban đầu có thể thay đổi theo quyết định và o là chi phí vận hành hệ thống mỗi kỳ. Phải nêu rõ khoản nào đã nằm trong F để không cộng trùng máy tính hoặc pilot.

Khi học bằng hàng thật, dùng tổn thất thực phát sinh trên đúng L kỳ triển khai, so với chính sách mà cửa hàng sẽ dùng nếu không thử thuật toán:

$$\Delta TC_j(L,K)=\Delta F_j+\sum_{t=1}^{L}\big(c_{j,t}-c_{b,t}\big)+K\big(\bar c_{j,\mathrm{deploy}}-\bar c_{b,\mathrm{deploy}}\big)+\Delta O_j.$$

Đây là chi phí tăng thêm so với baseline, không phải toàn bộ chi phí cửa hàng cộng thêm một lần nữa. Nếu đã đo chi phí học thực trong tổng chi phí vận hành, không đưa nó vào mục pilot lần thứ hai.

Bảng B17 chỉ ước lượng điểm hòa vốn sau toàn bộ 21 000 kỳ học dưới cùng mô hình. Khoảng 15 908 đến 684 368 là số kỳ triển khai đóng băng tiếp theo, chưa cộng thời gian học. Nếu tự giả định một kỳ là một ngày, khoảng này tương đương gần 44 đến 1 875 năm, nhưng chưa phải dự báo doanh nghiệp; giả định phân phối ổn định lâu như vậy không được kiểm chứng.

Mục C5 bổ sung phép mô phỏng chi phí học tại các mốc 30, 90 và 365 kỳ để tránh suy ngược từ trung bình 21 000 kỳ. Nó chưa cung cấp hóa đơn cửa hàng. Pilot thật vẫn cần ghi giao dịch, tồn kho, mất bán ước lượng, số lần can thiệp và giờ nhân sự. Hóa đơn CPU và lao động của các lần chạy trước cũng chưa được thu thập theo giao thức chi phí.

## C5 Mô phỏng bổ sung ngân sách học trong 365 kỳ

Chạy mới toàn bộ 18 điều kiện với bốn dạng tuần, 30 seed từ 6000 đến 6029 và cùng đường nhu cầu cho hai tác nhân. Ngân sách học là 365 kỳ ngay từ đầu; các mốc 30 và 90 là đoạn đầu của lần học này. Cấu hình chọn từ nghiên cứu trước được giữ nguyên, không tuning lại cho pilot ngắn. Đây là thử nghiệm hậu kiểm trên mô phỏng Gamma, không phải cửa hàng thật.

Baseline theo thứ được ước lượng trước từ 3 500 mẫu riêng, nên có lợi thế lịch sử so với hai tác nhân bắt đầu học từ đầu. Nó đại diện phương án cửa hàng đã có. Muốn so một triển khai có đầy đủ lịch sử, cần thử thêm RL được học offline trước khi ra cửa hàng.

Bảng dùng sample mốc 100 đơn vị mỗi ngày và giữ hàng 100 VND mỗi đơn vị mỗi ngày. Lãi mất là 100, 500, 1 000 VND khi p bằng 1, 5, 10. Số tiền là tổng giữ hàng cộng lãi đóng góp mất trong đúng số kỳ đã ghi, tính bằng triệu VND mỗi SKU; chưa có phí công nghệ. Mỗi dòng gộp cân bằng sáu ô mùa vụ và nhiễu.

|Kỳ|p|SRDQN|Meta|Theo thứ|Meta %|SRDQN %|Theo thứ %|
|---|---|---|---|---|---|---|---|
|30|1|0.474|0.872|0.117|99.1|90.3|76.6|
|30|5|0.601|0.885|0.276|99.1|90.2|93.0|
|30|10|0.756|0.900|0.362|99.1|90.1|96.4|
|90|1|1.397|2.581|0.346|98.1|89.6|76.4|
|90|5|1.781|2.654|0.813|98.1|90.0|93.0|
|90|10|2.250|2.742|1.065|98.1|89.8|96.5|
|365|1|4.884|10.790|1.400|98.8|86.3|76.3|
|365|5|6.762|10.988|3.285|99.0|90.8|93.0|
|365|10|8.451|11.178|4.304|99.0|91.7|96.5|

Ba cột phần trăm là mức đáp ứng theo lượng. Ở cả chín dòng, Meta có chi phí trung bình cao hơn DQN và baseline. Tại p bằng 10 sau 365 kỳ, baseline có mức đáp ứng bình quân khoảng 96,5%, Meta 99,0% và DQN 91,7%. Nếu mức tối thiểu 95% được yêu cầu, chi phí thấp của DQN chưa đủ để chọn nó; baseline theo thứ cần được kiểm chứng trước khi trả thêm cho Meta. Các mức trung bình chưa phải bảo đảm SLA từng SKU.

Bảng không chứng minh ý nghĩa thống kê từng hàng. Phân rã từng ô, seed và mốc nằm trong results_pilot.csv; tổng 4 320 mô hình của hai tác nhân được học trong 365 kỳ, cùng 2 160 đường baseline. Nếu pilot 30 hoặc 90 kỳ là toàn bộ chân trời biết trước, phải chạy lại với ngân sách ấy.

## C6 Chi phí theo điều kiện khi nhiễu thấp

Bảng quy đổi dùng 100 đơn vị nhu cầu mốc mỗi ngày, giữ hàng 100 VND mỗi đơn vị mỗi ngày và giả định 365 ngày vận hành. Chi phí là giữ hàng cộng lãi đóng góp mất, chưa cộng hệ thống. Mỗi hàng là trung bình bốn dạng tuần và 30 seed. Đơn vị tiền trong bảng là triệu VND mỗi SKU mỗi năm.

|a|p|SRDQN|Meta|Theo thứ|Theo thứ trừ Meta|Đáp ứng Meta %|
|---|---|---|---|---|---|---|
|0.0|1|0.92|0.73|0.73|0.000|90.0|
|0.0|5|3.15|1.49|1.49|0.000|96.5|
|0.0|10|5.06|1.85|1.86|0.010|99.0|
|0.4|1|0.89|0.74|0.74|0.000|88.6|
|0.4|5|3.27|1.49|1.50|0.003|97.2|
|0.4|10|5.02|1.86|1.86|0.005|98.7|
|0.8|1|0.93|0.79|0.76|-0.034|86.6|
|0.8|5|2.84|1.55|1.57|0.016|96.7|
|0.8|10|4.60|1.98|1.99|0.011|98.5|

Cột theo thứ trừ Meta dương là lợi ích vận hành tối đa trước chi phí hệ thống; số âm nghĩa là Meta tốn hơn baseline. Đây là ước lượng điểm hậu kiểm, không phải mức tiết kiệm VND đã xác nhận bằng thử nghiệm cửa hàng.

p bằng 1, 5, 10 tương ứng lãi mất giả định 100, 500, 1 000 VND mỗi đơn vị. Nếu cửa hàng cần mức đáp ứng tối thiểu 95%, phải kiểm tra mức phục vụ trước khi so tiền; phần trăm trung bình của một ô không bảo đảm từng SKU hoặc từng thời kỳ đạt 95%.

Tệp 18_condition_financial_scenarios.csv chứa toàn bộ chi phí gốc, phép đổi, tồn kho, mức đáp ứng và điểm hòa vốn từng ô. Không dùng trung bình các ô như tỷ trọng thị trường thực khi chưa có trọng số doanh nghiệp.

## C7 Chi phí theo điều kiện khi nhiễu cao

Bảng quy đổi dùng 100 đơn vị nhu cầu mốc mỗi ngày, giữ hàng 100 VND mỗi đơn vị mỗi ngày và giả định 365 ngày vận hành. Chi phí là giữ hàng cộng lãi đóng góp mất, chưa cộng hệ thống. Mỗi hàng là trung bình bốn dạng tuần và 30 seed. Đơn vị tiền trong bảng là triệu VND mỗi SKU mỗi năm.

|a|p|SRDQN|Meta|Theo thứ|Theo thứ trừ Meta|Đáp ứng Meta %|
|---|---|---|---|---|---|---|
|0.0|1|2.17|2.02|2.02|0.001|62.4|
|0.0|5|6.39|4.79|4.79|0.004|88.7|
|0.0|10|8.23|6.24|6.25|0.008|94.1|
|0.4|1|2.28|2.03|2.03|0.001|63.3|
|0.4|5|6.50|4.83|4.85|0.014|88.6|
|0.4|10|8.58|6.33|6.38|0.047|93.9|
|0.8|1|2.34|2.08|2.10|0.025|60.5|
|0.8|5|6.87|5.20|5.39|0.187|87.1|
|0.8|10|9.40|7.00|7.28|0.285|92.9|

Cột theo thứ trừ Meta dương là lợi ích vận hành tối đa trước chi phí hệ thống; số âm nghĩa là Meta tốn hơn baseline. Đây là ước lượng điểm hậu kiểm, không phải mức tiết kiệm VND đã xác nhận bằng thử nghiệm cửa hàng.

p bằng 1, 5, 10 tương ứng lãi mất giả định 100, 500, 1 000 VND mỗi đơn vị. Nếu cửa hàng cần mức đáp ứng tối thiểu 95%, phải kiểm tra mức phục vụ trước khi so tiền; phần trăm trung bình của một ô không bảo đảm từng SKU hoặc từng thời kỳ đạt 95%.

Tệp 18_condition_financial_scenarios.csv chứa toàn bộ chi phí gốc, phép đổi, tồn kho, mức đáp ứng và điểm hòa vốn từng ô. Không dùng trung bình các ô như tỷ trọng thị trường thực khi chưa có trọng số doanh nghiệp.

## C8 Baseline và rủi ro phục vụ trên hai nguồn giữ lại

Trên hai nguồn giữ lại, chỉ có mức phạt p bằng 1. Bảng này dùng thang chuẩn hóa, không đổi Rossmann sang số lượng SKU hay tiền thật.

|Nguồn|Chi phí Meta|Theo thứ|Giảm so với theo thứ %|Đáp ứng Meta %|Theo thứ %|
|---|---|---|---|---|---|
|Beer|0.387492|0.390931|0.88|73.4|73.1|
|Rossmann|0.245602|0.248055|0.99|88.2|89.5|


Chênh lệch Meta với baseline theo thứ chỉ khoảng 0,9% trên Beer và 1,0% trên Rossmann. Hai phép kiểm định nguồn trước đây so Meta với SRDQN; chúng không chứng minh các chênh lệch nhỏ với baseline ở bảng này có ý nghĩa thống kê hoặc kinh tế. Chưa có khoảng tin cậy tài chính cho lợi ích tăng thêm này.

Ở Rossmann, Meta có chi phí p bằng 1 thấp hơn một chút nhưng mức đáp ứng bình quân thấp hơn baseline theo thứ. Điều này phản ánh đánh đổi trong hàm chi phí; nó không cho phép tuyên bố Meta phục vụ tốt hơn. Nếu yêu cầu tối thiểu 95% là bắt buộc, cả hai mức bình quân nguồn đang báo cáo đều chưa đáp ứng yêu cầu ấy.

Nhu cầu Beer kiểm tra cao hơn mốc 2013 khoảng 30–36%; Rossmann có ngày đóng cửa nhưng mô phỏng vẫn cho phép đặt. Để đánh giá tiền thật phải dùng lịch nhận hàng, giờ mở cửa và chính sách ngày nghỉ đúng của cửa hàng. Ngày đóng cửa cần được xử lý như một quy tắc vận hành; gán nhu cầu 0 đơn thuần chưa mô tả hết quyết định tồn kho.

Toàn bộ kết quả nguồn là kiểm tra chính sách cố định từ bộ sinh theo thứ sang doanh số tương lai. Chưa phải một pilot thực với hành động do thuật toán quyết định và quan sát nhu cầu mất bán tương ứng. Cần kiểm chứng lại baseline hiện hành, nhu cầu bị kiểm duyệt, phân phối trôi và giá trị l trước khi duyệt đầu tư.

## C9 Sample quyết định đầu tư và ngưỡng ngân sách

Xét riêng p bằng 10 của sample A, lấy trung bình cân bằng sáu ô mùa vụ và nhiễu. Điều này tạo một kịch bản minh họa; không khẳng định một cửa hàng thật có đúng tổ hợp điều kiện ấy.

|Chính sách|Chi phí vận hành triệu VND mỗi SKU mỗi năm|Đáp ứng bình quân %|
|---|---|---|
|SRDQN-A|6.816|94.26|
|Meta-HQL-P|4.211|96.18|
|Prior weekday|4.272|96.53|


Meta tiết kiệm so với SRDQN khoảng 2.605 triệu VND, nhưng so với baseline theo thứ chỉ 60 894 VND mỗi SKU mỗi năm, trước chi phí hệ thống. Bootstrap ghép cặp theo 30 seed cho trung bình sáu ô p bằng 10 có khoảng 95% xấp xỉ [55 227; 66 795] VND. Khoảng hậu kiểm chỉ phản ánh ngẫu nhiên trong mô phỏng, không bao gồm sai đơn giá, drift hoặc sai mô hình cửa hàng. Lợi ích so với baseline thực dụng là căn cứ đầu tư phù hợp hơn.

Giả định chi phí Meta tăng thêm so với baseline đang có là 50 triệu VND ban đầu và 24 triệu VND mỗi năm; đây là sample ngân sách, không phải báo giá hay số giờ đã đo. Với 100 SKU giống nhau và độc lập, lợi ích vận hành một năm là 6.089 triệu, còn chi phí hệ thống năm đầu là 74 triệu. Tổng chênh lệch năm đầu bất lợi cho Meta khoảng 67.911 triệu VND.

|Số SKU giống nhau|Lợi ích vận hành năm triệu VND|Lợi ích ròng năm đầu|NPV ba năm triệu VND|
|---|---|---|---|
|1|0.061|-73.939|-107.498|
|100|6.089|-67.911|-93.018|
|1000|60.894|-13.106|38.613|


Trong sample này cần khoảng 395 SKU để trang trải riêng OPEX năm và 1216 SKU để trang trải setup cùng OPEX năm đầu. Với ba năm và chiết khấu giả định 12%, ngưỡng NPV bằng 0 khoảng 736 SKU. Chưa tính biến động nhu cầu, thuế, giá trị cuối kỳ hoặc ràng buộc liên SKU; không suy thẳng các ngưỡng này thành quy mô triển khai khuyến nghị.

## C10 Dòng tiền vốn lưu động và việc cần kiểm chứng tiếp

Khoản giải phóng vốn hàng tồn nên được ghi là biến động dòng tiền tại thời điểm giảm vốn; khoản giảm chi phí kho được ghi theo kỳ. Khi lập DCF trên dòng tiền thực, dùng chi phí giữ hàng bằng tiền cùng biến động vốn lưu động; không cộng thêm một khoản chi phí vốn cơ hội đã được phản ánh lại trong cùng phép tính.

$$NPV=-\Delta F-\Delta WC_0+\sum_{y=1}^{Y}\frac{\Delta FCF_y}{(1+r)^y}+\frac{\Delta WC_{\mathrm{recovered}}}{(1+r)^Y}.$$

Delta FCF ở đây là dòng tiền tăng thêm sau OPEX và thuế nếu có. Công thức minh họa C9 chưa đưa vốn lưu động hoặc thuế vào và dùng chiết khấu 12% do nghiên cứu giả định. Nguyên tắc xem xét cả vòng đời, kiểm tra nhạy và ngưỡng đổi quyết định phù hợp với hướng dẫn thẩm định công khai [8]; tỷ lệ chiết khấu doanh nghiệp phải lấy từ chính doanh nghiệp.

Ở sample p bằng 10, chênh lệch tồn cuối kỳ Meta với baseline theo thứ tương ứng đại diện vốn tồn kho giảm khoảng 258 695 VND mỗi SKU khi giá vốn 50 000 và nhu cầu mốc 100. Đây là đại diện từ tồn cuối kỳ, không bao gồm vốn hàng đi đường hoặc trong ngày và không phải khoản tiết kiệm được cộng lại hàng năm.


Để ra quyết định, cần thu thập h và l theo SKU, giá vốn, chi phí đặt nhận, lead time, SLA, giờ nhân sự và hóa đơn máy tính. So baseline hiện hành, baseline theo thứ, bản DQN chỉnh mục tiêu và bản HQL hiệu chỉnh trên cùng SKU, lịch và thông tin. Chạy nhạy theo p thực, lambda, H sai, tự tương quan và drift; thêm ablation phản hồi suy ra. Dùng pilot có giới hạn tiền mất và mức phục vụ để đo chi phí học trực tiếp; chưa bắt đầu pilot thật trong nghiên cứu này.

PDF gốc được tạo trong workspace có hai tệp nhúng, gồm Word OMML và ZIP. Không thể xác nhận nội dung bản nén mà người hướng dẫn nhận khi chưa có bản đó. Để tránh mất tệp nhúng trong quá trình nén hoặc gửi, lần xuất này còn cung cấp gói ZIP riêng có mã, dữ liệu, kết quả và các CSV tài chính. Hash tệp và kiểm tra ZIP hỗ trợ đối chiếu; chúng không thay cho đăng ký nghiên cứu độc lập hoặc một lần tái lập bởi người khác.

Kết luận về lựa chọn hiện tại là chưa đủ bằng chứng để duyệt triển khai Meta-HQL-P chỉ từ tỷ lệ thắng 18 trên 18. CFO cần lợi ích tăng thêm so với phương án đơn giản, khả năng đạt mức phục vụ và tổng chi phí tương ứng cách học. Hai sample cho thấy các đơn giá hoặc quy mô khác nhau có thể thay đổi cả miền áp dụng lẫn khả năng thu hồi đầu tư.


## Nguồn dẫn trong báo cáo

Tài liệu tham khảo và nguồn dữ liệu

[1] Oroojlooyjadid A, Nazari M, Snyder LV, Takáč M. A Deep Q-Network for the Beer Game Deep Reinforcement Learning for Inventory Optimization. Manufacturing & Service Operations Management 24(1), 285-304, 2022; trực tuyến 2021. <https://doi.org/10.1287/msom.2020.0939>.

[2] Gong XY, Simchi-Levi D. Bandits atop Reinforcement Learning Tackling Online Inventory Models with Cyclic Demands. Management Science 70(9), 6139-6157, 2024; trực tuyến 2023. <https://doi.org/10.1287/mnsc.2023.4947>. Mô hình lost-sales và thuật toán HQL, Meta-HQL là cơ sở thích nghi.

[3] Kho mã Beer Game của tác giả. <https://github.com/OptMLGroup/DeepBeerInventory-RL>. Dùng để đối chiếu nguồn và lựa chọn item 5, 34, 46.

[4] Kaggle Store Item Demand Forecasting Challenge. <https://www.kaggle.com/competitions/demand-forecasting-kernels-only/data>. Bản CSV dùng: <https://github.com/nimanov/Demand-Forecasting-using-LightGBM/blob/master/train.csv>, commit 1cd0e8ec5446fb09e421f2ac68cb801738a7bf8c. Đã kiểm tra cấu trúc và lịch; chưa đối chiếu từng byte với bản tải Kaggle độc lập.

[5] Kaggle Rossmann Store Sales. <https://www.kaggle.com/competitions/rossmann-store-sales/data>. Bản sao dùng: <https://github.com/juniorcl/rossman-store-sales/tree/main/databases>.

Mọi kết quả số được tính từ đầu ra thực nghiệm của lần chạy này. Các tuyên bố phương pháp, giả định và giới hạn được tách khỏi kết quả đo.

[6] ACCA. Inventory control. Chi phí giữ và đặt hàng. <https://www.accaglobal.com/middle-east/en/student/exam-support-resources/fundamentals-exams-study-resources/f2/technical-articles/stock-control.html>.

[7] IFRS Foundation. IAS 2 Inventories. Phân biệt giá trị hàng tồn và thời điểm ghi nhận chi phí. <https://www.ifrs.org/issued-standards/list-of-standards/ias-2-inventories/>. Không dùng nguồn này để xác định đơn giá VND hoặc quy định kế toán áp dụng cho cửa hàng giả định.

[8] HM Treasury. The Green Book 2026. Nguyên tắc thẩm định vòng đời, nhạy và ngưỡng thay đổi quyết định. <https://www.gov.uk/government/publications/the-green-book--2/the-green-book-2026>. Tài liệu khu vực công chỉ được dẫn cho nguyên tắc phân tích; sample không dùng mức chiết khấu khu vực công.
