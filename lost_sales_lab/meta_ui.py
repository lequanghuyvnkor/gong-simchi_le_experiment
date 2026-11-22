"""Read-only daily replay of Meta-HQL's scheduler and physical transitions."""

from math import ceil

import altair as alt
import pandas as pd
import streamlit as st

from hql import QUpdate
from hql_ui import decimal


def rewind_meta() -> None:
    st.session_state.meta_cursor = 1


def move_meta(amount: int, limit: int, finish: bool = False) -> None:
    st.session_state.meta_cursor = limit if finish else min(limit, max(1, st.session_state.meta_cursor + amount))


def arm_rows(states):
    return [{
        "Bản sao w": state.arm,
        "Thứ tự ngày thực": " – ".join(str((state.arm + i - 1) % 3 + 1) for i in range(3)),
        "Tập đã học K_w": state.episodes,
        "V₁ ước lượng": state.value,
        "Trần bắt đầu": state.entry_cap,
        "Trạng thái": "Đã ngừng" if not state.alive else "Đang xét" if state.selected else "Còn ứng viên",
    } for state in states]


def explain_meta_plan(choice) -> None:
    st.write(f"Bandit đang xét **bản sao {choice.arm}**, pha **j = {choice.bandit_phase}**; cần chạy thêm **{choice.block_target} tập** trong khối, đã xong **{choice.completed_in_block}**.")
    if choice.status == "run":
        st.success(f"Ngày thực {choice.day} (vị trí {choice.phase} trong chu kỳ) dùng ngày nội bộ {choice.local_phase} của bản sao {choice.arm}. Đang có {choice.opening}, đặt thêm {choice.ordered}, đạt y = {choice.order_up_to}.")
    else:
        phase_text = "đúng pha" if choice.phase == choice.arm else f"cần pha {choice.arm}, hiện là pha {choice.phase}"
        stock_text = "tồn đủ thấp" if choice.opening <= choice.entry_cap else f"tồn {choice.opening} vượt trần bắt đầu {choice.entry_cap}"
        st.info(f"Đặt thêm 0 để chờ chuyển: {phase_text}; {stock_text}. Hàng đang có tiếp tục bán, vẫn phát sinh chi phí.")


