"""Inspectable HQL choices, immutable update replay, and paired comparisons."""

from math import isfinite

import altair as alt
import pandas as pd
import streamlit as st

from experiment import PairedRun
from hql import Elimination, QUpdate


def decimal(value: float) -> str:
    return f"{value:.5f}".rstrip("0").rstrip(".") if isfinite(value) else "∞"


def rewind_q() -> None:
    st.session_state.q_cursor = 0


def move_q(amount: int, limit: int, finish: bool = False) -> None:
    st.session_state.q_cursor = limit if finish else min(limit, max(0, st.session_state.q_cursor + amount))


def explain_choice(choice) -> None:
    largest = max(choice.running)
    st.write(f"Ngày {choice.day}, vị trí h = {choice.phase}: HQL đang có **{choice.opening}** sản phẩm; còn **{len(choice.running)}** mức ứng viên.")
    if choice.opening < largest:
        st.success(f"Chọn y = max(Aₕ) = {largest}; đặt thêm {choice.ordered} để nâng tồn từ {choice.opening} lên {choice.order_up_to}.")
    elif choice.opening == largest:
        st.info(f"Tồn đã bằng mức ứng viên cao nhất {largest}. Giữ y = {choice.opening}, đặt thêm 0.")
    else:
        st.info(f"Tồn {choice.opening} đang cao hơn mọi ứng viên (cao nhất {largest}). HQL giữ y = x = {choice.opening}, đặt thêm 0 và chờ bán bớt.")
    st.caption(f"Một mức đạt Q cao nhất trong tập (có thể đồng hạng) là y = {choice.best_q_action}. Quy tắc chọn của HQL ưu tiên mức cao nhất còn trong tập để khai thác phản hồi một phía.")
    st.caption(f"Tập ứng viên dùng cho quyết định: {', '.join(map(str, choice.running))}.")


