"""Vietnamese business explanations and read-only FQL learning replay."""

import altair as alt
import pandas as pd
import streamlit as st

from fql_model import FQLConfig, FQLSpec, StockState, flow
from fql_experiment import FQLRun


def num(value):
    return f"{value:,.4f}".rstrip("0").rstrip(".").replace(",", " ")


def pair(values):
    return f"(A: {values[0]}, B: {values[1]})"


def reset_fql(config=None):
    config = config or st.session_state.fql_run.config
    st.session_state.fql_run = FQLRun(config)
    for key in list(st.session_state):
        if key.startswith(("fql_q_", "fql_inspect_")) or key in ("fql_decision_day", "fql_history_day", "fql_error"):
            st.session_state.pop(key, None)
    for i in range(2):
        st.session_state[f"fql_order_{i}"] = min(2, config.spec.max_order[i])


def advance_fql():
    run = st.session_state.fql_run
    if len(run.human) >= run.config.total_days:
        return
    try:
        result = run.step(tuple(st.session_state[f"fql_order_{i}"] for i in range(2)))
        st.session_state.fql_decision_day = result.day
        st.session_state.fql_history_day = result.day
        if result.terminal:
            st.session_state.fql_q_episode = result.cycle
            st.session_state.fql_q_cursor = 0
        st.session_state.pop("fql_error", None)
    except ValueError as error:
        st.session_state.fql_error = str(error)


def settings(run):
    current = run.config
    spec = current.spec
    with st.sidebar:
        st.header("Thiết lập FQL")
        st.caption("2 sản phẩm · H = 3 · L = 1 · backlogging episodic")
        with st.form("fql_settings"):
            cycles = st.number_input("Số chu kỳ FQL", 1, 20, current.cycles, key="fql_cfg_cycles")
            initial, caps, purchase, holding, back = [], [], [], [], []
            for i, name in enumerate(("A", "B")):
                with st.expander(f"Sản phẩm {name} · tồn, hạn mức và phí"):
                    initial.append(st.number_input(f"Tồn ban đầu {name}", 0, 5, spec.initial_stock[i], key=f"fql_cfg_initial_{i}"))
                    caps.append(st.number_input(f"Đặt tối đa {name} mỗi ngày", 1, 4, spec.max_order[i], key=f"fql_cfg_cap_{i}"))
                    purchase.append(st.number_input(f"Tiền mua một đơn vị {name}", 0., 100., spec.purchase[i], step=.5, key=f"fql_cfg_buy_{i}"))
                    holding.append(st.number_input(f"Phí lưu một đơn vị {name}/ngày", 0., 100., spec.holding[i], step=.5, key=f"fql_cfg_hold_{i}"))
                    back.append(st.number_input(f"Phí chờ một đơn vị {name}/ngày", 0., 100., spec.backlog_rate[i], step=.5, key=f"fql_cfg_back_{i}"))
            fixed = st.number_input("Phí chung mỗi lần đặt hàng F", 0., 100., spec.fixed_fee, step=.5, key="fql_cfg_fixed")
            means = []
            with st.expander("Nhu cầu lặp theo 3 ngày"):
                st.caption(f"Mỗi sản phẩm có nhu cầu Binomial({spec.demand_cap}, p), từ 0 đến {spec.demand_cap}. Đây là phân phối hữu hạn, không phải cắt ngọn Poisson. FQL không biết p hay trung bình.")
                for phase in range(3):
                    means.append(tuple(st.number_input(f"Cầu trung bình {name} · ngày {phase + 1}", 0., float(spec.demand_cap), float(current.demand_means[phase][i]), step=.5, key=f"fql_cfg_mean_{phase}_{i}") for i, name in enumerate(("A", "B"))))
                seed = st.number_input("Mã tình huống FQL (seed)", 0, 2**32 - 1, current.seed, key="fql_cfg_seed")
            submitted = st.form_submit_button("Áp dụng và bắt đầu lại FQL", use_container_width=True)
        if submitted:
            try:
                updated = FQLConfig(FQLSpec(tuple(caps), tuple(initial), spec.demand_cap, tuple(purchase), tuple(holding), tuple(back), float(fixed)), int(cycles), tuple(means), int(seed))
                reset_fql(updated)
                st.success("Đã bắt đầu thí nghiệm FQL mới.")
            except ValueError as error:
                st.error(str(error))
        st.button("Chơi lại cùng nhu cầu FQL", key="fql_replay", on_click=reset_fql, use_container_width=True)
        st.caption("Chỉ bấm Áp dụng mới đổi thiết lập. Chơi lại giữ nguyên seed và toàn bộ nhu cầu tương ứng từng ngày.")