def render_meta(run) -> None:
    agent = run.agent
    st.subheader("Meta-HQL điều phối các bản sao thế nào?")
    st.caption(f"{agent.label} · Một kho thực, ba bản sao HQL ảo · Tồn kho thực được giữ qua mọi chu kỳ và lần chuyển.")
    st.markdown("**Ba nhánh bandit hiện tại**")
    roster = pd.DataFrame(arm_rows(agent.states()))
    styled = roster.style.format({"V₁ ước lượng": "{:.5f}"}).apply(lambda row: ["background-color: #e4f3ee" if row["Trạng thái"] == "Đang xét" else "" for _ in row], axis=1)
    st.dataframe(styled, hide_index=True, use_container_width=True)
    st.caption(f"Pha bandit hiện tại j = {agent.bandit_phase}; mỗi nhánh còn lại được phân khối {2**agent.bandit_phase} tập. K_w chỉ đếm tập 3 ngày nội bộ đã hoàn tất; ngày chờ không tăng bộ đếm.")
    if run.config.cycles < 12:
        st.info("Ván ngắn vẫn cho thấy việc chuyển bản sao. Để xem trọn nhiều pha 1, 2, 4… tập, bạn có thể đặt 12 chu kỳ trở lên trong thanh bên.")
    if agent.confidence_scale != 8 or agent.bandit_c2 != 1:
        st.warning("Đang dùng tham số minh họa thu hẹp nhanh. Nhãn và CSV ghi rõ các hệ số; không diễn giải kết quả thành đảm bảo lý thuyết của bài báo.")
    if agent.safeguard_count:
        st.warning(f"Đã có {agent.safeguard_count} lần giữ lại tập ứng viên trước của bản sao cuối vì phép chặn làm rỗng tập. Chi tiết được ghi trong các bước ngày tương ứng.")
    if agent.days_observed < agent.total_days:
        with st.expander(f"Kế hoạch Meta-HQL cho ngày {agent.days_observed + 1}", expanded=not agent.steps):
            explain_meta_plan(agent.plan())
            st.caption("Kế hoạch dùng thông tin đã có, trước nhu cầu mới. Mở phần này không chạy thêm ngày.")
    if not agent.steps:
        st.info("Chọn mức đặt hàng của bạn rồi bấm Chạy ngày. Mỗi ngày sẽ có dấu vết chọn nhánh, kiểm tra chuyển, quyết định và phản hồi.")
    else:
        timeline = pd.DataFrame([{
            "Ngày": step.choice.day, "Bản sao đang xét": f"Bản sao {step.choice.arm}",
            "Trạng thái": "Chạy HQL" if step.choice.status == "run" else "Chờ chuyển",
            "Tồn đầu": step.choice.opening, "Đặt thêm": step.choice.ordered,
            "Ngày nội bộ": str(step.choice.local_phase) if step.choice.local_phase else "—",
        } for step in agent.steps])
        ticks = sorted(set([1, len(agent.steps), *range(1, len(agent.steps) + 1, max(1, ceil(len(agent.steps) / 15)))]))
        visual = alt.Chart(timeline).mark_rect().encode(
            x=alt.X("Ngày:O", title="Ngày thực đã chạy", axis=alt.Axis(labelAngle=0, values=ticks)),
            y=alt.Y("Bản sao đang xét:N", sort=["Bản sao 1", "Bản sao 2", "Bản sao 3"], title=None, scale=alt.Scale(domain=["Bản sao 1", "Bản sao 2", "Bản sao 3"])),
            color=alt.Color("Trạng thái:N", scale=alt.Scale(domain=["Chạy HQL", "Chờ chuyển"], range=["#0f766e", "#b46d18"]), legend=alt.Legend(orient="bottom")),
            tooltip=["Ngày:O", "Bản sao đang xét:N", "Trạng thái:N", "Ngày nội bộ:N", "Tồn đầu:Q", "Đặt thêm:Q"],
        ).properties(height=270, title="Bản sao nào đang chạy, ngày nào đang chờ?").configure_view(stroke=None)
        st.altair_chart(visual, use_container_width=True)
        st.session_state.setdefault("meta_day_select", len(agent.steps))
        day = st.selectbox("Ngày Meta-HQL muốn xem lại", list(range(1, len(agent.steps) + 1)), key="meta_day_select", on_change=rewind_meta)
        step = agent.steps[day - 1]
        limit = len(step.events)
        st.session_state.setdefault("meta_cursor", 1)
        st.session_state.meta_cursor = min(limit, max(1, st.session_state.meta_cursor))
        st.slider("Bước bandit đang xem", min_value=1, max_value=limit, key="meta_cursor")
        left, middle, right = st.columns(3)
        left.button("Bước bandit trước", key="meta_previous", on_click=move_meta, args=(-1, limit), disabled=st.session_state.meta_cursor == 1, use_container_width=True)
        middle.button("Bước bandit tiếp", key="meta_next", on_click=move_meta, args=(1, limit), disabled=st.session_state.meta_cursor == limit, use_container_width=True)
        right.button("Xem cuối ngày", key="meta_finish", on_click=move_meta, args=(0, limit, True), disabled=st.session_state.meta_cursor == limit, use_container_width=True)
        index = st.session_state.meta_cursor
        event = step.events[index - 1]
        st.caption(f"Ngày thực {day} · bước {index} / {limit}. Đây là phát lại dấu vết đã lưu; không chạy ngày mới, không đổi lựa chọn và không học lặp lại.")
        st.markdown(f"**{event.title}**")
        st.write(event.explanation)
        st.caption(f"Kết quả đã xảy ra trong ngày này: bản sao đang xét {step.choice.arm}; bán {step.sales}; còn {step.remaining} sản phẩm chuyển tiếp.")
        if event.kind == "bandit_review" and step.review:
            review = step.review
            review_rows = [{"Nhánh": row.arm, "K_w": row.episodes, "V₁": row.value, "V tốt nhất − V₁": row.gap, "Ngưỡng 2CB₂": row.threshold, "Quyết định": "Đã ngừng trước" if not row.was_alive else "Giữ" if row.kept else "Loại"} for row in review.assessments]
            st.dataframe(pd.DataFrame(review_rows).style.format({"V₁": "{:.5f}", "V tốt nhất − V₁": "{:.5f}", "Ngưỡng 2CB₂": "{:.5f}"}), hide_index=True, use_container_width=True)
        if step.q_trace:
            with st.expander(f"Xem cập nhật Q của bản sao {step.choice.arm} trong ngày {day}"):
                trace = step.q_trace
                st.write(f"Tập riêng k = {trace.episode}; α = {decimal(trace.alpha)}. Các h dưới đây là ngày nội bộ, theo thứ tự ngày thực bắt đầu từ pha {step.choice.arm}.")
                updates = [{"h nội bộ": e.phase, "Mức y": e.action, "Q cũ": e.old_q, "Tổng r": e.reward_sum, "V nối": e.bootstrap, "τ": e.stopping_phase, "Q mới": e.new_q} for e in trace.events if isinstance(e, QUpdate)]
                st.dataframe(pd.DataFrame(updates).style.format({column: "{:.5f}" for column in ["Q cũ", "Tổng r", "V nối", "Q mới"]}), hide_index=True, use_container_width=True, height=280)

    with st.expander("Xem Q hiện tại của từng bản sao"):
        arm = st.selectbox("Bản sao có bảng Q muốn xem", [1, 2, 3], key="meta_q_arm")
        base = agent.learners[arm - 1]
        q_rows = {"Mức y": range(agent.capacity + 1)}
        for h in range(3):
            real_phase = (arm + h - 1) % 3 + 1
            q_rows[f"Q h{h + 1} · ngày thực {real_phase}"] = base.q[h]
            q_rows[f"Ứng viên h{h + 1}"] = base.active[h]
        st.dataframe(pd.DataFrame(q_rows), hide_index=True, use_container_width=True)
        st.caption("Đây là Q hiện tại sau tất cả ngày đã chạy, độc lập với ngày đang chọn để phát lại. Bản sao không được chơi hoặc ngày đang chờ không nhận mẫu học.")
    with st.expander("Cách bandit chọn và các quy ước của bản học"):
        st.write("Ba nhánh tương ứng ba cách dịch đầu chu kỳ: 1–2–3, 2–3–1 và 3–1–2. Bandit đi qua các nhánh còn lại theo thứ tự, mỗi pha giao thêm 2^j tập cho mỗi nhánh; đây là lịch khám phá có loại nhánh, không phải chọn tham lam nhánh điểm cao nhất mỗi ngày.")
        st.latex(r"V^{(w)}_1=\max_{y\in A^{(w)}_1}Q^{(w)}_1(y),\qquad 2CB_2(K_w)=4C_2\sqrt{\frac{H^7\log T}{K_w}}")
        st.write("Bản học xét loại ở cuối pha, sau khi các nhánh còn lại đã hoàn tất khối được giao, theo phần mô tả pha ở Mục 5. K_w đếm tập riêng hoàn tất của nhánh. Giữ nhánh tốt nhất; loại nhánh có chênh lệch V ít nhất ngưỡng 2CB₂ của nó.")
        st.write("Bài báo để C₂ dưới dạng hằng số; mặc định C₂ = 1 ở đây là lựa chọn của bản học. Lưới mức tồn nguyên và cận thu hẹp nhanh là các cấu hình để học, không dùng để khẳng định cận regret lý thuyết.")
        st.write("Khi vào một khối mới, chờ đúng pha và tồn đủ thấp bằng cách đặt thêm 0. Trong khối đang chạy, các tập HQL nối tiếp; tồn thực không bị xóa khi bộ học kết thúc một tập ảo. Sau mỗi tập, chặn trần các ngày nội bộ 2–3 theo ngày đầu. Nếu chặn làm rỗng tập thì dừng bản sao; với bản sao cuối, bản học giữ tập trước và ghi dấu bảo vệ.")
        st.markdown("Đối chiếu Algorithm 2 và Mục 5, trang 6149–6150 của [bài báo gốc](https://doi.org/10.1287/mnsc.2023.4947).")