def render_hql(run: PairedRun) -> None:
    st.subheader("HQL nghĩ gì khi đặt hàng?")
    agent = run.agent
    if agent is None:
        st.info("HQL ở Mục 4 áp dụng cho episodic lost-sales. Chọn Loại bỏ hết (episodic) trong thiết lập để xem HQL và so sánh. Mô hình giữ tồn qua chu kỳ cần Meta-HQL.")
        return
    st.caption(f"{agent.label} · lưới số nguyên 0…{agent.capacity} · Q là điểm lợi ích kỳ vọng còn lại, đo bằng phần thưởng chuẩn hóa.")
    if agent.confidence_scale != 8:
        st.warning("Bạn đang dùng cận thu hẹp nhanh để minh họa loại hành động. Biến thể này không mang đảm bảo lý thuyết của cận gốc; CSV ghi rõ phiên bản và hệ số.")

    if agent.days_observed < agent.total_days:
        with st.expander(f"Quyết định HQL cho ngày {agent.days_observed + 1} sắp chạy", expanded=not run.choices):
            explain_choice(agent.plan())
            st.caption("Kế hoạch này được lập trước khi nhu cầu ngày đó phát sinh. Xem kế hoạch không chạy thêm ngày.")
    if run.choices:
        selected_day = st.selectbox(
            "Xem lại quyết định HQL đã chạy", list(range(1, len(run.choices) + 1)),
            key="hql_decision_day", format_func=lambda day: f"Ngày {day} · h = {(day - 1) % 3 + 1}",
        )
        choice = run.choices[selected_day - 1]
        explain_choice(choice)
        observed = run.hql_history[selected_day - 1]
        st.write(f"Sau quyết định, cửa hàng HQL ghi nhận **S = {observed.sales}**, còn **I = {observed.remaining}**. Đây là phản hồi riêng của HQL.")
        if observed.censored:
            st.caption(f"HQL chỉ biết D ≥ {observed.sales}; phần cầu vượt quá hàng sẵn bán không đi vào bộ học.")
        else:
            st.caption(f"Vì còn hàng, HQL suy ra nhu cầu hôm đó bằng lượng bán {observed.sales}.")

    st.markdown("**Cập nhật Q vào cuối chu kỳ, theo thứ tự h = 3, 2, 1**")
    if not agent.traces:
        st.info(f"Đã thu {len(agent.buffer)} / 3 phản hồi trong chu kỳ đầu. Q vẫn bằng 3 cho mọi mức; sau khi chạy ngày 3, bạn có thể phát lại từng phép cập nhật ở đây.")
        st.dataframe(pd.DataFrame({"Mức y": range(agent.capacity + 1), "Q ngày 1": agent.q[0], "Q ngày 2": agent.q[1], "Q ngày 3": agent.q[2]}), hide_index=True, use_container_width=True)
    else:
        episode = st.selectbox("Chu kỳ có cập nhật Q", list(range(1, len(agent.traces) + 1)), key="q_episode_select", on_change=rewind_q)
        trace = agent.traces[episode - 1]
        limit = len(trace.events)
        st.session_state.setdefault("q_cursor", 0)
        st.session_state.q_cursor = min(st.session_state.q_cursor, limit)
        st.slider("Bước cập nhật đang xem", min_value=0, max_value=limit, key="q_cursor")
        previous, following, final = st.columns(3)
        previous.button("Bước Q trước", key="q_previous", on_click=move_q, args=(-1, limit), disabled=st.session_state.q_cursor == 0, use_container_width=True)
        following.button("Bước Q tiếp", key="q_next", on_click=move_q, args=(1, limit), disabled=st.session_state.q_cursor == limit, use_container_width=True)
        final.button("Xem hết chu kỳ", key="q_finish", on_click=move_q, args=(0, limit, True), disabled=st.session_state.q_cursor == limit, use_container_width=True)
        cursor = st.session_state.q_cursor
        q, active = trace.snapshot(cursor)
        event = trace.events[cursor - 1] if cursor else None
        phase = event.phase if event else 3
        st.caption(f"Phát lại chu kỳ {episode}: bước {cursor} / {limit}. Các nút này chỉ đổi phần giải thích; Q thật và ngày mô phỏng không thay đổi.")

        if isinstance(event, QUpdate):
            st.markdown(f"**Cập nhật Q của ngày h = {event.phase}, mức y = {event.action}**")
            st.write(f"Thử quỹ đạo giả định bắt đầu với {event.action} sản phẩm. Ở mỗi bước, lượng bán giả định là min(hàng đang có, lượng bán HQL đã quan sát).")
            path = [{"Ngày h": step.phase, "Hàng giả định": step.stock, "Lượng bán HQL quan sát": step.observed_sales, "Bán giả định": step.simulated_sales, "Còn lại": step.remaining, "Phần thưởng r": step.reward} for step in event.trajectory]
            st.dataframe(pd.DataFrame(path).style.format({"Phần thưởng r": "{:.5f}"}), hide_index=True, use_container_width=True)
            if event.stopping_phase == 4:
                st.write("Dừng ở τ = 4: đã hết chu kỳ 3 ngày, nên giá trị tiếp nối V₄ = 0.")
            else:
                st.write(f"Dừng ở τ = {event.stopping_phase}: tồn giả định đã cho phép chọn lại một mức trong tập ứng viên của ngày đó. Lấy Vτ tốt nhất trong các mức còn khả thi.")
            st.write(f"Tổng thưởng trước τ = **{decimal(event.reward_sum)}**; Vτ = **{decimal(event.bootstrap)}**; mục tiêu cập nhật = **{decimal(event.target)}**.")
            st.latex(r"Q_{\mathrm{mới}}=(1-\alpha_k)Q_{\mathrm{cũ}}+\alpha_k\left(\sum_{s=h}^{\tau-1} r_s+V_\tau\right)")
            st.write(f"α = {decimal(event.alpha)}: (1 − {decimal(event.alpha)}) × {decimal(event.old_q)} + {decimal(event.alpha)} × {decimal(event.target)} = **{decimal(event.new_q)}**.")
        elif isinstance(event, Elimination):
            st.markdown(f"**Thu hẹp tập ứng viên của ngày h = {event.phase}**")
            st.write(f"Q tốt nhất = **{decimal(event.best_q)}** tại mức y = {event.best_action}. Giữ mức y khi Q tốt nhất − Q(y) ≤ **{decimal(event.bound)}**.")
            st.write(f"Giữ {len(event.kept)} mức: {', '.join(map(str, event.kept))}.")
            if event.removed:
                st.write(f"Loại {len(event.removed)} mức: {', '.join(map(str, event.removed))}.")
            else:
                st.info("Chưa loại mức nào: chênh lệch Q vẫn nằm trong cận tin cậy. Q đã được cập nhật dù tập ứng viên chưa đổi.")
        else:
            first_event = trace.events[0]
            st.write(f"Đây là bảng trước khi học từ chu kỳ đã chọn. Bấm Bước Q tiếp để xem phép cập nhật đầu tiên, bắt đầu ở h = {first_event.phase}, y = {first_event.action}.")

        table = pd.DataFrame({
            "Mức y": range(agent.capacity + 1),
            "Q trước chu kỳ": trace.q_before[phase - 1],
            "Q đang xem": q[phase - 1],
            "Tập ứng viên": ["Còn" if flag else "Đã loại" for flag in active[phase - 1]],
        })
        st.markdown(f"**Bảng Q của ngày h = {phase} tại bước đang xem**")
        styled = table.style.format({"Q trước chu kỳ": "{:.5f}", "Q đang xem": "{:.5f}"})
        if isinstance(event, QUpdate):
            styled = styled.apply(lambda row: ["background-color: #e4f3ee" if row["Mức y"] == event.action else "" for _ in row], axis=1)
        st.dataframe(styled, hide_index=True, use_container_width=True, height=320)
        if agent.confidence_scale == 8:
            st.caption("Cận gốc dùng hệ số 8 nên rất bảo thủ trong ván ngắn. Mức đặt hàng có thể vẫn cao qua nhiều chu kỳ; hãy quan sát số Q thay đổi trước khi kỳ vọng tập ứng viên thu hẹp.")
        with st.expander("Toàn bộ Q hiện tại sau các chu kỳ đã học"):
            st.dataframe(pd.DataFrame({"Mức y": range(agent.capacity + 1), "Q ngày 1": agent.q[0], "Q ngày 2": agent.q[1], "Q ngày 3": agent.q[2]}).style.format({f"Q ngày {h}": "{:.5f}" for h in (1, 2, 3)}), hide_index=True, use_container_width=True)

    with st.expander("Công thức và phạm vi triển khai"):
        st.latex(r"r=\frac{oM-oI+pS}{(o+p)M},\qquad \alpha_k=\frac{H+1}{H+k}")
        st.latex(r"CB_1=c\sqrt{\frac{H^5\,9\log(AT)}{k-1}},\quad c=8\ \text{trong bài báo}")
        st.write("Q khởi tạo bằng H = 3. Phần thưởng nằm trong [0,1] và tăng khi chi phí giả định giảm. Bản học dùng A = M + 1 mức nguyên từ 0 đến M; bài báo dùng lưới mịn phụ thuộc T. Chu kỳ đầu đặt cận vô hạn để giữ toàn bộ ứng viên.")
        st.write("Cập nhật ngược từ ngày 3 về ngày 1; quỹ đạo giả định chỉ cộng thưởng đến trước thời điểm dừng τ rồi nối Vτ. HQL học từ lượng bán riêng, không nhận nhu cầu thật hay phản hồi của bạn. Cả hai phía dùng cùng tồn kho ban đầu; các chu kỳ tiếp theo đều bắt đầu từ 0.")
        st.markdown("Đối chiếu Algorithm 1, Mục 4, trang 6146–6147 của [bài báo gốc](https://doi.org/10.1287/mnsc.2023.4947).")