def state_table(state):
    return pd.DataFrame({"Sản phẩm": ["A", "B"], "Tồn trong kho": state.on_hand,
                         "Đơn còn nợ": state.backlog, "Hàng đến hôm nay": state.pipeline})


def flow_table(result):
    f = result.flow
    return pd.DataFrame({
        "Sản phẩm": ["A", "B"], "Tồn đầu": f.opening.on_hand, "Nợ đầu": f.opening.backlog,
        "Hàng đến": f.opening.pipeline, "Đặt hôm nay": f.order, "Nhu cầu mới": f.demand,
        "Giao nợ cũ": f.old_filled, "Giao cầu mới": f.new_filled,
        "Tồn cuối": f.closing.on_hand, "Nợ cuối": f.closing.backlog,
        "Đang về cuối": f.closing.pipeline,
    })


def explain_flow(result, spec):
    f = result.flow
    for i, col in enumerate(st.columns(2)):
        with col:
            name = ("A", "B")[i]
            st.markdown(f"**Sản phẩm {name} · nhu cầu mới {f.demand[i]}**")
            st.write(f"Tồn đầu {f.opening.on_hand[i]}, nợ cũ {f.opening.backlog[i]}; nhận {f.opening.pipeline[i]} từ đơn hôm qua. Giao nợ cũ {f.old_filled[i]} trước, rồi giao {f.new_filled[i]} cho nhu cầu mới.")
            st.markdown(f"**Tồn cuối: {f.closing.on_hand[i]} · Nợ cuối: {f.closing.backlog[i]} · Đang về: {f.order[i]}**")
            st.caption(f"Tồn ròng: {f.opening.net[i]} + {f.opening.pipeline[i]} − {f.demand[i]} = {f.closing.net[i]}. Số âm biểu thị nợ khách, không phải hàng âm trong kho.")
    st.markdown(f"**Chi phí ngày: {num(f.total_cost)}** = mua {num(f.purchase_cost)} + phí đặt chung {num(f.fixed_cost)} + lưu kho {num(f.holding_cost)} + chờ giao {num(f.backlog_cost)}.")
    st.caption(f"Tiền mua = {num(spec.purchase[0])} × {f.order[0]} + {num(spec.purchase[1])} × {f.order[1]}. Phí chung {num(spec.fixed_fee)} tính một lần nếu có đặt A hoặc B. Phí chờ tính trên toàn bộ nợ cuối ngày, kể cả nợ cũ còn chưa giao.")
    if result.terminal:
        st.info(f"Kết thúc thí nghiệm 3 ngày: ghi nhận tồn {pair(f.closing.on_hand)}, nợ {pair(f.closing.backlog)}, đang về {pair(f.closing.pipeline)}. Các số dư này kết thúc tại đây, không chuyển sang episode mới. Sau khi tính đủ chi phí ngày 3, V₄ = 0; không hoàn tiền mua hay tính giá trị thu hồi. Episode sau khởi tạo lại cùng tồn ban đầu.")


