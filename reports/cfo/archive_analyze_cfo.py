"""Post-hoc financial scenarios from existing experiment outputs; no retraining."""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
import os
ROOT=Path(os.environ['GONG_RUN_DIR']).resolve()
O=ROOT/'outputs/cfo_analysis'; O.mkdir(exist_ok=True)
W=ROOT/'work/combined_report_build'; (W/'figures').mkdir(parents=True,exist_ok=True)

S='SRDQN-A'; M='Meta-HQL-P'; B='Prior weekday'
def table(headers,rows):
    return '\n|'+'|'.join(headers)+'|\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('|'+'|'.join(map(str,r))+'|\n' for r in rows)+'\n'
def f(x,n=3):return f'{x:,.{n}f}'.replace(',',' ')

d=pd.read_csv(ROOT/'outputs/condition_study/combined_core.csv')
d=d[d.checkpoint==21000]
assume={'status':'HYPOTHETICAL_NOT_STORE_ACTUALS','mean_units_per_day':100.,'purchase_vnd_per_unit':50000.,
    'selling_price_vnd':55000.,'avoidable_fulfilment_vnd':4000.,'holding_vnd_per_unit_day':100.,
    'lost_contribution_vnd_per_unit':1000.,'p':10.,'periods_per_year':365,
    'meta_incremental_setup_vnd_vs_existing_baseline':50000000.,
    'meta_incremental_annual_running_vnd_vs_existing_baseline':24000000.,'discount_rate_assumed':.12,
    'physical_inventory_cap':400.,'policy_drift_assumed':False,
    'holding_cost_basis':'Sample A assumes cash holding costs, excluding capital opportunity charge; working capital is separate.',
    'note':'365-day and 3-year illustrations assume fixed policies and stable future distribution; no real-world trial.'}
(O/'sample_assumptions.json').write_text(json.dumps(assume,indent=2),encoding='utf-8')
scale=assume['mean_units_per_day']*assume['holding_vnd_per_unit_day']; K=365
def saving_interval(frame,alpha,salt):
    q=frame.pivot_table(index='seed',columns='algorithm',values='frozen_cost',aggfunc='mean')
    z=(q[B]-q[M]).to_numpy();rng=np.random.default_rng(salt)
    vals=z[rng.integers(len(z),size=(20000,len(z)))].mean(1)
    return tuple(float(x*K*scale) for x in np.quantile(vals,[alpha/2,1-alpha/2]))
rows=[]
for (case,a,cv,p),g in d.groupby(['case','a','cv','p']):
    z=g.groupby('algorithm')[['online_cost','frozen_cost','frozen_fill','frozen_inventory']].mean()
    cs,cm,cb=[z.loc[x,'frozen_cost'] for x in [S,M,B]]
    ls,lm=[z.loc[x,'online_cost'] for x in [S,M]]
    lo,hi=saving_interval(g,.05/18,6100+len(rows))
    rows.append(dict(case=case,a=a,cv=cv,p=p,SRDQN_cost=cs,Meta_cost=cm,weekday_cost=cb,
        SRDQN_fill=z.loc[S,'frozen_fill'],Meta_fill=z.loc[M,'frozen_fill'],weekday_fill=z.loc[B,'frozen_fill'],
        SRDQN_end_inventory=z.loc[S,'frozen_inventory'],Meta_end_inventory=z.loc[M,'frozen_inventory'],
        weekday_end_inventory=z.loc[B,'frozen_inventory'],
        assumed_h_vnd=100.,assumed_mu_units_day=100.,assumed_loss_vnd=p*100.,
        SRDQN_annual_vnd=K*scale*cs,Meta_annual_vnd=K*scale*cm,weekday_annual_vnd=K*scale*cb,
        Meta_gross_annual_saving_vs_SRDQN_vnd=K*scale*(cs-cm),
        Meta_gross_annual_saving_vs_weekday_vnd=K*scale*(cb-cm),
        Meta_gross_saving_vs_weekday_CI_low_vnd=lo,Meta_gross_saving_vs_weekday_CI_high_vnd=hi,
        Meta_online21k_excess_vs_SRDQN_vnd=21000*scale*(lm-ls),
        frozen_break_even_after_21k_online_periods=21000*(lm-ls)/(cs-cm)))