def render_comparison(run: PairedRun, researcher: bool) -> None:
    name = run.algorithm_name
    st.subheader(f"Bạn và {name} trên cùng chuỗi nhu cầu")
    if run.agent is None:
        st.info("Chạy một thuật toán để mở phần so sánh.")
        return
    st.caption(f"Đối thủ đang chạy: {run.agent.label}. Mỗi lần bấm Chạy ngày, cả hai phía chốt quyết định trước cùng một lần sinh nhu cầu.")
    if not run.human:
        st.info(f"Chạy ngày đầu tiên bằng mức đặt hàng của bạn. {name} sẽ chạy cùng ngày và kết quả xuất hiện ở đây.")
        return
    data = pd.DataFrame(run.comparison_rows(researcher))
    last = data.iloc[-1]
    gap = float(last[f"Chênh lệch chi phí Bạn − {name}"])
    a, b, c = st.columns(3)
    if researcher:
        human_field, hql_field = "Bạn · tổng chi phí", f"{name} · tổng chi phí"
        a.metric("Tổng chi phí · Bạn", decimal(float(last[human_field])))
        b.metric(f"Tổng chi phí · {name}", decimal(float(last[hql_field])))
    else:
        human_field, hql_field = "Bạn · chi phí giả định lũy kế", f"{name} · chi phí giả định lũy kế"
        a.metric("Chi phí giả định · Bạn", decimal(float(last[human_field])))
        b.metric(f"Chi phí giả định · {name}", decimal(float(last[hql_field])))
    c.metric(f"Chênh lệch Bạn − {name}", f"{'+' if gap > 0 else ''}{decimal(gap)}")
    st.write(f"Chênh lệch dương nghĩa là {name} tốn ít chi phí hơn; âm nghĩa là cách đặt hàng của bạn tốn ít hơn trên các ngày đã chạy.")
    if name == "Meta-HQL":
        waits = sum(choice.status != "run" for choice in run.choices)
        st.caption(f"Đã tính đủ {len(run.human)} ngày thực, gồm {waits} ngày chờ chuyển. Tồn kho của cả hai phía đều được giữ sang ngày sau.")
    if not researcher:
        st.info("Đang so sánh chi phí giả định tính được từ lượng bán và tồn dư của từng bên. Vì cùng nhu cầu D, chênh lệch này bằng chênh lệch chi phí thật. Bật góc nhìn người nghiên cứu để xem nhu cầu chung và tổng chi phí thật của mỗi bên.")
    plotted = data[["Ngày", human_field, hql_field]].rename(columns={human_field: "Bạn", hql_field: name}).melt("Ngày", var_name="Cách đặt hàng", value_name="Chi phí lũy kế")
    visual = alt.Chart(plotted).mark_line(point=True).encode(
        x=alt.X("Ngày:O", title="Ngày đã chạy", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Chi phí lũy kế:Q", title="Chi phí thật lũy kế" if researcher else "Chi phí giả định lũy kế", scale=alt.Scale(zero=True)),
        color=alt.Color("Cách đặt hàng:N", scale=alt.Scale(domain=["Bạn", name], range=["#4f79a5", "#0f766e"]), legend=alt.Legend(orient="bottom")),
        strokeDash=alt.StrokeDash("Cách đặt hàng:N", legend=None),
        tooltip=["Ngày:O", "Cách đặt hàng:N", alt.Tooltip("Chi phí lũy kế:Q", format=".2f")],
    ).properties(height=280).configure_view(stroke=None)
    st.altair_chart(visual, use_container_width=True)
    st.dataframe(data, hide_index=True, use_container_width=True)
    st.download_button(f"Tải so sánh Bạn và {name} · CSV", data.to_csv(index=False).encode("utf-8-sig"), file_name=f"so_sanh_ban_va_{name.lower().replace('-', '_')}.csv", mime="text/csv", key="download_comparison")
    st.caption(f"Đây là so sánh trên đúng chuỗi nhu cầu đã chạy. Xem phản hồi và Q của {name} trong lúc chơi có thể cung cấp thêm thông tin cho quyết định của bạn; để tự thử độc lập, hãy hoàn tất ván thủ công trước rồi mở phần thuật toán.")