def render_play(run):
    n = len(run.human)
    done = n >= run.config.total_days
    day = n + 1
    phase = (day - 1) % 3 + 1
    st.subheader("Đã hoàn tất thí nghiệm" if done else f"Chuẩn bị ngày {day} · ngày {phase}/3 của chu kỳ {(day - 1) // 3 + 1}")
    st.progress(n / run.config.total_days, text=f"Đã chạy {n} / {run.config.total_days} ngày")
    left, right = st.columns([1, 1.3], gap="large")
    with left:
        st.markdown("**Cửa hàng của bạn · số dư kết thúc**" if done else "**Cửa hàng của bạn · trước khi nhận hàng**")
        if done:
            closing = run.human[-1].flow.closing
            table = state_table(closing).rename(columns={"Hàng đến hôm nay": "Đang về cuối episode"})
        else:
            table = state_table(run.human_state)
        st.dataframe(table, hide_index=True, use_container_width=True)
        order = tuple(st.number_input(f"Bạn đặt thêm bao nhiêu {name}?", 0, run.config.spec.max_order[i], step=1, key=f"fql_order_{i}", disabled=done) for i, name in enumerate(("A", "B")))
        st.markdown(f'<div class="equation">Đặt thêm <b>{pair(order)}</b> → đến <b>ngày {day + 1}</b>.<br>Hàng đang đến hôm nay mới dùng để giao hôm nay.</div>', unsafe_allow_html=True)
        if phase == 3 and not done:
            st.caption("Đây là ngày cuối episode: đơn mới tới sau chân trời 3 ngày, vẫn trả tiền mua và phí đặt, nhưng không đem lại lợi ích trong episode này.")
        st.button("Đã chạy đủ số ngày" if done else f"Chạy ngày {day}", key="fql_advance", type="primary", disabled=done, on_click=advance_fql, use_container_width=True)
        st.caption("Một lần bấm chốt cả hai cửa hàng trước khi sinh đúng một cặp nhu cầu chung. Đổi số hoặc phát lại Q không chạy thêm ngày.")
        if "fql_error" in st.session_state:
            st.error(st.session_state.fql_error)
        with st.expander("Trình tự một ngày"):
            st.markdown("1. Xem tồn, nợ và đơn đang trên đường.\n2. Chốt đơn mới cho ngày mai.\n3. Nhận đơn đã đặt hôm qua.\n4. Giao nợ cũ trước, rồi phục vụ nhu cầu mới.\n5. Tính tiền mua, phí đặt chung, phí lưu kho và phí chờ giao.\n6. Mang tồn/nợ và đơn mới sang ngày sau trong cùng episode.")
    with right:
        if n:
            result = run.human[-1]
            st.subheader(f"Kết quả ngày {result.day} · cửa hàng của bạn")
            explain_flow(result, run.config.spec)
            if result.terminal:
                st.success("Đã học Q cho cả 3 ngày theo thứ tự 3 → 2 → 1. Mở FQL từng bước để phát lại.")
        else:
            st.subheader("Khách chờ giao, đơn hàng có độ trễ")
            st.write("Nếu hôm nay thiếu hàng, khách được ghi vào đơn còn nợ. Ngày mai, hàng về được dùng trả nợ trước. Bạn cần đặt từ hôm nay để đáp ứng nhu cầu ngày mai.")
            st.info("FQL chạy ở cửa hàng riêng, cùng tồn ban đầu và cùng nhu cầu. Sau đủ 3 ngày, FQL dùng nhu cầu đã thấy để học tất cả trạng thái và phương án đặt trong bảng Q.")


def render_history(run):
    if not run.human:
        st.info("Chạy ít nhất một ngày để xem dòng hàng và chi phí.")
        return
    policy = st.radio("Xem cửa hàng", ("Bạn", "FQL"), horizontal=True, key="fql_history_policy")
    day = st.selectbox("Xem lại ngày", range(1, len(run.human) + 1), key="fql_history_day")
    result = (run.human if policy == "Bạn" else run.algorithm)[day - 1]
    st.subheader(f"Ngày {day} · {policy} · chu kỳ {result.cycle}, ngày {result.phase}/3")
    st.dataframe(flow_table(result), hide_index=True, use_container_width=True)
    explain_flow(result, run.config.spec)
    st.caption("Tồn cuối, nợ cuối và đang về là số dư trước khi kết thúc episode. Bảng không thay số dư bằng số khởi tạo của chu kỳ sau.")


def decision_table(run, choice):
    rows = []
    for i, action in enumerate(run.agent.actions):
        rows.append({"Đặt A": int(action[0]), "Đặt B": int(action[1]), "Q trước quyết định": choice.q_values[i], "Được chọn": "✓" if i == choice.chosen_index else ""})
    return pd.DataFrame(rows)