t=pd.DataFrame(rows).sort_values(['cv','a','p']);t.to_csv(O/'18_condition_financial_scenarios.csv',index=False)
by=d.groupby(['p','algorithm'])[['online_cost','frozen_cost','frozen_fill','frozen_inventory']].mean()
stats=[]
for p in [1,5,10]:
    z=by.loc[p];cs,cm,cb=[z.loc[x,'frozen_cost'] for x in [S,M,B]]
    lo,hi=saving_interval(d[d.p==p],.05,6210+p)
    stats.append(dict(p=p,SRDQN=cs,Meta=cm,weekday=cb,
        SRDQN_annual=K*scale*cs,Meta_annual=K*scale*cm,weekday_annual=K*scale*cb,
        saving_vs_SRDQN=K*scale*(cs-cm),saving_vs_weekday=K*scale*(cb-cm),
        saving_vs_weekday_pooled95_low=lo,saving_vs_weekday_pooled95_high=hi,
        Meta_fill=z.loc[M,'frozen_fill'],weekday_fill=z.loc[B,'frozen_fill'],
        end_inventory_capital_release_proxy_vs_weekday=50000*100*(z.loc[B,'frozen_inventory']-z.loc[M,'frozen_inventory'])))
ps=pd.DataFrame(stats);ps.to_csv(O/'p_level_financial_scenarios.csv',index=False)
gain=float(ps.loc[ps.p==10,'saving_vs_weekday'].iloc[0]);F=50e6;run=24e6;r=.12
annuity=sum(1/(1+r)**y for y in [1,2,3])
portfolio=[]
for n in [1,100,1000]:
    annual=n*gain-run
    portfolio.append(dict(n_identical_independent_skus=n,gross_annual_saving=n*gain,
        annual_net_before_setup=annual,first_year_net=annual-F,NPV_3_year=-F+annual*annuity,
        simple_payback_year=F/annual if annual>0 else None))
pd.DataFrame(portfolio).to_csv(O/'illustrative_portfolio_tco.csv',index=False)
summary={'scenario_count':len(t),'Meta_lower_than_weekday_point_estimate_cells':int((t.Meta_cost<t.weekday_cost).sum()),
    'annual_p10_saving_per_sku_vs_weekday':gain,'npv_annuity_3yr_12pct':annuity,
    'first_year_n_break_even':(F+run)/gain,'recurring_n_break_even':run/gain,
    'npv3_n_break_even':(F/annuity+run)/gain,
    'sample_B_h':50000*.25/365,'sample_B_p':20000/(50000*.25/365),
    'online_frozen_break_even_min':float(t.frozen_break_even_after_21k_online_periods.min()),
    'online_frozen_break_even_max':float(t.frozen_break_even_after_21k_online_periods.max()),
    'original_21000_training_unchanged':True,'supplementary_pilot_training':True,
    'no_store_invoice_costs':True,'post_hoc_analysis':True}
