"""ForgeAI's Streamlit frontend — Anthropic Console-inspired design with muted brick-red accents."""
from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import urlencode

import streamlit as st

from api_client import APIError, endpoint, request

FAILURE_CATEGORIES = ("retrieval miss", "prompt defect", "hallucination", "wrong refusal")


def api(*segments: str, **kwargs):
    return request(endpoint(*segments), **kwargs)


def models(providers, configured_only=False):
    return list(dict.fromkeys(
        model for p in providers
        if p["configured"] or not configured_only
        for model in p["models"]
    ))


def status_pill(status: str) -> str:
    s = (status or "").lower()
    if s in {"complete", "completed", "passed", "supported"}:
        cls = "forge-pill-success"
    elif s in {"failed", "incomplete", "unsupported", "hallucination", "wrong refusal"}:
        cls = "forge-pill-red"
    elif s in {"running", "waiting_intake", "waiting_approval", "partial", "error", "complete_with_errors"}:
        cls = "forge-pill-warn"
    else:
        cls = "forge-pill-neutral"
    return f'<span class="forge-pill {cls}">{escape(status)}</span>'


def choose_run(key: str):
    runs = api("runs")["runs"]
    if not runs:
        st.info("Build an agent to create your first run.")
        st.stop()
    labels = {run["id"]: f'{run["id"]} ({run["status"]})' for run in runs}
    ids = list(labels)
    preferred = st.query_params.get("run") or st.session_state.get("preferred_run")
    return st.selectbox(
        "Agent run",
        ids,
        index=ids.index(preferred) if preferred in labels else 0,
        format_func=labels.__getitem__,
        key=key,
        label_visibility="collapsed",
    )


def lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# 1. Overview
# ---------------------------------------------------------------------------