def move_cursor(delta=None, end=False):
    st.session_state.fql_q_cursor = 3 if end else st.session_state.fql_q_cursor + delta


def render_q(run):
    agent = run.agent
    if not run.human:
        choice = agent.plan()
        st.subheader("FQL sẽ chọn đơn thế nào?")
        st.write(f"Q khởi tạo bằng H = 3. Có {len(agent.actions)} cặp đơn hợp lệ; khi hòa, chọn cặp nhỏ nhất theo thứ tự A rồi B, nên đơn đầu tiên là {pair(choice.order)}.")
        st.dataframe(decision_table(run, choice), hide_index=True, use_container_width=True)
        st.caption("Không cần ép thử mọi đơn: khi đã biết nhu cầu, FQL tính được kết quả giả định của mọi cặp đơn. Chạy đủ 3 ngày để xem cập nhật Q.")
        return
    if len(run.human) < run.config.total_days:
        upcoming = agent.plan()
        with st.expander(f"Kế hoạch FQL cho ngày {upcoming.day} sắp chạy"):
            st.write(f"Trạng thái hiện tại {upcoming.state.key}; chọn đơn {pair(upcoming.order)}, Q = {num(upcoming.q_values[upcoming.chosen_index])}. Chỉ dùng Q và trạng thái đã có, chưa biết nhu cầu ngày {upcoming.day}.")
            st.dataframe(decision_table(run, upcoming), hide_index=True, use_container_width=True)
    day = st.selectbox("Quyết định FQL của ngày", range(1, len(run.human) + 1), key="fql_decision_day")
    choice = run.choices[day - 1]
    result = run.algorithm[day - 1]
    st.subheader(f"1 · Chọn đơn trước khi thấy nhu cầu ngày {day}")
    st.write(f"Trạng thái x = (tồn ròng A, tồn ròng B; đang về A, đang về B) = {choice.state.key}. FQL chọn {pair(choice.order)} vì Q lớn nhất = {num(choice.q_values[choice.chosen_index])}.")
    if choice.tie_count > 1:
        st.caption(f"Có {choice.tie_count} cặp cùng Q lớn nhất. Quy tắc phá hòa: A nhỏ hơn trước, rồi B nhỏ hơn; không dùng nhu cầu hôm nay để chọn.")
    with st.expander("Xem Q của toàn bộ cặp đơn trước quyết định", expanded=False):
        st.dataframe(decision_table(run, choice), hide_index=True, use_container_width=True)
    st.subheader("2 · Quan sát đầy đủ và chuyển trạng thái")
    st.write(f"Quan sát nhu cầu {pair(result.flow.demand)}. Tồn ròng cuối = {pair(choice.state.net)} + hàng đến {pair(choice.state.pipeline)} − nhu cầu {pair(result.flow.demand)} = {pair(result.flow.closing.net)}. Đơn mới {pair(choice.order)} trở thành hàng đang về.")
    st.dataframe(flow_table(result), hide_index=True, use_container_width=True)
    st.caption("Khác lost-sales, mọi yêu cầu mua đều được ghi nhận, kể cả phần phải chờ. Cùng nhu cầu này cho phép tái tính chi phí và trạng thái kế tiếp cho cả những đơn không chọn.")
    st.subheader("3 · Cuối chu kỳ, cập nhật Q ngược ngày 3 → 2 → 1")
    if not agent.traces:
        st.info(f"Đã thu {len(agent.pending)}/3 cặp nhu cầu trong chu kỳ đầu. Q chưa thay đổi. Cần chạy ngày 3 để có đủ dữ liệu cập nhật.")
        return
    if agent.pending:
        st.caption(f"Chu kỳ hiện tại đang có {len(agent.pending)}/3 cặp nhu cầu; Q giữ nguyên từ chu kỳ hoàn tất gần nhất. Bên dưới là phát lại chu kỳ đã hoàn tất.")
    episode = st.selectbox("Chu kỳ học Q", range(1, len(agent.traces) + 1), key="fql_q_episode", on_change=lambda: st.session_state.update(fql_q_cursor=0))
    trace = agent.traces[episode - 1]
    st.session_state.setdefault("fql_q_cursor", 0)
    cursor = st.slider("Bước cập nhật Q", 0, 3, key="fql_q_cursor", help="0: trước khi học; 1: ngày 3; 2: ngày 2; 3: ngày 1. Chỉ phát lại dữ liệu đã lưu.")
    columns = st.columns(3)
    columns[0].button("Bước Q trước", key="fql_q_previous", disabled=cursor == 0, on_click=move_cursor, args=(-1,), use_container_width=True)
    columns[1].button("Bước Q tiếp", key="fql_q_next", disabled=cursor == 3, on_click=move_cursor, args=(1,), use_container_width=True)
    columns[2].button("Xem hết cập nhật", key="fql_q_finish", on_click=move_cursor, kwargs={"end": True}, use_container_width=True)
    update = trace.updates[max(cursor - 1, 0)]
    phase = update.phase
    grid = agent.grids[phase - 1]
    observation = trace.observations[phase - 1]
    st.markdown(f"**{'Chưa áp dụng · chuẩn bị' if cursor == 0 else f'Bước {cursor}/3 · đã cập nhật'} ngày {phase}**")
    st.write(f"Dùng nhu cầu ngày {phase}: {pair(update.demand)}. Quét {len(grid.values):,} trạng thái × {len(agent.actions)} cặp đơn = {update.q_after.size:,} ô Q; không chỉ ô thực tế đã đi qua.")
    st.caption(f"Toàn bộ bảng có {agent.entry_count:,} ô. Miền trạng thái bao gồm mọi trạng thái tới được từ tồn ban đầu trong 3 ngày với nhu cầu 0–{run.config.spec.demand_cap}; không chặn nợ hay cắt ngọn tồn.")
    with st.expander("Chọn trạng thái giả định để xem một lát bảng Q", expanded=True):
        values = []
        for i, col in enumerate(st.columns(4)):
            labels = ("Tồn ròng A", "Tồn ròng B", "Đang về A", "Đang về B")
            options = list(range(int(grid.low[i]), int(grid.low[i] + grid.shape[i])))
            values.append(col.selectbox(labels[i], options, index=options.index(observation.choice.state.key[i]), key=f"fql_inspect_state_{episode}_{phase}_{i}"))
        state = StockState(tuple(values[:2]), tuple(values[2:]))
        row = grid.index(state)
        shown = trace.snapshot(cursor)[phase - 1][row]
        frame = pd.DataFrame({"Đặt A": agent.actions[:, 0], "Đặt B": agent.actions[:, 1], "Q cũ": update.q_before[row], "Thưởng r": update.reward[row], "V ngày sau": update.bootstrap[row], "Mục tiêu r + V": update.target[row], "Q sau bước đang xem": shown})
        styled = frame.style.format({c: "{:.5f}" for c in frame.columns[2:]}).highlight_max(subset=["Q sau bước đang xem"], color="#e4f3ee")
        st.dataframe(styled, hide_index=True, use_container_width=True)
        st.caption("Ô xanh là Q cao nhất ở trạng thái này sau bước đang xem; các cặp đơn có thể cùng điểm.")
    index = st.selectbox("Ô Q muốn giải thích", range(len(agent.actions)), index=observation.choice.chosen_index, format_func=lambda i: f"Đặt A = {agent.actions[i, 0]}, B = {agent.actions[i, 1]}", key=f"fql_inspect_action_{episode}_{phase}")
    action = tuple(int(v) for v in agent.actions[index])
    hypothetical = flow(run.config.spec, state, action, update.demand)
    r, v = update.reward[row, index], update.bootstrap[row, index]
    old, target, new = update.q_before[row, index], update.target[row, index], update.q_after[row, index]
    st.markdown(f"- **Giả sử đặt {pair(action)}:** tồn cuối {pair(hypothetical.closing.on_hand)}, nợ cuối {pair(hypothetical.closing.backlog)}, đang về {pair(action)}.\n- **Chi phí C = {num(hypothetical.total_cost)}:** mua {num(hypothetical.purchase_cost)}, đặt chung {num(hypothetical.fixed_cost)}, lưu kho {num(hypothetical.holding_cost)}, chờ giao {num(hypothetical.backlog_cost)}.\n- **Thưởng r = 1 − C/Cmax = {num(r)}**, với Cmax = {num(run.config.spec.cost_bound)}. Thưởng cao tương ứng chi phí thấp; đây là điểm học, không phải lợi nhuận.\n- **V ngày sau = {num(v)}:** {'cuối chân trời nên V₄ = 0.' if phase == 3 else 'lấy Q lớn nhất tại đúng trạng thái kế tiếp, từ bảng ngày sau vừa cập nhật.'}\n- **α = (H+1)/(H+k) = 4/(3+{episode}) = {num(update.alpha)}.** Q mới = (1−α) × Q cũ + α × (r+V).\n- **({num(1-update.alpha)}) × {num(old)} + {num(update.alpha)} × ({num(r)} + {num(v)}) = {num(new)}.**")
    if cursor == 0:
        st.caption("Các con số trên là phép tính sắp phát lại. Bảng đang ở Q cũ; bấm Bước Q tiếp để áp dụng bước ngày 3 trên màn hình.")
    st.caption("Phát lại chỉ đọc dấu vết đã lưu. Không huấn luyện lại, không sinh thêm nhu cầu, không thay đổi quyết định của bạn hay FQL.")


