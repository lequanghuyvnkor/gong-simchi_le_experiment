"""Vietnamese day-by-day teaching interface for Gong & Simchi-Levi's setting."""

from html import escape
from pathlib import Path
import sys

import altair as alt
import pandas as pd
import streamlit as st

# Also works when launched from the parent research directory or by AppTest.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
from model import CYCLE_LENGTH, Config, history_rows
from experiment import PairedRun
from hql_ui import render_comparison, render_hql
from meta_ui import render_meta


st.set_page_config(page_title="Tồn kho · Học qua mô phỏng", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

STYLE = """
<style>
.block-container {max-width:1180px; padding-top:4.4rem; padding-bottom:3rem;}
[data-testid="stAppViewContainer"] {background:#f7fafc; color:#17324d;}
[data-testid="stHeader"] {background:rgba(247,250,252,.96);}
[data-testid="stSidebar"] {background:#edf3f7;}
h1,h2,h3 {color:#17324d; letter-spacing:-.025em;}
h1 {font-size:2.5rem !important; line-height:1.18 !important;}
p,li,label {font-size:1rem;}
.eyebrow {font-size:.79rem; font-weight:700; letter-spacing:.14em; color:#52718b; margin-bottom:.7rem;}
.intro {color:#52718b; font-size:1.06rem; max-width:760px; margin:.6rem 0 1.2rem;}
.mode-label {display:inline-block; color:#0f766e; background:#e4f3ee; border-radius:8px; padding:.38rem .65rem; font-size:.86rem; font-weight:600;}
.cycle-strip {display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.6rem; margin:1.2rem 0 .6rem;}
.cycle-day {padding:.75rem 1rem; border-radius:10px; border:1px solid #d7e2ea; background:#fff;}
.cycle-day.active {border-color:#0f766e; background:#e4f3ee;}
.cycle-day strong {display:block; font-size:1rem;}
.cycle-day span {display:block; color:#52718b; font-size:.85rem; margin-top:.15rem;}
.stock-grid {display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; margin:.8rem 0;}
.stock-cell {background:#fff; border:1px solid #d7e2ea; padding:.8rem 1rem; border-radius:10px;}
.stock-label {font-size:.86rem; color:#52718b;}
.stock-value {font-size:1.8rem; font-weight:700; color:#17324d; line-height:1.3;}
.stock-note {color:#52718b; font-size:.81rem;}
.equation {padding:.9rem 1rem; margin:.8rem 0; background:#e4f3ee; color:#14594f; border-radius:9px; font-size:1rem;}
.empty-state {padding:1.2rem 0; color:#52718b; line-height:1.7;}
[data-testid="stMetricValue"] {font-size:1.6rem;}
[data-testid="stTabs"] {margin-top:1rem;}
@media(max-width:700px) {
 .block-container {padding-top:4rem; padding-left:1rem; padding-right:1rem;}
 h1 {font-size:1.9rem !important;}
 .cycle-day {padding:.6rem;}
 .cycle-day span {font-size:.8rem;}
}
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)

with st.sidebar:
    st.caption("Mở mô hình trong phiên riêng")
    st.link_button("HQL · lost-sales", "?model=hql", use_container_width=True)
    st.link_button("Meta-HQL · giữ tồn", "?model=meta", use_container_width=True)
    st.link_button("FQL · 2 sản phẩm, giao 1 ngày", "?model=fql", use_container_width=True)

if st.query_params.get("model") == "fql":
    from fql_ui import render_fql_app
    render_fql_app()
    st.stop()


def number(value: float) -> str:
    return f"{value:,.2f}".rstrip("0").rstrip(".").replace(",", " ")


def reset(config: Config | None = None, confidence_scale: float | None = None, bandit_c2: float | None = None) -> None:
    config = config or st.session_state.config
    confidence_scale = confidence_scale if confidence_scale is not None else st.session_state.get("confidence_scale", 8.0)
    bandit_c2 = bandit_c2 if bandit_c2 is not None else st.session_state.get("bandit_c2", 1.0)
    run = PairedRun(config, confidence_scale, bandit_c2)
    st.session_state.config = config
    st.session_state.confidence_scale = confidence_scale
    st.session_state.bandit_c2 = bandit_c2
    st.session_state.experiment = run
    st.session_state.history = run.human
    st.session_state.inventory = config.initial_inventory
    st.session_state.target_stock = min(config.capacity, max(config.initial_inventory, 5))
    st.session_state.pop("step_error", None)
    for key in ("q_cursor", "q_episode_select", "hql_decision_day", "meta_cursor", "meta_day_select", "meta_q_arm"):
        st.session_state.pop(key, None)


def advance() -> None:
    config = st.session_state.config
    day = len(st.session_state.history) + 1
    opening = st.session_state.inventory
    target = st.session_state.target_stock
    if day > config.total_days:
        return
    if not opening <= target <= config.capacity:
        st.session_state.step_error = "Hãy chọn yₜ từ tồn đầu ngày xₜ đến mức tối đa M."
        return
    run = st.session_state.experiment
    result = run.step(target)
    st.session_state.inventory = result.next_opening
    if config.discard_at_cycle_end:
        st.session_state.hql_decision_day = day
        if result.phase == CYCLE_LENGTH:
            st.session_state.q_episode_select = result.cycle
            st.session_state.q_cursor = 0
    else:
        st.session_state.meta_day_select = day
        st.session_state.meta_cursor = 1
    st.session_state.pop("step_error", None)


if "config" not in st.session_state:
    reset(Config(discard_at_cycle_end=False, cycles=12) if st.query_params.get("model") == "meta" else Config())
# Preserve any manual run already open when this feature is hot-reloaded.
elif "experiment" not in st.session_state or getattr(st.session_state.experiment, "version", 0) < 3:
    upgraded = PairedRun(st.session_state.config, st.session_state.get("confidence_scale", 8.0), st.session_state.get("bandit_c2", 1.0))
    for previous in st.session_state.history:
        replayed = upgraded.step(previous.order_up_to)
        if replayed.demand != previous.demand:
            raise RuntimeError("Không thể khôi phục cùng chuỗi nhu cầu của phiên đang mở.")
    st.session_state.experiment = upgraded
    st.session_state.history = upgraded.human
    st.session_state.confidence_scale = st.session_state.get("confidence_scale", 8.0)
    st.session_state.bandit_c2 = st.session_state.get("bandit_c2", 1.0)
st.session_state.setdefault("researcher_view", False)


def settings() -> None:
    current = st.session_state.config
    with st.sidebar:
        st.header("Thiết lập thí nghiệm")
        st.caption("Một sản phẩm · hàng đến ngay · mỗi chu kỳ 3 ngày.")
        with st.form("settings_form"):
            mode = st.selectbox(
                "Tồn dư sau ngày thứ 3",
                ["Loại bỏ hết (episodic)", "Giữ sang chu kỳ sau (nondiscarding)"],
                index=0 if current.discard_at_cycle_end else 1,
                key="cfg_mode",
            )
            cycles = st.number_input("Số chu kỳ muốn thử", 1, 60, current.cycles, key="cfg_cycles")
            initial = st.number_input("Tồn kho ban đầu x₁", 0, 50, current.initial_inventory, key="cfg_initial")
            capacity = st.number_input("Mức tồn kho tối đa M", 1, 50, current.capacity, key="cfg_capacity")
            holding = st.number_input("Phí lưu kho o · mỗi sản phẩm/ngày", 0.1, 1000.0, current.holding_rate, step=0.5, key="cfg_holding")
            penalty = st.number_input("Mức phạt p · mỗi đơn vị cầu bị mất", 0.1, 1000.0, current.penalty_rate, step=0.5, key="cfg_penalty")
            confidence = st.selectbox(
                "Cận tin cậy của HQL",
                ["Theo bài báo · hệ số 8", "Minh họa thu hẹp nhanh · hệ số 0.001"],
                index=0 if st.session_state.confidence_scale == 8 else 1, key="cfg_confidence",
                help="Mặc định theo Algorithm 1. Cận thu hẹp nhanh chỉ minh họa cơ chế loại hành động, không có đảm bảo lý thuyết của cận gốc.",
            )
            with st.expander("Bandit Meta-HQL · dùng khi giữ tồn"):
                bandit_setting = st.selectbox("Cận bandit Meta-HQL", ["Công thức CB₂ · C₂ = 1", "Minh họa thu hẹp nhanh · C₂ = 0.001"], index=0 if st.session_state.bandit_c2 == 1 else 1, key="cfg_bandit")
                st.caption("C₂ trong bài là một hằng số chưa ấn định. Giá trị 1 là lựa chọn của bản học; cận nhỏ dùng để quan sát loại nhánh sớm.")
            with st.expander("Nhu cầu do người nghiên cứu thiết lập"):
                st.caption("Mỗi ngày dùng phân phối Poisson. Trung bình lặp lại theo chu kỳ; lượng cầu thực tế từng ngày vẫn ngẫu nhiên độc lập. Cửa hàng không dùng các tham số này để chọn đơn hàng.")
                means = tuple(
                    st.number_input(f"Nhu cầu trung bình · ngày {phase + 1}", 0.0, 30.0, current.demand_means[phase], step=1.0, key=f"cfg_mean_{phase}")
                    for phase in range(CYCLE_LENGTH)
                )
                seed = st.number_input("Mã tình huống ngẫu nhiên (seed)", 0, 2**32 - 1, current.seed, key="cfg_seed")
                st.caption("Giữ cùng mã để thử quyết định khác trên cùng chuỗi nhu cầu. Đổi mã để có tình huống mới.")
            submitted = st.form_submit_button("Áp dụng và bắt đầu lại", use_container_width=True)
        if submitted:
            try:
                updated = Config(
                    capacity=int(capacity), initial_inventory=int(initial),
                    holding_rate=float(holding), penalty_rate=float(penalty),
                    demand_means=means, seed=int(seed), cycles=int(cycles),
                    discard_at_cycle_end=mode.startswith("Loại"),
                )
                reset(updated, 8.0 if confidence.startswith("Theo") else .001, 1.0 if bandit_setting.startswith("Công") else .001)
                st.success("Đã áp dụng thiết lập và bắt đầu từ ngày 1.")
            except ValueError as error:
                st.error(str(error))
        st.button("Chơi lại cùng tình huống", key="replay", on_click=reset, use_container_width=True)
        st.caption("Các mức phí dùng đơn vị chi phí giả định. Thiết lập mới chỉ có hiệu lực khi bấm Áp dụng.")


settings()
config = st.session_state.config
history = st.session_state.history
run = st.session_state.experiment
done = len(history) >= config.total_days
next_day = len(history) + 1
phase = (next_day - 1) % CYCLE_LENGTH + 1
cycle = (next_day - 1) // CYCLE_LENGTH + 1

st.markdown('<div class="eyebrow">GONG & SIMCHI-LEVI · HỌC QUA THỬ NGHIỆM</div>', unsafe_allow_html=True)
st.title("Một cửa hàng. Từng quyết định.")
st.markdown('<p class="intro">Bạn quyết định bổ sung hàng. Khách đến mua. Quan sát điều xảy ra để hiểu mô hình lost-sales — thiếu hàng thì mất cơ hội bán, khách không chờ giao sau.</p>', unsafe_allow_html=True)
mode_name = "Episodic · loại bỏ tồn dư cuối chu kỳ" if config.discard_at_cycle_end else "Nondiscarding · giữ tồn qua chu kỳ"
st.markdown(f'<span class="mode-label">1 sản phẩm · Chu kỳ 3 ngày · {mode_name}</span>', unsafe_allow_html=True)
st.caption("Mở thanh bên ở góc trên trái để thay đổi thiết lập thí nghiệm.")
researcher = st.toggle("Xem góc nhìn người nghiên cứu", key="researcher_view", help="Hiện nhu cầu thật và chi phí mất doanh số của những ngày đã chạy. Không hiện nhu cầu tương lai.")
if researcher:
    st.caption("Đang mở lời giải: nhu cầu thật và chi phí bị che khuất chỉ được hiện cho những ngày đã chạy.")
else:
    st.caption("Góc nhìn cửa hàng: chỉ thấy lượng bán và hàng còn lại. Khi bán hết, nhu cầu vượt tồn kho bị che khuất.")

play_tab, history_tab, hql_tab, comparison_tab, model_tab = st.tabs(["Chạy từng ngày", "Lịch sử & chi phí", f"{run.algorithm_name} từng bước", "So sánh", "Hiểu mô hình"])


def stock_cells(items: list[tuple[str, int, str]]) -> None:
    cells = "".join(
        f'<div class="stock-cell"><div class="stock-label">{escape(label)}</div><div class="stock-value">{value}</div><div class="stock-note">{escape(note)}</div></div>'
        for label, value, note in items
    )
    st.markdown(f'<div class="stock-grid">{cells}</div>', unsafe_allow_html=True)


with play_tab:
    display_cycle = config.cycles if done else cycle
    st.subheader(f"Chu kỳ {display_cycle} / {config.cycles}")
    strip = []
    for index in range(1, CYCLE_LENGTH + 1):
        active = not done and index == phase
        status = "Đã chạy" if done or index < phase else ("Đang chuẩn bị" if active else "Chưa chạy")
        strip.append(f'<div class="cycle-day{" active" if active else ""}"><strong>Ngày {index}</strong><span>{status}</span></div>')
    st.markdown(f'<div class="cycle-strip" aria-label="Tiến độ chu kỳ 3 ngày">{"".join(strip)}</div>', unsafe_allow_html=True)
    st.progress(len(history) / config.total_days, text=f"Đã chạy {len(history)} / {config.total_days} ngày")
    if done:
        st.success("Bạn đã hoàn tất thí nghiệm. Mở Lịch sử & chi phí để xem lại, hoặc Chơi lại cùng tình huống để thử cách đặt hàng khác.")

    decision_col, outcome_col = st.columns([1, 1.3], gap="large")
    with decision_col:
        st.subheader("Đã hoàn tất các quyết định" if done else f"Chuẩn bị ngày {next_day}")
        st.metric("Tồn kho đang có · xₜ", f"{st.session_state.inventory} sản phẩm")
        target = st.number_input(
            "Bạn muốn có bao nhiêu hàng sau bổ sung? · yₜ",
            min_value=0, max_value=config.capacity, step=1,
            key="target_stock", disabled=done,
            help="Đây là tổng hàng sẵn để bán sau khi bổ sung. Đơn đặt thêm là qₜ = yₜ − xₜ và đến ngay trong ngày.",
        )
        opening = st.session_state.inventory
        valid = target >= opening
        if valid:
            st.markdown(f'<div class="equation">Đang có <b>{opening}</b> + đặt thêm <b>{target - opening}</b> = sẵn bán <b>{target}</b> sản phẩm.</div>', unsafe_allow_html=True)
            st.caption(f"Quyết định hợp lệ: {opening} ≤ {target} ≤ {config.capacity}. Hàng đặt thêm đến ngay, trước khi khách mua.")
        else:
            st.error(f"Bạn đang có {opening} sản phẩm, nên yₜ phải từ {opening} trở lên. Giảm xuống {target} sẽ tương đương lấy bớt hàng ra trước khi bán; mô hình chỉ cho phép bổ sung.")
        st.button(
            "Đã chạy đủ số ngày" if done else f"Chạy ngày {next_day}",
            type="primary", key="advance_day", disabled=done or not valid,
            on_click=advance, use_container_width=True,
        )
        st.caption("Chỉ nút Chạy ngày mới chốt quyết định và sinh nhu cầu cho ngày đó. Đổi số hoặc mở phần giải thích không chạy thêm ngày.")
        if run.agent:
            st.caption(f"{run.algorithm_name} tự đặt hàng tại một cửa hàng riêng trên cùng nhu cầu mỗi ngày. Mở {run.algorithm_name} từng bước để xem cách học, hoặc So sánh để đối chiếu.")
        if "step_error" in st.session_state:
            st.error(st.session_state.step_error)
        with st.expander("Trong ngày, việc gì xảy ra trước?"):
            st.markdown("1. Bạn thấy tồn đầu ngày **xₜ**.\n2. Bạn chọn mức **yₜ**, đặt thêm **qₜ = yₜ − xₜ**.\n3. Hàng đến ngay, rồi nhu cầu **Dₜ** mới phát sinh.\n4. Bán **Sₜ**, đếm hàng còn **Iₜ** và ghi chi phí.\n5. Cuối ngày thứ 3, xử lý tồn dư theo chế độ đã chọn.")

    with outcome_col:
        if not history:
            st.subheader("Mở cửa ngày đầu tiên")
            suggested = min(config.capacity, max(config.initial_inventory, 5))
            st.markdown(f'<div class="empty-state">Thử chọn <b>yₜ = {suggested}</b>: tồn đầu ngày là <b>{config.initial_inventory}</b>, nên bạn đặt thêm <b>{suggested - config.initial_inventory}</b> sản phẩm để đạt mức đó.<br><br>Sau khi bấm <b>Chạy ngày 1</b>, phần này sẽ giải thích từng dòng hàng và chi phí bằng số cụ thể.</div>', unsafe_allow_html=True)
            st.info(f"Hiện tại: lưu kho {number(config.holding_rate)} / sản phẩm dư; phạt {number(config.penalty_rate)} / đơn vị nhu cầu bị mất.")
        else:
            last = history[-1]
            st.subheader(f"Kết quả ngày {last.day}")
            st.caption(f"Vừa đóng ngày {last.phase} của chu kỳ {last.cycle}.")
            stock_cells([
                ("Tồn đầu ngày · xₜ", last.opening, "hàng đã có sẵn"),
                ("Đặt thêm · qₜ", last.ordered, f"nâng tồn lên yₜ = {last.order_up_to}"),
                ("Bán được · Sₜ", last.sales, "cửa hàng quan sát được"),
                ("Còn sau bán · Iₜ", last.remaining, "trước khi xử lý cuối chu kỳ"),
            ])
            if last.censored:
                st.warning(f"Đã bán hết {last.sales} sản phẩm. Cửa hàng chỉ kết luận Dₜ ≥ {last.sales}; chưa biết còn bao nhiêu nhu cầu không phục vụ được.")
            else:
                st.success(f"Còn hàng sau khi bán, nên biết nhu cầu Dₜ = {last.sales}. Toàn bộ nhu cầu hôm nay đã được phục vụ.")

            st.markdown("**Chi phí của ngày vừa chạy**")
            st.write(f"Lưu kho: {number(last.holding_rate)} × {last.remaining} sản phẩm dư = **{number(last.holding_cost)}**.")
            if researcher or not last.censored:
                st.write(f"Mất doanh số: {number(last.penalty_rate)} × {last.lost} đơn vị cầu mất = **{number(last.penalty_cost)}**.")
                st.write(f"Tổng chi phí thật: {number(last.holding_cost)} + {number(last.penalty_cost)} = **{number(last.total_cost)}**.")
                if researcher:
                    st.info(f"Lời giải ngày {last.day}: nhu cầu thật {last.demand}, bán {last.sales}, mất {last.lost} đơn vị nhu cầu.")
            else:
                st.write("Mất doanh số: **chưa xác định được từ dữ liệu cửa hàng**.")
                st.caption("Vì phần nhu cầu mất bị che khuất, tổng chi phí thật của ngày này cũng chưa xác định được.")

            if last.phase == CYCLE_LENGTH:
                if config.discard_at_cycle_end:
                    st.info(f"Đã kết thúc chu kỳ: loại bỏ {last.discarded} sản phẩm dư. Tồn đầu ngày kế tiếp = 0. Chi phí lưu kho ở trên được tính trước bước loại bỏ.")
                else:
                    st.info(f"Đã kết thúc chu kỳ: giữ {last.next_opening} sản phẩm sang ngày đầu chu kỳ kế tiếp.")
            else:
                st.caption(f"Chuyển {last.next_opening} sản phẩm còn lại sang đầu ngày {last.day + 1}.")


def chart(data: pd.DataFrame, fields: list[str], title: str, cost: bool = False) -> None:
    long = data[["Ngày", *fields]].melt("Ngày", var_name="Đại lượng", value_name="Giá trị")
    base = alt.Chart(long).encode(
        x=alt.X("Ngày:O", title="Ngày đã chạy", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Giá trị:Q", title="Đơn vị chi phí" if cost else "Sản phẩm", scale=alt.Scale(zero=True)),
        color=alt.Color("Đại lượng:N", title=None, scale=alt.Scale(domain=fields, range=["#0f766e", "#4f79a5", "#b46d18", "#8753a1"][:len(fields)]), legend=alt.Legend(orient="bottom", labelLimit=300)),
        tooltip=[alt.Tooltip("Ngày:O"), alt.Tooltip("Đại lượng:N"), alt.Tooltip("Giá trị:Q", format=".2f" if cost else ".0f")],
    )
    visual = base.mark_bar() if cost else base.mark_line(point=True)
    st.altair_chart(visual.properties(height=260, title=title).configure_view(stroke=None), use_container_width=True)


with history_tab:
    st.subheader("Nhìn lại các quyết định")
    if not history:
        st.info("Chạy ngày đầu tiên để có lịch sử, biểu đồ và bảng tải về.")
    else:
        rows = history_rows(history, researcher)
        data = pd.DataFrame(rows)
        metric_a, metric_b, metric_c = st.columns(3)
        metric_a.metric("Đã bán", f"{sum(r.sales for r in history)} sản phẩm")
        metric_b.metric("Chi phí lưu kho đã biết", number(sum(r.holding_cost for r in history)))
        if researcher:
            metric_c.metric("Tổng chi phí thật · người nghiên cứu", number(sum(r.total_cost for r in history)))
        else:
            metric_c.metric("Số ngày nhu cầu bị che khuất", str(sum(r.censored for r in history)))
        stock_fields = ["Sau bổ sung y", "Bán được S", "Tồn sau bán I"]
        if researcher:
            stock_fields.append("Nhu cầu thật D")
        chart(data, stock_fields, "Hàng sẵn bán, lượng bán và tồn dư")
        cost_fields = ["Chi phí lưu kho", "Chi phí mất doanh số"] if researcher else ["Chi phí lưu kho"]
        chart(data, cost_fields, "Chi phí từng ngày", cost=True)
        if not researcher:
            st.caption("Biểu đồ chi phí ở góc nhìn cửa hàng chỉ hiển thị phí lưu kho. Bật góc nhìn người nghiên cứu để xem phần chi phí mất doanh số bị che khuất.")
        st.dataframe(data, hide_index=True, use_container_width=True)
        st.download_button(
            "Tải lịch sử CSV · góc nhìn hiện tại", data.to_csv(index=False).encode("utf-8-sig"),
            file_name="lost_sales_nguoi_nghien_cuu.csv" if researcher else "lost_sales_cua_hang.csv",
            mime="text/csv", key="download_history",
        )
        st.caption("CSV chỉ gồm những ngày đã chạy và các cột được phép xem ở góc nhìn đang chọn. Chơi lại cùng tình huống giữ nguyên chuỗi nhu cầu để bạn thử quyết định khác.")


with hql_tab:
    if config.discard_at_cycle_end:
        render_hql(run)
    else:
        render_meta(run)

with comparison_tab:
    render_comparison(run, researcher)

with model_tab:
    st.subheader("Dịch mô hình sang ngôn ngữ kinh doanh")
    glossary = [
        ("t", "Ngày đang vận hành", "Đếm liên tục qua các chu kỳ: 1, 2, 3, 4…"),
        ("h ∈ {1,2,3}; H = 3", "Vị trí trong chu kỳ; độ dài chu kỳ", "Ngày thứ 1 của mỗi chu kỳ dùng cùng một phân phối nhu cầu."),
        ("xₜ", "Hàng có sẵn đầu ngày", "Bạn quan sát được trước khi đặt hàng."),
        ("yₜ", "Tổng hàng sẵn bán sau bổ sung", "Bạn quyết định, trước khi biết nhu cầu hôm nay."),
        ("qₜ = yₜ − xₜ", "Số sản phẩm đặt thêm", "Đến ngay trong ngày; lead time bằng 0."),
        ("Dₜ", "Tổng nhu cầu thật của khách", "Ngẫu nhiên; khi bán hết hàng, cửa hàng chỉ biết một cận dưới."),
        ("Sₜ = min(yₜ,Dₜ)", "Lượng bán thực tế", "Cửa hàng luôn quan sát được."),
        ("Iₜ = max(yₜ−Dₜ,0)", "Hàng còn sau bán", "Cũng bằng yₜ − Sₜ; cửa hàng đếm được."),
        ("Lₜ = max(Dₜ−yₜ,0)", "Nhu cầu bị mất", "Khách không mua được sẽ rời đi; không trở thành đơn nợ ngày sau."),
        ("o; p", "Phí lưu kho; mức phạt mất doanh số", "Các mức phí đã biết, áp dụng cho từng sản phẩm dư hoặc từng đơn vị cầu mất."),
        ("M", "Mức tồn kho sau bổ sung tối đa", "Giới hạn mức yₜ trong thí nghiệm."),
    ]
    st.dataframe(pd.DataFrame(glossary, columns=["Ký hiệu", "Nghĩa kinh doanh", "Cách hiểu"]), hide_index=True, use_container_width=True)
    st.markdown("**Ràng buộc và chuyển tồn kho**")
    st.latex(r"0 \le x_t \le y_t \le M,\qquad q_t=y_t-x_t\ge0")
    st.write("Bạn chỉ bổ sung hàng trước khi bán. Tồn kho và lượng đặt thêm trong bản học này là số nguyên sản phẩm.")
    st.write("Trong chu kỳ, tồn đầu ngày tiếp theo bằng hàng còn sau bán: xₜ₊₁ = Iₜ. Ở cuối ngày thứ 3, chế độ episodic loại bỏ phần dư và đưa tồn đầu ngày tiếp theo về 0; chế độ nondiscarding giữ nguyên Iₜ.")
    st.markdown("**Chi phí: cân bằng giữa dư hàng và thiếu hàng**")
    st.latex(r"C_t = o I_t + p L_t = o(y_t-D_t)^+ + p(D_t-y_t)^+")
    st.write(f"Trong thiết lập đang chạy, mỗi sản phẩm dư tốn {number(config.holding_rate)} đơn vị chi phí; mỗi đơn vị cầu bị mất bị phạt {number(config.penalty_rate)}. Ký hiệu (z)⁺ nghĩa là lấy số lớn hơn giữa z và 0.")
    st.write("Mức phạt thể hiện tổn thất do thiếu hàng trong mô hình. Khi không biết lượng cầu bị mất, cửa hàng cũng không quan sát chính xác khoản chi phí này.")
    with st.expander("Nâng cao: chi phí giả định quan sát được"):
        st.latex(r"\widetilde C_t = o I_t - p S_t,\qquad C_t-\widetilde C_t=pD_t")
        st.write("Chi phí giả định tính được từ hàng dư và lượng bán. Nó có thể âm và là đại lượng phục vụ học thuật toán, không phải lợi nhuận kinh doanh.")
        if history:
            last = history[-1]
            st.write(f"Ngày {last.day}: {number(last.holding_rate)} × {last.remaining} − {number(last.penalty_rate)} × {last.sales} = **{number(last.pseudo_cost)}**.")
        st.write("Với cùng nhu cầu và cùng mức phí, phần pDₜ không phụ thuộc quyết định đặt hàng. Vì vậy, khi so sánh hai chính sách trên cùng chuỗi nhu cầu, chênh lệch chi phí thật bằng chênh lệch chi phí giả định.")
    with st.expander("Các giả định của bản mô phỏng"):
        st.markdown("- Bạn tự đặt hàng; HQL hoặc Meta-HQL chạy ở một cửa hàng riêng với cùng nhu cầu và điều kiện ban đầu. Bộ học chỉ nhận lượng bán riêng.\n- Một sản phẩm, hàng đặt đến ngay, chỉ bổ sung hàng, không ghi nợ đơn thiếu.\n- H = 3; nhu cầu Poisson độc lập với trung bình lặp theo 3 vị trí trong chu kỳ. Poisson là lựa chọn minh họa của bản mô phỏng; bài báo cho phép phân phối chu kỳ tổng quát hơn.\n- Phí lưu kho o và mức phạt p giữ cố định trong một thí nghiệm; bài báo còn cho phép mức phí biến thiên theo chu kỳ.\n- Chi phí mua hàng chuẩn hóa bằng 0. Cuối chu kỳ episodic: thanh lý 0, không thêm phí loại bỏ. Nondiscarding: giữ toàn bộ tồn, kể cả ngày chờ chuyển bản sao.\n- HQL dùng lưới nguyên 0…M; cận gốc có hệ số 8. Meta-HQL dùng ba bản sao dịch pha và lịch khối 1, 2, 4… tập; C₂ = 1 là lựa chọn minh họa cho hằng số bài để mở.\n- Tùy chọn cận thu hẹp nhanh và xử lý giữ tập của bản sao cuối được ghi rõ trên giao diện; không suy diễn thành đảm bảo regret lý thuyết.")
    st.markdown("Nguồn mô hình: Gong & Simchi-Levi, *Bandits atop Reinforcement Learning: Tackling Online Inventory Models with Cyclic Demands*, Mục 2. [Mở bài báo](https://doi.org/10.1287/mnsc.2023.4947).")

st.caption("LOST-SALES LAB · Mô phỏng môi trường tồn kho để học qua quyết định · H = 3")