(O/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')

report=r'''## C1 Đọc phản biện dưới góc độ quyết định đầu tư

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
'''

if (O/'pilot_financial_summary.csv').exists():
    pilot=pd.read_csv(O/'pilot_financial_summary.csv')
    report+=r'''
## C5 Mô phỏng bổ sung ngân sách học trong 365 kỳ

Chạy mới toàn bộ 18 điều kiện với bốn dạng tuần, 30 seed từ 6000 đến 6029 và cùng đường nhu cầu cho hai tác nhân. Ngân sách học là 365 kỳ ngay từ đầu; các mốc 30 và 90 là đoạn đầu của lần học này. Cấu hình chọn từ nghiên cứu trước được giữ nguyên, không tuning lại cho pilot ngắn. Đây là thử nghiệm hậu kiểm trên mô phỏng Gamma, không phải cửa hàng thật.

Baseline theo thứ được ước lượng trước từ 3 500 mẫu riêng, nên có lợi thế lịch sử so với hai tác nhân bắt đầu học từ đầu. Nó đại diện phương án cửa hàng đã có. Muốn so một triển khai có đầy đủ lịch sử, cần thử thêm RL được học offline trước khi ra cửa hàng.

Bảng dùng sample mốc 100 đơn vị mỗi ngày và giữ hàng 100 VND mỗi đơn vị mỗi ngày. Lãi mất là 100, 500, 1 000 VND khi p bằng 1, 5, 10. Số tiền là tổng giữ hàng cộng lãi đóng góp mất trong đúng số kỳ đã ghi, tính bằng triệu VND mỗi SKU; chưa có phí công nghệ. Mỗi dòng gộp cân bằng sáu ô mùa vụ và nhiễu.
'''
    pr=[]
    for h in [30,90,365]:
        for p in [1,5,10]:
            q=pilot[(pilot.horizon==h)&(pilot.p==p)].set_index('algorithm')
            pr.append([h,p,*[f(q.loc[x,'total_cost_vnd_sample']/1e6,3) for x in [S,M,B]],
                f(100*q.loc[M,'fill'],1),f(100*q.loc[S,'fill'],1),f(100*q.loc[B,'fill'],1)])
    report+=table(['Kỳ','p','SRDQN','Meta','Theo thứ','Meta %','SRDQN %','Theo thứ %'],pr)
    report+='Ba cột phần trăm là mức đáp ứng theo lượng. Ở cả chín dòng, Meta có chi phí trung bình cao hơn DQN và baseline. Tại p bằng 10 sau 365 kỳ, baseline có mức đáp ứng bình quân khoảng 96,5%, Meta 99,0% và DQN 91,7%. Nếu mức tối thiểu 95% được yêu cầu, chi phí thấp của DQN chưa đủ để chọn nó; baseline theo thứ cần được kiểm chứng trước khi trả thêm cho Meta. Các mức trung bình chưa phải bảo đảm SLA từng SKU.\n\n'
    report+='Bảng không chứng minh ý nghĩa thống kê từng hàng. Phân rã từng ô, seed và mốc nằm trong results_pilot.csv; tổng 4 320 mô hình của hai tác nhân được học trong 365 kỳ, cùng 2 160 đường baseline. Nếu pilot 30 hoặc 90 kỳ là toàn bộ chân trời biết trước, phải chạy lại với ngân sách ấy.\n'

for cv,chapter,label in [(.25,6,'thấp'),(.75,7,'cao')]:
    report+=f'\n## C{chapter} Chi phí theo điều kiện khi nhiễu {label}\n\n'
    report+='Bảng quy đổi dùng 100 đơn vị nhu cầu mốc mỗi ngày, giữ hàng 100 VND mỗi đơn vị mỗi ngày và giả định 365 ngày vận hành. Chi phí là giữ hàng cộng lãi đóng góp mất, chưa cộng hệ thống. Mỗi hàng là trung bình bốn dạng tuần và 30 seed. Đơn vị tiền trong bảng là triệu VND mỗi SKU mỗi năm.\n'
    rr=[]
    for row in t[t.cv==cv].itertuples():
        rr.append([f(row.a,1),int(row.p),f(row.SRDQN_annual_vnd/1e6,2),f(row.Meta_annual_vnd/1e6,2),
                   f(row.weekday_annual_vnd/1e6,2),f(row.Meta_gross_annual_saving_vs_weekday_vnd/1e6,3),f(100*row.Meta_fill,1)])
    report+=table(['a','p','SRDQN','Meta','Theo thứ','Theo thứ trừ Meta','Đáp ứng Meta %'],rr)
    report+='Cột theo thứ trừ Meta dương là lợi ích vận hành tối đa trước chi phí hệ thống; số âm nghĩa là Meta tốn hơn baseline. Đây là ước lượng điểm hậu kiểm, không phải mức tiết kiệm VND đã xác nhận bằng thử nghiệm cửa hàng.\n\n'
    report+='p bằng 1, 5, 10 tương ứng lãi mất giả định 100, 500, 1 000 VND mỗi đơn vị. Nếu cửa hàng cần mức đáp ứng tối thiểu 95%, phải kiểm tra mức phục vụ trước khi so tiền; phần trăm trung bình của một ô không bảo đảm từng SKU hoặc từng thời kỳ đạt 95%.\n\n'
    report+='Tệp 18_condition_financial_scenarios.csv chứa toàn bộ chi phí gốc, phép đổi, tồn kho, mức đáp ứng và điểm hòa vốn từng ô. Không dùng trung bình các ô như tỷ trọng thị trường thực khi chưa có trọng số doanh nghiệp.\n'

report+=r'''
## C8 Baseline và rủi ro phục vụ trên hai nguồn giữ lại

Trên hai nguồn giữ lại, chỉ có mức phạt p bằng 1. Bảng này dùng thang chuẩn hóa, không đổi Rossmann sang số lượng SKU hay tiền thật.
'''
src=pd.read_csv(ROOT/'outputs/condition_study/combined_sources.csv');src=src[src.checkpoint==21000]
srows=[]
for name,g in src.groupby('case'):
    zz=g.groupby('algorithm')[['frozen_cost','frozen_fill','frozen_inventory']].mean()
    cm,cb=zz.loc[M,'frozen_cost'],zz.loc[B,'frozen_cost']
    srows.append([name.split('_')[0],f(cm,6),f(cb,6),f(100*(cb-cm)/cb,2),
                  f(100*zz.loc[M,'frozen_fill'],1),f(100*zz.loc[B,'frozen_fill'],1)])
report+=table(['Nguồn','Chi phí Meta','Theo thứ','Giảm so với theo thứ %','Đáp ứng Meta %','Theo thứ %'],srows)
report+=r'''
Chênh lệch Meta với baseline theo thứ chỉ khoảng 0,9% trên Beer và 1,0% trên Rossmann. Hai phép kiểm định nguồn trước đây so Meta với SRDQN; chúng không chứng minh các chênh lệch nhỏ với baseline ở bảng này có ý nghĩa thống kê hoặc kinh tế. Chưa có khoảng tin cậy tài chính cho lợi ích tăng thêm này.

Ở Rossmann, Meta có chi phí p bằng 1 thấp hơn một chút nhưng mức đáp ứng bình quân thấp hơn baseline theo thứ. Điều này phản ánh đánh đổi trong hàm chi phí; nó không cho phép tuyên bố Meta phục vụ tốt hơn. Nếu yêu cầu tối thiểu 95% là bắt buộc, cả hai mức bình quân nguồn đang báo cáo đều chưa đáp ứng yêu cầu ấy.

Nhu cầu Beer kiểm tra cao hơn mốc 2013 khoảng 30–36%; Rossmann có ngày đóng cửa nhưng mô phỏng vẫn cho phép đặt. Để đánh giá tiền thật phải dùng lịch nhận hàng, giờ mở cửa và chính sách ngày nghỉ đúng của cửa hàng. Ngày đóng cửa cần được xử lý như một quy tắc vận hành; gán nhu cầu 0 đơn thuần chưa mô tả hết quyết định tồn kho.

Toàn bộ kết quả nguồn là kiểm tra chính sách cố định từ bộ sinh theo thứ sang doanh số tương lai. Chưa phải một pilot thực với hành động do thuật toán quyết định và quan sát nhu cầu mất bán tương ứng. Cần kiểm chứng lại baseline hiện hành, nhu cầu bị kiểm duyệt, phân phối trôi và giá trị l trước khi duyệt đầu tư.

## C9 Sample quyết định đầu tư và ngưỡng ngân sách

Xét riêng p bằng 10 của sample A, lấy trung bình cân bằng sáu ô mùa vụ và nhiễu. Điều này tạo một kịch bản minh họa; không khẳng định một cửa hàng thật có đúng tổ hợp điều kiện ấy.
'''
z=ps[ps.p==10].iloc[0]
report+=table(['Chính sách','Chi phí vận hành triệu VND mỗi SKU mỗi năm','Đáp ứng bình quân %'],[
    ['SRDQN-A',f(z.SRDQN_annual/1e6,3),f(100*by.loc[(10,S),'frozen_fill'],2)],
    ['Meta-HQL-P',f(z.Meta_annual/1e6,3),f(100*z.Meta_fill,2)],
    ['Prior weekday',f(z.weekday_annual/1e6,3),f(100*z.weekday_fill,2)]])
report+=f'\nMeta tiết kiệm so với SRDQN khoảng {f(z.saving_vs_SRDQN/1e6,3)} triệu VND, nhưng so với baseline theo thứ chỉ {f(gain,0)} VND mỗi SKU mỗi năm, trước chi phí hệ thống. Bootstrap ghép cặp theo 30 seed cho trung bình sáu ô p bằng 10 có khoảng 95% xấp xỉ [{f(z.saving_vs_weekday_pooled95_low,0)}; {f(z.saving_vs_weekday_pooled95_high,0)}] VND. Khoảng hậu kiểm chỉ phản ánh ngẫu nhiên trong mô phỏng, không bao gồm sai đơn giá, drift hoặc sai mô hình cửa hàng. Lợi ích so với baseline thực dụng là căn cứ đầu tư phù hợp hơn.\n\n'
report+=f'Giả định chi phí Meta tăng thêm so với baseline đang có là 50 triệu VND ban đầu và 24 triệu VND mỗi năm; đây là sample ngân sách, không phải báo giá hay số giờ đã đo. Với 100 SKU giống nhau và độc lập, lợi ích vận hành một năm là {f(100*gain/1e6,3)} triệu, còn chi phí hệ thống năm đầu là 74 triệu. Tổng chênh lệch năm đầu bất lợi cho Meta khoảng {f((74e6-100*gain)/1e6,3)} triệu VND.\n'
report+=table(['Số SKU giống nhau','Lợi ích vận hành năm triệu VND','Lợi ích ròng năm đầu','NPV ba năm triệu VND'],[
    [int(v['n_identical_independent_skus']),f(v['gross_annual_saving']/1e6,3),f(v['first_year_net']/1e6,3),f(v['NPV_3_year']/1e6,3)] for v in portfolio])
report+=f'\nTrong sample này cần khoảng {int(np.ceil(summary["recurring_n_break_even"]))} SKU để trang trải riêng OPEX năm và {int(np.ceil(summary["first_year_n_break_even"]))} SKU để trang trải setup cùng OPEX năm đầu. Với ba năm và chiết khấu giả định 12%, ngưỡng NPV bằng 0 khoảng {int(np.ceil(summary["npv3_n_break_even"]))} SKU. Chưa tính biến động nhu cầu, thuế, giá trị cuối kỳ hoặc ràng buộc liên SKU; không suy thẳng các ngưỡng này thành quy mô triển khai khuyến nghị.\n'

report+=r'''
## C10 Dòng tiền vốn lưu động và việc cần kiểm chứng tiếp

Khoản giải phóng vốn hàng tồn nên được ghi là biến động dòng tiền tại thời điểm giảm vốn; khoản giảm chi phí kho được ghi theo kỳ. Khi lập DCF trên dòng tiền thực, dùng chi phí giữ hàng bằng tiền cùng biến động vốn lưu động; không cộng thêm một khoản chi phí vốn cơ hội đã được phản ánh lại trong cùng phép tính.

$$NPV=-\Delta F-\Delta WC_0+\sum_{y=1}^{Y}\frac{\Delta FCF_y}{(1+r)^y}+\frac{\Delta WC_{\mathrm{recovered}}}{(1+r)^Y}.$$

Delta FCF ở đây là dòng tiền tăng thêm sau OPEX và thuế nếu có. Công thức minh họa C9 chưa đưa vốn lưu động hoặc thuế vào và dùng chiết khấu 12% do nghiên cứu giả định. Nguyên tắc xem xét cả vòng đời, kiểm tra nhạy và ngưỡng đổi quyết định phù hợp với hướng dẫn thẩm định công khai [8]; tỷ lệ chiết khấu doanh nghiệp phải lấy từ chính doanh nghiệp.
'''
report+=f'\nỞ sample p bằng 10, chênh lệch tồn cuối kỳ Meta với baseline theo thứ tương ứng đại diện vốn tồn kho giảm khoảng {f(z.end_inventory_capital_release_proxy_vs_weekday,0)} VND mỗi SKU khi giá vốn 50 000 và nhu cầu mốc 100. Đây là đại diện từ tồn cuối kỳ, không bao gồm vốn hàng đi đường hoặc trong ngày và không phải khoản tiết kiệm được cộng lại hàng năm.\n\n'
report+=r'''
Để ra quyết định, cần thu thập h và l theo SKU, giá vốn, chi phí đặt nhận, lead time, SLA, giờ nhân sự và hóa đơn máy tính. So baseline hiện hành, baseline theo thứ, bản DQN chỉnh mục tiêu và bản HQL hiệu chỉnh trên cùng SKU, lịch và thông tin. Chạy nhạy theo p thực, lambda, H sai, tự tương quan và drift; thêm ablation phản hồi suy ra. Dùng pilot có giới hạn tiền mất và mức phục vụ để đo chi phí học trực tiếp; chưa bắt đầu pilot thật trong nghiên cứu này.

PDF gốc được tạo trong workspace có hai tệp nhúng, gồm Word OMML và ZIP. Không thể xác nhận nội dung bản nén mà người hướng dẫn nhận khi chưa có bản đó. Để tránh mất tệp nhúng trong quá trình nén hoặc gửi, lần xuất này còn cung cấp gói ZIP riêng có mã, dữ liệu, kết quả và các CSV tài chính. Hash tệp và kiểm tra ZIP hỗ trợ đối chiếu; chúng không thay cho đăng ký nghiên cứu độc lập hoặc một lần tái lập bởi người khác.

Kết luận về lựa chọn hiện tại là chưa đủ bằng chứng để duyệt triển khai Meta-HQL-P chỉ từ tỷ lệ thắng 18 trên 18. CFO cần lợi ích tăng thêm so với phương án đơn giản, khả năng đạt mức phục vụ và tổng chi phí tương ứng cách học. Hai sample cho thấy các đơn giá hoặc quy mô khác nhau có thể thay đổi cả miền áp dụng lẫn khả năng thu hồi đầu tư.
'''
(W/'cfo_addition.md').write_text(report,encoding='utf-8')
manifest={f.name:{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
    for f in O.iterdir() if f.is_file() and f.name!='manifest_sha256.json'}
(O/'manifest_sha256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