def render_comparison(run):
    st.subheader("Hai cửa hàng, cùng từng cặp nhu cầu")
    if not run.human:
        st.info("Tự đặt hàng và chạy một ngày để bắt đầu so sánh.")
        return
    rows = run.comparison_rows()
    last = rows[-1]
    columns = st.columns(3)
    columns[0].metric("Bạn · tổng chi phí", num(last["Bạn · lũy kế"]))
    columns[1].metric("FQL · tổng chi phí", num(last["FQL · lũy kế"]))
    columns[2].metric("Bạn − FQL", num(last["Chênh lệch Bạn − FQL"]))
    st.caption("Chênh lệch dương: FQL tốn ít hơn trong lượt này. Bao gồm tiền mua, phí đặt chung, lưu kho và chờ giao của mọi ngày đã chạy.")
    records = [{"Ngày": row["Ngày"], "Cửa hàng": name, "Chi phí lũy kế": row[f"{name} · lũy kế"]} for row in rows for name in ("Bạn", "FQL")]
    ticks = sorted({1, len(rows), *range(1, len(rows) + 1, max(1, (len(rows) + 11) // 12))})
    colors = alt.Scale(domain=["Bạn", "FQL"], range=["#3b6ea8", "#0f766e"])
    chart = alt.Chart(pd.DataFrame(records)).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("Ngày:Q", axis=alt.Axis(values=ticks, format="d")), y=alt.Y("Chi phí lũy kế:Q", scale=alt.Scale(zero=True)),
        color=alt.Color("Cửa hàng:N", scale=colors), tooltip=["Ngày:Q", "Cửa hàng:N", alt.Tooltip("Chi phí lũy kế:Q", format=".2f")],
    ).properties(height=285)
    st.altair_chart(chart, use_container_width=True)
    name = st.selectbox("Sản phẩm để xem dòng hàng", ("A", "B"), key="fql_compare_product")
    inventory = [{"Ngày": row["Ngày"], "Chu kỳ": row["Chu kỳ"], "Cửa hàng": policy, "Số lượng": row[f"{policy} · {name} · {label}"], "Số dư": label.capitalize()} for row in rows for policy in ("Bạn", "FQL") for label in ("tồn cuối", "nợ cuối", "đang về cuối")]
    stock_ticks = sorted({1, len(rows), *range(1, len(rows) + 1, max(1, (len(rows) + 4) // 5))})
    for col, kind in zip(st.columns(3), ("Tồn cuối", "Nợ cuối", "Đang về cuối")):
        subset = pd.DataFrame([row for row in inventory if row["Số dư"] == kind])
        maximum = int(subset["Số lượng"].max())
        quantity_ticks = sorted({0, maximum, *range(0, maximum + 1, max(1, (maximum + 4) // 5))})
        with col:
            st.markdown(f"**{kind} · {name}**")
            lines = alt.Chart(subset).mark_line(point=True, strokeWidth=2).encode(
                x=alt.X("Ngày:Q", axis=alt.Axis(values=stock_ticks, format="d")),
                y=alt.Y("Số lượng:Q", scale=alt.Scale(domain=[0, max(1, maximum)], nice=False), axis=alt.Axis(values=quantity_ticks, format="d")),
                color=alt.Color("Cửa hàng:N", scale=colors, legend=alt.Legend(title=None, orient="top")),
                detail="Chu kỳ:N", tooltip=["Ngày:Q", "Cửa hàng:N", "Số dư:N", "Số lượng:Q"],
            ).properties(height=210)
            st.altair_chart(lines, use_container_width=True)
    st.caption("Đồ thị ghi số dư trước reset cuối ngày 3. Các đường tách theo episode, vì không chuyển số dư qua ranh giới chu kỳ.")
    display = ["Ngày", "Nhu cầu A", "Nhu cầu B", "Bạn · A · đặt thêm", "Bạn · B · đặt thêm", "FQL · A · đặt thêm", "FQL · B · đặt thêm", "Bạn · chi phí ngày", "FQL · chi phí ngày", "Chênh lệch Bạn − FQL"]
    data = pd.DataFrame(rows)
    st.dataframe(data[display], hide_index=True, use_container_width=True)
    st.download_button("Tải CSV · dòng hàng và chi phí hai bên", data.to_csv(index=False).encode("utf-8-sig"), "fql_paired_comparison.csv", "text/csv", key="fql_download")
    st.caption("Đây là so sánh trên một chuỗi nhu cầu, không phải regret kỳ vọng so với chính sách tối ưu biết phân phối. Xem Q trước khi tự chốt đơn có thể gợi ý cho bạn; hãy hoàn tất quyết định trước nếu muốn tự thử độc lập.")


def render_model(run):
    spec = run.config.spec
    st.subheader("Đọc mô hình bằng ngôn ngữ kinh doanh")
    st.dataframe(pd.DataFrame([
        ("N = 2", "Hai mã hàng A và B; không thay thế cho nhau."),
        ("H = 3", "Một thí nghiệm kéo dài 3 ngày. Phân phối nhu cầu lặp theo vị trí ngày."),
        ("L = 1", "Đơn đặt hôm nay chỉ đến ngày mai."),
        ("nᵢ", "Tồn ròng trước hàng đến = tồn trong kho − đơn còn nợ. Số âm nghĩa là còn nợ khách."),
        ("pᵢ", "Hàng đang trên đường, sẽ đến trong ngày hiện tại; thuộc trạng thái x."),
        ("x = (nA,nB,pA,pB)", "Toàn bộ thông tin kho và đơn hàng FQL dùng khi quyết định."),
        ("y = (qA,qB)", "Quyết định số lượng đặt thêm. Algorithm 3 ký hiệu y; giao diện dùng q để tránh nhầm với mức tồn mục tiêu của HQL."),
        ("D = (DA,DB)", "Toàn bộ nhu cầu được ghi nhận; phần chưa giao trở thành nợ, không mất đi trong chu kỳ."),
        ("Qₕ(x,y)", "Điểm thưởng dự kiến cho quyết định y trong trạng thái x, từ ngày h đến cuối episode."),
    ], columns=["Ký hiệu", "Ý nghĩa kinh doanh"]), hide_index=True, use_container_width=True)
    st.markdown(f"**Ràng buộc:** đặt nguyên 0 ≤ qA ≤ {spec.max_order[0]}, 0 ≤ qB ≤ {spec.max_order[1]}; hàng đã đặt không hủy; không trả hàng hay chuyển hàng giữa A và B. Không có ràng buộc sức chứa kho hoặc ngân sách chung. Phí đặt F là khoản phí, không phải một hạn mức.")
    st.latex(r"n'_{i}=n_i+p_i-D_i,\quad p'_i=q_i,\quad I'_i=\max(n'_i,0),\quad B'_i=\max(-n'_i,0)")
    st.latex(r"C=F\,\mathbf{1}\{q_A+q_B>0\}+\sum_{i\in\{A,B\}}(c_iq_i+o_iI'_i+b_iB'_i)")
    st.write("Trong cùng một sản phẩm, không vừa có tồn cuối dương vừa còn nợ: hàng sẵn có được dùng giao cho khách. Nợ chưa giao chịu phí chờ mỗi ngày cho tới khi được phục vụ hoặc tới cuối episode.")
    st.markdown("**Ranh giới episode phải đọc rõ:** bản học này xét các hợp đồng 3 ngày độc lập. Cuối ngày 3 ghi đủ chi phí và số dư tồn/nợ/đang về, đặt giá trị tiếp nối bằng 0, rồi khởi tạo lượt sau với cùng tồn ban đầu, nợ 0 và hàng đang về 0. Đây là quy ước terminal của bản mô phỏng; không mô tả việc hủy nợ khách miễn phí trong vận hành liên tục. Phí thanh lý, phạt trễ hạn cuối hợp đồng và giá trị thu hồi đều được đặt bằng 0. Muốn giữ mọi số dư qua chu kỳ cần mô hình nondiscarding và Mimic-QL.")
    st.markdown(f"**Lưới hữu hạn để nhìn được bảng Q:** nhu cầu mỗi mã từ 0 đến {spec.demand_cap}, đơn hàng nguyên theo hạn mức trên. Các xác suất và seed không được đưa cho bộ học. Liệt kê toàn bộ trạng thái tới được trong 3 ngày, tổng {run.agent.entry_count:,} ô Q. Không nén tồn ròng, không chặn nợ, không suy rộng đảm bảo lý thuyết sang mọi cấu hình thực tế.")
    st.latex(r"r=1-C/C_{\max},\quad\alpha_k=\frac{H+1}{H+k},\quad Q_h\leftarrow(1-\alpha_k)Q_h+\alpha_k\left[r_h+\max_{y'}Q_{h+1}(x',y')\right]")
    st.write(f"Cmax = {num(spec.cost_bound)} là cận trên cố định của chi phí ngày trên toàn miền hữu hạn; r trong [0,1]. Tối đa tổng điểm r tương đương tối thiểu tổng chi phí trong episode dài bằng nhau. Q khởi tạo bằng 3, học cuối chu kỳ theo ngày 3 → 2 → 1, dùng Q ngày sau vừa cập nhật; không có bandit hay tập ứng viên bị loại như HQL.")
    st.markdown("Nguồn: Gong & Simchi-Levi, [bài báo gốc](https://pubsonline.informs.org/doi/10.1287/mnsc.2023.4947), Mục 7–7.1, Algorithm 3, trang 6153–6154. Lưới nguyên, phân phối nhu cầu hữu hạn, hệ số chi phí và quy ước terminal cụ thể là lựa chọn của bản học.")


def render_fql_app():
    if "fql_run" not in st.session_state:
        reset_fql(FQLConfig())
    settings(st.session_state.fql_run)
    run = st.session_state.fql_run
    st.markdown('<div class="eyebrow">GONG & SIMCHI-LEVI · FULL-Q-LEARNING</div>', unsafe_allow_html=True)
    st.title("Đặt hôm nay. Giao ngày mai.")
    st.markdown('<p class="intro">Quản lý hai mã hàng, theo dõi khách đang chờ và hàng trên đường. Tự đặt hàng từng ngày, rồi xem FQL học từ cùng nhu cầu đã xảy ra.</p>', unsafe_allow_html=True)
    st.markdown('<span class="mode-label">FQL · 2 sản phẩm · Chu kỳ 3 ngày · Giao hàng 1 ngày · Có đơn còn nợ</span>', unsafe_allow_html=True)
    st.caption("Episodic: mỗi thí nghiệm 3 ngày kết thúc độc lập, không chuyển số dư sang chu kỳ sau. Mở thanh bên để đổi phí, hạn mức và kịch bản nhu cầu.")
    play, history, q, comparison, model = st.tabs(["Chạy từng ngày", "Dòng hàng & chi phí", "FQL từng bước", "So sánh", "Hiểu mô hình"])
    with play:
        render_play(run)
    with history:
        render_history(run)
    with q:
        render_q(run)
    with comparison:
        render_comparison(run)
    with model:
        render_model(run)