def overview():
    heading, action = st.columns([4.2, 1], vertical_alignment="center")
    with heading:
        st.header("Your workspace")
        st.html('<div class="forge-subtitle">Generated agents, evaluation scorecards, and demonstration artifacts.</div>')
    with action:
        with st.container(key="overview-cta"):
            st.page_link(build_page, label="Build Agent", icon=":material/add:")

    runs = api("runs")["runs"]
    if not runs:
        with st.container(border=True):
            st.info("No generated agents found. Upload documents and provide a brief to build your first agent.")
        return

    search_col, status_col = st.columns([2.5, 1])
    query_text = search_col.text_input("Search agents", placeholder="Search by run ID, scope, or model...", label_visibility="collapsed")
    statuses = ["All statuses", *sorted({r["status"] for r in runs})]
    status_filter = status_col.selectbox("Filter status", statuses, label_visibility="collapsed")

    filtered = []
    q = query_text.strip().lower()
    for run in runs:
        if status_filter != "All statuses" and run["status"] != status_filter:
            continue
        if q and q not in f'{run["id"]} {run["scope"]} {run["model"]}'.lower():
            continue
        filtered.append(run)

    if not filtered:
        st.info("No runs match the current search or status filter.")
        return

    rows = []
    for run in filtered:
        rate = run["selected_pass_rate"]
        score = f'<strong>{rate:.0%}</strong> <span style="color:#73736C;font-size:0.75rem">({run["total_cases"]})</span>' if rate is not None else "—"
        short_model = run["model"].split("/")[-1] if "/" in run["model"] else run["model"]
        query = urlencode({"run": run["id"]})
        actions = " ".join(
            f'<a href="{page.url_path}?{query}">{label}</a>'
            for page, label in (
                (playground_page, "Chat"),
                (evaluations_page, "Eval"),
                (reports_page, "Reports"),
            )
        )
        rows.append(
            f'<tr>'
            f'<td><strong>{escape(run["id"])}</strong><small title="{escape(run["scope"])}">{escape(run["scope"])}</small></td>'
            f'<td title="{escape(run["model"])}"><code>{escape(short_model)}</code></td>'
            f'<td>{status_pill(run["status"])}</td>'
            f'<td>{score}</td>'
            f'<td class="run-actions">{actions}</td>'
            f'</tr>'
        )
    st.html(
        '<div class="forge-table-wrap"><table class="forge-table">'
        '<colgroup><col style="width:36%"><col style="width:18%"><col style="width:15%"><col style="width:11%"><col style="width:20%"></colgroup>'
        '<thead><tr><th>Agent / Run</th><th>Model</th><th>Status</th><th>Score</th><th style="text-align:right">Actions</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


# ---------------------------------------------------------------------------
# 2. Build Agent (with Vertical Stepper & Human Checkpoint)
# ---------------------------------------------------------------------------

def render_stepper(stages: list[dict], build_status: str):
    items = []
    for idx, stage in enumerate(stages, 1):
        st_name = stage["status"]
        badge_cls = st_name if st_name in {"completed", "running", "failed"} else ""
        num_label = "✓" if st_name == "completed" else f"{idx:02d}"
        detail = escape(stage.get("detail") or "")
        label = st_name.replace("_", " ").capitalize()
        if build_status in {"waiting_intake", "waiting_approval"} and st_name == "completed" and idx in (2, 3):
            label = "Awaiting review"
        items.append(
            f'<div class="forge-step">'
            f'  <div class="forge-step-left">'
            f'    <div class="forge-step-num {badge_cls}">{num_label}</div>'
            f'    <div>'
            f'      <div class="forge-step-title">{escape(stage["name"])}</div>'
            f'      {f"<div class=forge-step-detail>{detail}</div>" if detail else ""}'
            f'    </div>'
            f'  </div>'
            f'  <div>{status_pill(label)}</div>'
            f'</div>'
        )
    st.html(f'<div class="forge-stepper">{"".join(items)}</div>')


@st.fragment(run_every=3)
def build_progress(build_id: str):
    try:
        build = api("builds", build_id)
    except APIError as exc:
        st.error(str(exc))
        if st.button("Return to build form"):
            st.session_state.pop("build_id", None)
            st.rerun()
        return

    status = build["status"]
    stages = build.get("stages", [])
    st.subheader("Execution pipeline")
    st.caption(f'Run ID: {build["run_id"]} · Model: {build["model"]} · Elapsed: {build.get("elapsed_seconds", 0)}s')
    if stages:
        render_stepper(stages, status)
    if status == "running":
        return
    st.session_state["build_snapshot"] = build
    if status in {"failed", "completed"}:
        st.session_state["preferred_run"] = build["run_id"]
    st.rerun()


def show_checkpoint(build: dict):
    build_id = build["build_id"]
    status = build["status"]
    st.subheader("Execution pipeline")
    st.caption(f'Run ID: {build["run_id"]} · Model: {build["model"]}')
    if build.get("stages"):
        render_stepper(build["stages"], status)

    st.divider()
    if status == "waiting_intake":
        st.subheader("Human checkpoint: Clarifying questions")
        st.caption("Answer up to 5 intake questions (leave blank to record as unresolved).")
        with st.form(f"{build_id}-intake"):
            answers = [st.text_input(q, key=f"{build_id}-answer-{i}") for i, q in enumerate(build["questions"])]
            if st.form_submit_button("Submit answers & continue", type="primary"):
                api("builds", build_id, "intake", json={"answers": answers})
                st.session_state.pop("build_snapshot", None)
                st.rerun()
    elif status == "waiting_approval":
        req = build["requirements"]
        st.subheader("Human checkpoint: Review requirements & groundability")
        if cov := build.get("coverage"):
            cov_rows = [
                f'<tr><td><strong>{escape(topic)}</strong></td><td>{status_pill(f["status"])}</td>'
                f'<td style="color:#73736C">{escape(f.get("limitation", ""))}</td></tr>'
                for topic, f in cov.items()
            ]
            st.html(
                '<div class="forge-table-wrap" style="margin-bottom:1rem"><table class="forge-table">'
                '<thead><tr><th>Topic</th><th>Groundability</th><th>Evidence / Limitation</th></tr></thead>'
                f'<tbody>{"".join(cov_rows)}</tbody></table></div>'
            )
        with st.form(f"{build_id}-approval"):
            scope = st.text_area("Scope", req["scope"])
            col1, col2 = st.columns(2)
            audience = col1.text_input("Audience", req["audience"])
            tone = col2.text_input("Tone", req["tone"])
            col3, col4 = st.columns(2)
            allowed = col3.text_area("Must answer (one topic per line)", "\n".join(req["must_answer"]))
            refused = col4.text_area("Must refuse (one topic per line)", "\n".join(req["must_refuse"]))
            if st.form_submit_button("Approve requirements & generate agent", type="primary"):
                revised = req | {
                    "scope": scope.strip() or req["scope"],
                    "audience": audience,
                    "tone": tone,
                    "must_answer": lines(allowed),
                    "must_refuse": lines(refused),
                }
                api("builds", build_id, "approve", json={"requirements": revised})
                st.session_state.pop("build_snapshot", None)
                st.rerun()
    elif status == "failed":
        st.error(build.get("error") or "Build failed.")
        st.page_link(evaluations_page, label="Open Evaluations")
    elif status == "completed":
        st.success(f'Agent ready: {build["run_id"]}')
        c1, c2 = st.columns(2)
        c1.page_link(playground_page, label="Open in Playground", icon=":material/chat:")
        c2.page_link(reports_page, label="View Reports", icon=":material/description:")


def build_agent():
    st.html('<div class="forge-breadcrumb">Agents / New</div>')
    st.header("Create an agent")
    st.html('<div class="forge-subtitle">Define the task, provide a knowledge source, and let ForgeAI build a grounded, evaluated agent.</div>')
    with st.container(key="build-content"):
        build_form()


def build_form():
    if build_id := st.session_state.get("build_id"):
        snapshot = st.session_state.get("build_snapshot")
        if not snapshot:
            build_progress(build_id)
        else:
            show_checkpoint(snapshot)
            if snapshot["status"] in {"completed", "failed"} and st.button("Start another build"):
                st.session_state.pop("build_id")
                st.session_state.pop("build_snapshot")
                st.rerun()
        return

    examples = api("examples")
    prov_data = api("providers")
    providers = prov_data["providers"]
    presets = {item["id"]: item for item in examples["briefs"]}
    datasets = {item["id"]: item["files"] for item in examples["datasets"]}
    all_models = ["auto", *models(providers)]
    default_model = prov_data.get("default_model")
    default_idx = all_models.index(default_model) if default_model in all_models else 0

    with st.form("build-agent", border=True):
        left, right = st.columns(2)
        name = left.text_input("Agent name", placeholder="e.g. policy-assistant", max_chars=60)
        model = right.selectbox(
            "Model",
            all_models,
            index=default_idx,
            format_func=lambda item: "Automatic fallback" if item == "auto" else item,
        )
        ex_col, btn_col = st.columns([3.5, 1], vertical_alignment="bottom")
        example = ex_col.selectbox(
            "Example brief (optional)",
            [None, *presets],
            format_func=lambda item: presets[item]["label"] if item else "Write your own",
        )
        if btn_col.form_submit_button("Load brief", disabled=not presets, use_container_width=True) and example:
            st.session_state["brief-template"] = presets[example]["brief"]
        brief = st.text_area(
            "Requester brief",
            st.session_state.get("brief-template", ""),
            height=85,
            max_chars=4000,
            placeholder="Describe the agent's scope, audience, tone, must-answer and must-refuse topics...",
        )
        uploads, examples_column = st.columns(2)
        files = uploads.file_uploader("Upload documents (PDF, TXT, CSV)", type=["pdf", "csv", "txt"], accept_multiple_files=True)
        selected = examples_column.selectbox(
            "Or select document dataset folder",
            [None, *datasets],
            format_func=lambda item: f"demo_data/{item} ({len(datasets[item])} files)" if item else "Choose a dataset",
        )
        st.divider()
        budget, intake, scope, submit = st.columns([1.2, 1.8, 1.2, 1.2], vertical_alignment="center")
        iterations = budget.number_input("Max iterations", 0, 3, int(prov_data.get("max_iterations", 1)))
        interactive = intake.checkbox("Interactive human checkpoint")
        prototype = scope.checkbox("Prototype only")
        if submit.form_submit_button("Build agent ->", type="primary", use_container_width=True):
            if len(brief.strip()) < 10 or not (files or selected) or (files and selected):
                st.error("Enter a brief of at least 10 characters and choose either uploaded files or one demo dataset.")
                return
            payload = {
                "name": name.strip(),
                "brief": brief.strip(),
                "model": model,
                "interactive": interactive,
                "prototype_only": prototype,
                "max_iterations": iterations,
            }
            if files:
                parts = [("files", (file.name, file.getvalue(), file.type)) for file in files]
                payload["upload_id"] = api("uploads", files=parts, timeout=90)["upload_id"]
            else:
                payload["demo_dataset"] = selected
            st.session_state["build_id"] = api("builds", json=payload)["build_id"]
            st.rerun()


# ---------------------------------------------------------------------------
# 3. Playground / Interactive Chat (3-column layout)
# ---------------------------------------------------------------------------

def show_trace(trace: dict, *, show_evidence: bool = True):
    answer = trace.get("answer") or {}
    st.write(answer.get("answer", trace.get("error") or "No answer was returned."))
    if answer.get("refused"):
        st.html('<span class="forge-pill forge-pill-warn">Out-of-scope or insufficient evidence refusal</span>')
    if answer.get("citations"):
        chips = "".join(f'<span class="forge-source-chip">{escape(c)}</span>' for c in answer["citations"])
        st.html(f'<div style="margin-top:0.35rem"><span style="font-size:0.75rem;color:#73736C;margin-right:0.4rem">Sources:</span>{chips}</div>')
    if show_evidence and (trace.get("retrieved") or trace.get("tools")):
        with st.expander("Grounding and tool activity"):
            for passage in trace.get("retrieved", []):
                st.code(passage["id"], language=None)
                st.caption(passage["text"])
            for tool in trace.get("tools", []):
                st.json(tool, expanded=False)


def playground():
    title, run_col, model_col, actions = st.columns([1.4, 2, 1.9, 1.5], vertical_alignment="center")
    title.header("Interactive chat")
    with run_col:
        run_id = choose_run("chat-run")
    with model_col:
        options = [None, *models(api("providers")["providers"], configured_only=True)]
        model = st.selectbox("Chat model", options, format_func=lambda item: item or "Saved run model", label_visibility="collapsed")
    detail = api("runs", run_id)
    config = detail["agent_config"]
    conversations = st.session_state.setdefault("conversations", {})
    history = conversations.setdefault(run_id, [])
    if actions.button("New chat", use_container_width=True):
        history.clear()
        st.rerun()
    show_grounding = actions.toggle("Grounding", value=True, key="chat-grounding")
    st.divider()

    if show_grounding:
        chat, grounding = st.columns([2.8, 1.2], gap="medium")
        with grounding.container(key="grounding-panel"):
            st.subheader("Grounding")
            latest = history[-1][1] if history else {}
            manifest = detail.get("document_manifest") or config.get("document_manifest") or {}
            with st.container(border=True):
                st.markdown(f'**{len(manifest)} documents**')
                st.caption(latest.get("model") or model or config["model"])
            sources = latest.get("retrieved", [])
            st.markdown(f'**Retrieved sources ({len(sources)})**')
            if sources:
                for passage in sources:
                    with st.container(border=True):
                        st.markdown(f'`{passage["id"]}`')
                        st.caption(passage["text"][:220] + ("…" if len(passage["text"]) > 220 else ""))
            else:
                st.caption("Send a message to inspect retrieved passages and citations.")
            if latest.get("tools"):
                with st.expander("Tool calls"):
                    st.json(latest["tools"])
            with st.expander("Agent definition"):
                st.caption("System prompt")
                st.text(config["system_prompt"])
                st.caption("Retrieval & tools")
                st.json({"settings": config["settings"], "tools": [t["name"] for t in config.get("tools", [])]})
    else:
        chat = st.container()

    with chat:
        st.markdown(f'**{run_id}**')
        st.html(f'<div class="forge-subtitle" style="margin-bottom:0.75rem">{escape(config["requirements"]["scope"])}</div>')
        with st.container(height=360, border=False):
            if not history:
                st.caption("Ask an in-scope, out-of-scope, or tool-backed question to test this agent.")
            for question, trace in history:
                st.chat_message("user").write(question)
                with st.chat_message("assistant"):
                    show_trace(trace, show_evidence=not show_grounding)
        if prompt := st.chat_input("Ask a question...", max_chars=2000):
            question = prompt.strip()
            if question:
                with st.spinner("Retrieving evidence and generating response..."):
                    trace = api("runs", run_id, "chat", json={"question": question, "model": model}, timeout=240)
                history.append((question, trace))
                st.rerun()


# ---------------------------------------------------------------------------
# 4. Evaluations
# ---------------------------------------------------------------------------

def evaluations():
    heading, control = st.columns([3.2, 1.3], vertical_alignment="center")
    with heading:
        st.header("Agent evaluation")
        st.html('<div class="forge-subtitle">Automated tests to verify accuracy, grounding, and refusal adherence.</div>')
    with control:
        run_id = choose_run("evaluation-run")

    detail = api("runs", run_id)
    metadata = detail.get("run_metadata") or {}
    status = metadata.get("status", "prototype")
    if reason := metadata.get("stop_reason"):
        st.caption(f"Run status: {status} · {reason}")
    if status == "incomplete":
        mode = "scoring" if detail.get("eval_dataset") else "generation"
        if st.button(f"Resume {mode}", type="primary"):
            result = api("runs", run_id, "resume", json={"mode": mode})
            st.success(f'Resume requested · {result["status"]}')

    cards = detail["scorecards"]
    if cards:
        selected_v = metadata.get("selected_version")
        card = next((c for c in cards if c["version"] == selected_v), cards[0])
        grounded = card.get("dimensions", {}).get("grounded")
        g_rate = f'{grounded["passed"] / grounded["scored"]:.0%}' if grounded and grounded["scored"] else "—"
        g_sub = f'{grounded["passed"]}/{grounded["scored"]} scored cases' if grounded and grounded["scored"] else "No scored cases"

        left, right = st.columns(2)
        left.html(
            f'<div class="forge-metric-card">'
            f'  <div>'
            f'    <div class="forge-metric-label">Selected version (v{card["version"]})</div>'
            f'    <div class="forge-metric-value">{card["passed"]} / {card["total"]} tests passed</div>'
            f'    <div class="forge-metric-sub">{card["failed"]} failed · {card["error"]} infrastructure errors</div>'
            f'  </div>'
            f'  <span class="score-badge">{card["pass_rate"]:.0%}</span>'
            f'</div>'
        )
        right.html(
            f'<div class="forge-metric-card">'
            f'  <div>'
            f'    <div class="forge-metric-label">Grounding</div>'
            f'    <div class="forge-metric-value">{g_rate} grounded</div>'
            f'    <div class="forge-metric-sub">{g_sub}</div>'
            f'  </div>'
            f'</div>'
        )

    cases_tab, metrics_tab, optimization_tab = st.tabs(["Test cases", "Metrics", "Optimization log"])

    with cases_tab:
        if results := detail["case_results"]:
            f1, f2, f3, f4 = st.columns([1, 1, 1, 1.5])
            version = f1.selectbox("Iteration", list(results), key=f"version-{run_id}")
            outcome_filter = f2.selectbox("Status", ["All", "passed", "failed", "error"])
            categories = sorted({item["case"]["category"] for item in results[version]})
            category_filter = f3.selectbox("Category", ["All", *categories])
            search_q = f4.text_input("Search", placeholder="Search test cases...", label_visibility="collapsed")

            rows_shown = 0
            for item in results[version]:
                case = item["case"]
                if outcome_filter not in ("All", item["status"]) or category_filter not in ("All", case["category"]):
                    continue
                if search_q.strip() and search_q.strip().lower() not in f'{case["id"]} {case["question"]}'.lower():
                    continue
                rows_shown += 1
                grounded_flag = (item.get("judgment") or {}).get("grounded")
                g_text = "Grounded" if grounded_flag else (item.get("failure") or "Ungrounded")
                with st.expander(f'{case["id"]} · {case["category"]} · {item["status"].upper()} · {case["question"]}'):
                    c1, c2 = st.columns([1, 3])
                    c1.html(f'{status_pill(item["status"])}<div style="margin-top:0.4rem">{status_pill(g_text)}</div>')
                    c2.markdown(f'**Judge explanation:** {item["explanation"]}')
                    show_trace(item["execution"])
                    with st.expander("Expected facts & raw judgment"):
                        st.json({"expected": case, "judgment": item.get("judgment")})
            if not rows_shown:
                st.info("No test cases match the current filters.")
        else:
            st.info("No scored cases yet.")
        if dataset := detail.get("eval_dataset"):
            with st.expander("Frozen evaluation dataset"):
                st.json(dataset, expanded=False)

    with metrics_tab:
        if cards:
            st.subheader("Baseline vs optimization iterations")
            st.dataframe(
                [{k: v for k, v in card.items() if k != "dimensions"} for card in cards],
                hide_index=True,
                use_container_width=True,
            )
            chart_rows = [{"Version": f'v{c["version"]}', "Passed": c["passed"], "Failed": c["failed"], "Error": c["error"]} for c in cards]
            st.bar_chart(chart_rows, x="Version", y=["Passed", "Failed", "Error"], color=["#B43C32", "#D6D1C7", "#E6B800"])
            st.json({f'v{c["version"]}': c["dimensions"] for c in cards}, expanded=False)
        else:
            st.info("No scorecards yet.")

    with optimization_tab:
        st.subheader("Failure classification summary")
        if results := detail["case_results"]:
            v0_key = next(iter(results))
            counts = Counter(item.get("failure") for item in results[v0_key] if item.get("failure"))
            cols = st.columns(4)
            for col, cat in zip(cols, FAILURE_CATEGORIES):
                col.html(
                    f'<div class="forge-metric-card">'
                    f'  <div><div class="forge-metric-label">{cat.title()}</div>'
                    f'  <div class="forge-metric-value">{counts.get(cat, 0)}</div></div>'
                    f'</div>'
                )
        if logs := detail["iteration_logs"]:
            st.subheader("Targeted optimization iterations")
            for step in logs:
                with st.container(border=True):
                    top_l, top_r = st.columns([3, 1], vertical_alignment="center")
                    top_l.markdown(f'**Iteration {step["iteration"]}** (base `v{step["base_version"]}`)')
                    top_r.html(status_pill(step.get("outcome", "unmeasured")))
                    st.write(step["reason"])
                    before = step.get("before", {})
                    after = step.get("after", {})
                    st.caption(
                        f'Before: {before.get("passed", "?")}/{before.get("total", "?")} ({before.get("pass_rate", 0):.0%})'
                        + (f' → After: {after.get("passed", "?")}/{after.get("total", "?")} ({after.get("pass_rate", 0):.0%})' if after else "")
                        + f' · Affected cases: {", ".join(step.get("affected_case_ids", []))}'
                    )
                    with st.expander("Changed fields"):
                        st.json(step.get("changes", {}))
        else:
            st.info("No optimization iterations recorded.")


# ---------------------------------------------------------------------------
# 5. Reports
# ---------------------------------------------------------------------------

def reports():
    heading, control = st.columns([3.2, 1.3], vertical_alignment="center")
    with heading:
        st.header("Reports")
        st.html('<div class="forge-subtitle">Inspect and download generated definitions, scorecards, and quality reports.</div>')
    with control:
        run_id = choose_run("report-run")

    detail = api("runs", run_id)
    menu, preview = st.columns([1.15, 2.85], gap="medium")
    formats = {
        "final_report": "Final quality report",
        "agent_config": "Agent definition",
        "requirements": "Requirements",
        "coverage": "Groundability",
        "scorecards": "Scorecards",
        "iteration_logs": "Optimization logs",
        "eval_dataset": "Evaluation dataset",
    }
    with menu:
        with st.container(border=True):
            selected = st.radio("Artifact preview", list(formats), format_func=formats.__getitem__)
        with st.container(border=True):
            files = ["All artifacts (ZIP)", *[f["name"] for f in detail["files"]]]
            filename = st.selectbox("Download artifact", files)
            zip_file = filename == files[0]
            if st.button("Prepare ZIP" if zip_file else "Prepare download", type="primary", use_container_width=True):
                path = ("download-zip",) if zip_file else ("artifacts", filename)
                data = api("runs", run_id, *path, binary=True, timeout=90)
                st.session_state["download"] = (run_id, filename, data)
            download = st.session_state.get("download")
            if download and download[:2] == (run_id, filename):
                st.download_button(
                    "Download ZIP" if zip_file else "Download file",
                    download[2],
                    file_name=f"{run_id}-artifacts.zip" if zip_file else filename,
                    mime="application/zip" if zip_file else "application/octet-stream",
                    use_container_width=True,
                )
    with preview.container(border=True):
        if selected == "final_report":
            if report := detail.get("final_report"):
                st.markdown(report)
            else:
                st.info("This run has no final quality report.")
        else:
            st.json(detail.get(selected) or {})


# ---------------------------------------------------------------------------
# 6. Settings
# ---------------------------------------------------------------------------

def settings():
    st.header("Settings")
    st.html('<div class="forge-subtitle">Verify provider connectivity, configure fallback order, and set execution defaults. API credentials remain on the backend.</div>')
    data = api("providers")
    checks = st.session_state.setdefault("provider-checks", {})
    all_models = models(data["providers"])

    with st.container(key="settings-content"):
        st.subheader("Model providers")
        with st.container(border=True):
            for i, provider in enumerate(data["providers"]):
                if i:
                    st.divider()
                pid = provider["id"]
                label, status_col, action = st.columns([2.5, 1.6, 0.9], vertical_alignment="center")
                label.markdown(f'**{provider["name"]}**')
                label.caption(provider["default_model"])
                if pid in checks:
                    res = checks[pid]
                    if res["ok"]:
                        status_col.success(f'{res["message"]} ({res["latency_ms"]} ms)')
                    elif pid == "ollama":
                        status_col.info(res["message"])
                    else:
                        status_col.error(res["message"])
                else:
                    badge = "Optional (local)" if pid == "ollama" else ("Configured" if provider["configured"] else "Not configured")
                    status_col.html(status_pill(badge))
                if action.button("Verify", key=f"verify-{pid}", use_container_width=True):
                    with st.spinner(f"Verifying {provider['name']}..."):
                        checks[pid] = api("providers", pid, "verify", json={})
                    st.rerun()

        st.subheader("Evaluation & fallback preferences")
        with st.form("settings-form", border=True):
            fallback_order = st.multiselect(
                "Fallback order (used when model is set to Automatic fallback)",
                options=["groq", "cloudflare", "nvidia"],
                default=[p for p in data["fallback_order"] if p in {"groq", "cloudflare", "nvidia"}] or ["groq", "cloudflare", "nvidia"],
            )
            col1, col2 = st.columns(2)
            default_model = col1.selectbox(
                "Default agent model",
                options=all_models,
                index=all_models.index(data.get("default_model")) if data.get("default_model") in all_models else 0,
            )
            judge_model = col2.selectbox(
                "Default judge model",
                options=all_models,
                index=all_models.index(data.get("judge_model")) if data.get("judge_model") in all_models else 0,
            )
            col3, col4 = st.columns(2)
            max_iterations = col3.slider("Default max optimization iterations", 0, 3, int(data.get("max_iterations", 1)))
            request_timeout = col4.number_input("Request timeout (seconds)", min_value=10, max_value=240, value=int(data.get("request_timeout", 45)))
            st.caption(f'Embedding model: {data["default_embedding"]} (local CPU + FAISS)')
            if st.form_submit_button("Save settings", type="primary"):
                if not fallback_order:
                    st.error("Select at least one provider in the fallback order.")
                else:
                    api("settings", json={
                        "fallback_order": fallback_order,
                        "default_model": default_model,
                        "judge_model": judge_model,
                        "max_iterations": max_iterations,
                        "request_timeout": int(request_timeout),
                    })
                    st.success("Settings saved for this backend session.")


# ---------------------------------------------------------------------------
# 7. Documentation
# ---------------------------------------------------------------------------

def docs():
    st.header("Documentation")
    st.html('<div class="forge-subtitle">Architecture, agent creation workflow, evaluation pipeline, and CLI commands.</div>')
    with st.container(key="docs-content"):
        sections = {
            "Getting started": (
                "Start the FastAPI backend (`cd backend && python -m uvicorn api.main:app --reload --port 8000`) "
                "and launch the Streamlit UI (`streamlit run streamlit_frontend/app.py`)."
            ),
            "Agent creation workflow": (
                "1. **Document ingestion** (`documents.py`): Parses PDF, TXT, and CSV with stable source IDs.\n"
                "2. **Intake interviewer** (`intake.py`): Asks up to 5 clarifying questions (or runs unattended) to produce `requirements.json`.\n"
                "3. **Groundability guard** (`coverage.py`): Checks requested topics against retrieved evidence and restricts unsupported topics.\n"
                "4. **Agent generator** (`generator.py`): Produces validated `agent_config.json` with system prompt, chunking/retrieval parameters, output contract, and minimal tool allowlist."
            ),
            "Dataset requirements": (
                "Full evaluation generates multi-document test cases and therefore requires **at least 2 source documents** (PDF, TXT, or CSV) aligned with the requester brief. "
                "Single-document briefs can be tested using **Prototype only** mode."
            ),
            "Human checkpoint": (
                "Enabling **Interactive human checkpoint** pauses the build after intake questions and after groundability verification so the requester can edit and approve `requirements.json` before agent generation."
            ),
            "Grounded RAG & tools": (
                "`runner.py` loads any saved `agent_config.json`, retrieves chunks via CPU FAISS (`all-MiniLM-L6-v2`), executes only allowlisted tools (`csv_lookup`, `calculator`, `current_date`, `weather`), and validates citations."
            ),
            "Automated evaluation & optimization": (
                "`evaluation.py` freezes 20+ cases across `direct`, `out_of_scope`, `unsupported`, `ambiguous`, and `multi_document`. "
                "`judge.py` combines deterministic evidence/numeric checks with blinded LLM judging. "
                "`optimizer.py` classifies failures (`retrieval miss`, `prompt defect`, `hallucination`, `wrong refusal`), applies up to 3 targeted patches, and retains the best measured version."
            ),
            "CLI commands": None,
        }
        sec = st.radio("Section", list(sections), horizontal=True, label_visibility="collapsed")
        with st.container(border=True):
            st.subheader(sec)
            if sections[sec]:
                st.markdown(sections[sec])
            else:
                st.code(
                    "cd backend\n"
                    "python -m pytest -q\n"
                    "python -m forgeai build --non-interactive --brief \"...\" --docs ./demo_data/academic --out ./artifacts/my-run\n"
                    "python -m forgeai chat --config ./artifacts/groq-academic-final/agent_config.json\n"
                    "python -m forgeai evaluate --resume-scoring --run ./artifacts/groq-academic-final",
                    language="bash",
                )


# ---------------------------------------------------------------------------
# Sidebar & Navigation
# ---------------------------------------------------------------------------

@st.fragment(run_every=15)
def backend_status():
    try:
        connected = api("health", timeout=3).get("status") == "ok"
    except APIError:
        connected = False
    state = "connected" if connected else "offline"
    st.html(f'<div class="backend-status {state}"><span></span>Backend {state}</div>')


st.set_page_config(page_title="ForgeAI", page_icon=":material/smart_toy:", layout="wide")
theme = Path(__file__).with_name("style.css").read_text(encoding="utf-8")
st.markdown(f"<style>{theme}</style>", unsafe_allow_html=True)

build_page = st.Page(build_agent, title="Build Agent", url_path="build", icon=":material/add_box:")
playground_page = st.Page(playground, title="Playground", icon=":material/chat_bubble_outline:")
evaluations_page = st.Page(evaluations, title="Evaluations", icon=":material/bar_chart:")
reports_page = st.Page(reports, title="Reports", icon=":material/description:")
main_pages = [
    st.Page(overview, title="Overview", default=True, icon=":material/grid_view:"),
    build_page,
    playground_page,
    evaluations_page,
    reports_page,
]
secondary_pages = [
    st.Page(settings, title="Settings", url_path="settings", icon=":material/settings:"),
    st.Page(docs, title="Documentation", url_path="docs", icon=":material/menu_book:"),
]
navigation = st.navigation([*main_pages, *secondary_pages], position="hidden")

with st.sidebar:
    st.markdown('<div class="forge-brand"><span class="forge-brand-mark"></span>ForgeAI</div>', unsafe_allow_html=True)
    for page in main_pages:
        st.page_link(page)
    with st.container(key="secondary-nav"):
        for page in secondary_pages:
            st.page_link(page)
        backend_status()

try:
    navigation.run()
except APIError as error:
    st.error(str(error))
