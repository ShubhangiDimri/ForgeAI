"""ForgeAI's Streamlit frontend — Anthropic Console-inspired design with muted brick-red accents."""
from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

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


DEMO_RUN_IDS = {
    "groq-academic-final",
    "groq-procurement-final",
    "citation-precision-academic-r2",
    "citation-precision-procurement-r1",
    "groq-museum-rehearsal-r2",
    "retail-retrieval-key3-candidate",
}

STATUS_LABELS = {
    "complete": "Completed",
    "completed": "Completed",
    "complete_with_errors": "Completed with errors",
    "incomplete": "Incomplete",
    "prototype": "Prototype",
    "running": "Running",
}


def readable_status(status: str) -> str:
    return STATUS_LABELS.get((status or "").lower(), status.replace("_", " ").capitalize())


def readable_agent_name(run: dict) -> str:
    scope = (run.get("scope") or "").strip()
    if not scope or scope == run["id"]:
        return run["id"].replace("-", " ").title()
    clean = scope.removeprefix("Build an ").removeprefix("Build a ").strip()
    return clean[:52].rstrip(" ,.;") + ("…" if len(clean) > 52 else "")


def status_pill(status: str, label: str | None = None) -> str:
    s = (status or "").lower()
    if s in {"complete", "completed", "passed", "supported"}:
        cls = "forge-pill-success"
    elif s in {"failed", "incomplete", "unsupported", "hallucination", "wrong refusal"}:
        cls = "forge-pill-red"
    elif s in {"running", "waiting_intake", "waiting_approval", "partial", "error", "complete_with_errors"}:
        cls = "forge-pill-warn"
    else:
        cls = "forge-pill-neutral"
    return f'<span class="forge-pill {cls}">{escape(label or status)}</span>'


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

    search_col, view_col, status_col = st.columns([2, 1.1, 1.1])
    query_text = search_col.text_input("Search agents", placeholder="Search by agent, run ID, or model...", label_visibility="collapsed")
    view_filter = view_col.selectbox("Run type", ["All runs", "Demo runs", "Experiments"], label_visibility="collapsed")
    statuses = ["All statuses", *sorted({r["status"] for r in runs})]
    status_filter = status_col.selectbox(
        "Filter status",
        statuses,
        format_func=lambda s: s if s == "All statuses" else readable_status(s),
        label_visibility="collapsed",
    )

    filtered = []
    q = query_text.strip().lower()
    for run in runs:
        is_demo = run["id"] in DEMO_RUN_IDS
        if view_filter == "Demo runs" and not is_demo:
            continue
        if view_filter == "Experiments" and is_demo:
            continue
        if status_filter != "All statuses" and run["status"] != status_filter:
            continue
        if q and q not in f'{run["id"]} {run["scope"]} {run["model"]}'.lower():
            continue
        filtered.append(run)

    if not filtered:
        st.info("No runs match the current search or filters.")
        return

    page_size = 7
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    page_num = min(st.session_state.get("overview-page", 1), total_pages)
    start_idx = (page_num - 1) * page_size
    page_runs = filtered[start_idx : start_idx + page_size]

    rows = []
    for run in page_runs:
        rate = run["selected_pass_rate"]
        has_eval = rate is not None
        score = f'<strong>{rate:.0%}</strong> <span style="color:#73736C;font-size:0.75rem">({run["total_cases"]})</span>' if has_eval else "—"
        short_model = run["model"].split("/")[-1] if "/" in run["model"] else run["model"]
        created = run["created_at"][:10] if run.get("created_at") else "—"
        query = urlencode({"run": run["id"]})
        action_items = [
            f'<a href="{playground_page.url_path}?{query}">Chat</a>',
            f'<a href="{evaluations_page.url_path}?{query}">Eval</a>' if has_eval else '<span class="disabled" title="No evaluation available">Eval</span>',
            f'<a href="{reports_page.url_path}?{query}">Reports</a>',
        ]
        agent_title = readable_agent_name(run)
        rows.append(
            f'<tr>'
            f'<td><strong title="{escape(run["scope"])}">{escape(agent_title)}</strong><small>{escape(run["id"])}</small></td>'
            f'<td title="{escape(run["model"])}"><code>{escape(short_model)}</code></td>'
            f'<td>{status_pill(run["status"], readable_status(run["status"]))}</td>'
            f'<td>{score}</td>'
            f'<td style="color:#73736C;font-size:0.78rem">{escape(created)}</td>'
            f'<td class="run-actions">{" ".join(action_items)}</td>'
            f'</tr>'
        )
    st.html(
        '<div class="forge-table-wrap"><table class="forge-table">'
        '<colgroup><col style="width:27%"><col style="width:15%"><col style="width:17%"><col style="width:9%"><col style="width:10%"><col style="width:22%"></colgroup>'
        '<thead><tr><th>Agent</th><th>Model</th><th>Status</th><th>Score</th><th>Created</th><th style="text-align:right">Actions</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )

    info_col, prev_col, next_col = st.columns([4, 0.8, 0.8], vertical_alignment="center")
    info_col.caption(f"Showing {start_idx + 1}–{start_idx + len(page_runs)} of {len(filtered)} runs (Page {page_num} of {total_pages})")
    if prev_col.button("Previous", disabled=page_num <= 1, use_container_width=True):
        st.session_state["overview-page"] = page_num - 1
        st.rerun()
    if next_col.button("Next", disabled=page_num >= total_pages, use_container_width=True):
        st.session_state["overview-page"] = page_num + 1
        st.rerun()


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
        if seconds := stage.get("elapsed_seconds"):
            detail += f" · {seconds:.1f}s"
        label = st_name.replace("_", " ").capitalize()
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
    if status in {"running", "retrying"}:
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
        if req.get("requester_answers") or req.get("unresolved") or req.get("assumptions"):
            with st.expander("Intake decisions and open questions"):
                for question, answer in req.get("requester_answers", {}).items():
                    st.text(f"{question}\n{answer}")
                for item in req.get("assumptions", []):
                    st.caption(f"Assumption · {item}")
                for item in req.get("unresolved", []):
                    st.caption(f"Unresolved · {item}")
        if cov := build.get("coverage"):
            cov_rows = [
                f'<tr><td><strong>{escape(topic)}</strong></td><td>{status_pill(f["status"])}</td>'
                '<td style="color:#73736C">'
                + "".join(f'<div><code>{escape(e["id"])}</code> · {escape(e["quote"][:260])}</div>'
                          for e in f.get("evidence", []))
                + escape(f.get("limitation", "")) + '</td></tr>'
                for topic, f in cov.items()
            ]
            st.html(
                '<div class="forge-table-wrap" style="margin-bottom:1rem"><table class="forge-table">'
                '<thead><tr><th>Topic</th><th>Groundability</th><th>Evidence / Limitation</th></tr></thead>'
                f'<tbody>{"".join(cov_rows)}</tbody></table></div>'
            )
        with st.form(f"{build_id}-approval"):
            if req.get("original_brief"):
                st.caption("Original requester brief")
                st.text(req["original_brief"])
            if req.get("behavior"):
                st.caption("Requested behavior · " + " · ".join(req["behavior"]))
            scope = st.text_area("Scope", req["scope"])
            col1, col2 = st.columns(2)
            audience = col1.text_input("Audience", req["audience"])
            tone = col2.text_input("Tone", req["tone"])
            col3, col4 = st.columns(2)
            allowed = col3.text_area("Must answer (one topic per line)", "\n".join(req["must_answer"]))
            refused = col4.text_area("Must refuse (one topic per line)", "\n".join(req["must_refuse"]))
            if st.form_submit_button("Accept limitations & generate agent", type="primary"):
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
        if build["stages"][3]["status"] == "completed":
            detail = api("runs", build["run_id"])
            if (detail.get("run_metadata") or {}).get("status") == "incomplete":
                mode = "scoring" if detail.get("eval_dataset") else "generation"
                if st.button("Resume failed evaluation stage", type="primary"):
                    api("runs", build["run_id"], "resume", json={"mode": mode})
                    st.session_state.pop("build_snapshot", None)
                    st.rerun()
        elif st.button("Retry failed build stage", type="primary"):
            api("builds", build_id, "retry", json={})
            st.session_state.pop("build_snapshot", None)
            st.rerun()
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
    outcome = answer.get("outcome") or ("insufficient_evidence" if answer.get("refused") else "grounded")
    labels = {"grounded": "Grounded answer", "clarification": "Clarification required",
              "insufficient_evidence": "Insufficient evidence", "out_of_scope": "Out of scope",
              "partial": "Partial answer", "tool_assisted": "Tool-assisted answer", "ungrounded": "Grounding off"}
    if answer:
        st.caption(labels.get(outcome, outcome))
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
    if isinstance(conversations.get(run_id), list):
        conversations[run_id] = {"id": uuid4().hex, "messages": conversations[run_id]}
    conversation = conversations.setdefault(run_id, {"id": uuid4().hex, "messages": []})

    def reset_chat():
        conversations[run_id] = {"id": uuid4().hex, "messages": []}

    actions.button("New chat", use_container_width=True, on_click=reset_chat)
    history = conversation["messages"]
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
                    cited = passage["id"] in (latest.get("answer") or {}).get("citations", [])
                    with st.expander(f'{passage["id"]} · {"Cited" if cited else "Retrieved"}'):
                        st.text(passage["text"])
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
        st.info("Document grounding is off. Current questions will not be checked against policy documents.")

    with chat:
        st.markdown(f'**{run_id}**')
        st.caption(f'Model · {model or config["model"]}')
        st.html(f'<div class="forge-subtitle" style="margin-bottom:0.75rem">{escape(config["requirements"]["scope"])}</div>')
        with st.container(height=360, border=False):
            if not history:
                st.caption("Ask an in-scope, out-of-scope, or tool-backed question to test this agent.")
            for question, trace in history:
                st.chat_message("user").write(question)
                with st.chat_message("assistant"):
                    show_trace(trace, show_evidence=not show_grounding)
        if prompt := st.chat_input("Ask a question...", max_chars=2000, key=f'chat-{conversation["id"]}'):
            question = prompt.strip()
            if question:
                with st.spinner("Retrieving evidence and generating response..."):
                    previous = [{"question": q, "clarification": (t["answer"]["answer"][:1000]
                                 if (t.get("answer") or {}).get("outcome") == "clarification" else None)}
                                for q, t in history[-6:] if t.get("grounding", True)]
                    trace = api("runs", run_id, "chat", json={"question": question, "model": model,
                                "history": previous, "conversation_id": conversation["id"], "grounding": show_grounding},
                                timeout=240)
                if conversations[run_id]["id"] == trace.get("conversation_id"):
                    history.append((question, trace))
                    st.rerun()


# ---------------------------------------------------------------------------
# 4. Evaluations
# ---------------------------------------------------------------------------

def _dim_pill(label: str, ok: bool | None) -> str:
    if ok is True:
        return f'<span class="forge-pill forge-pill-success">✓ {escape(label)}</span>'
    if ok is False:
        return f'<span class="forge-pill forge-pill-red">✗ {escape(label)}</span>'
    return f'<span class="forge-pill forge-pill-neutral">— {escape(label)}</span>'


def _breakdown_bar(passed: int, failed: int, error: int, total: int) -> str:
    if total <= 0:
        return ""
    p_w = (passed / total) * 100
    f_w = (failed / total) * 100
    e_w = (error / total) * 100
    return (
        '<div style="margin:0.5rem 0 0.35rem">'
        '<div style="display:flex;height:14px;border-radius:6px;overflow:hidden;border:1px solid #E3DFD6;background:#F2F0E9">'
        f'<div style="width:{p_w:.2f}%;background:#357A57" title="Passed: {passed}"></div>'
        f'<div style="width:{f_w:.2f}%;background:#B43C32" title="Failed: {failed}"></div>'
        f'<div style="width:{e_w:.2f}%;background:#8C8982" title="Infrastructure error: {error}"></div>'
        '</div>'
        '<div style="display:flex;gap:1.25rem;font-size:0.76rem;color:#73736C;margin-top:0.35rem">'
        f'<span><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:#357A57;margin-right:4px"></span>Passed: {passed}</span>'
        f'<span><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:#B43C32;margin-right:4px"></span>Failed: {failed}</span>'
        f'<span><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:#8C8982;margin-right:4px"></span>Infrastructure errors: {error}</span>'
        '</div></div>'
    )


def evaluations():
    heading, control = st.columns([3.2, 1.3], vertical_alignment="center")
    with heading:
        st.header("Agent evaluation")
        st.html('<div class="forge-subtitle">Automated tests to verify accuracy, grounding, and refusal adherence.</div>')
    with control:
        run_id = choose_run("evaluation-run")
    st.query_params["run"] = run_id

    detail = api("runs", run_id)
    metadata = detail.get("run_metadata") or {}
    status = metadata.get("status", "prototype")
    is_replay = bool(metadata.get("source_run"))
    run_kind_label = (
        f'Frozen replay experiment (source: {metadata["source_run"]})'
        if is_replay
        else "Autonomous optimization run"
    )
    st.html(
        f'<div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.5rem">'
        f'{status_pill("neutral" if is_replay else "completed", run_kind_label)}'
        f'{status_pill(status, readable_status(status))}'
        f'</div>'
    )
    if reason := metadata.get("stop_reason"):
        st.caption(f"Stop reason: {reason}")
    if status == "incomplete":
        mode = "scoring" if detail.get("eval_dataset") else "generation"
        if st.button(f"Resume {mode}", type="primary"):
            result = api("runs", run_id, "resume", json={"mode": mode})
            st.success(f'Resume requested · {result["status"]}')

    cards = detail["scorecards"]
    results = detail.get("case_results") or {}
    selected_v = metadata.get("selected_version")
    if cards:
        card = next((c for c in cards if c["version"] == selected_v), cards[0])
        grounded = card.get("dimensions", {}).get("grounded")
        g_rate = f'{grounded["passed"] / grounded["scored"]:.0%}' if grounded and grounded["scored"] else "—"
        g_sub = f'{grounded["passed"]}/{grounded["scored"]} scored cases' if grounded and grounded["scored"] else "No scored cases"
        ver_label = f'Selected version (v{card["version"]})' if selected_v is not None else f'Baseline version (v{card["version"]})'

        left, right = st.columns(2)
        left.html(
            f'<div class="forge-metric-card">'
            f'  <div>'
            f'    <div class="forge-metric-label">{escape(ver_label)}</div>'
            f'    <div class="forge-metric-value">{card["passed"]} / {card["total"]} tests passed</div>'
            f'    <div class="forge-metric-sub">{card["failed"]} failed · {card["error"]} infrastructure errors</div>'
            f'  </div>'
            f'  <span class="score-badge">{card["pass_rate"]:.0%}</span>'
            f'</div>'
        )
        right.html(
            f'<div class="forge-metric-card">'
            f'  <div>'
            f'    <div class="forge-metric-label">Grounding ({escape(ver_label)})</div>'
            f'    <div class="forge-metric-value">{g_rate} grounded</div>'
            f'    <div class="forge-metric-sub">{g_sub}</div>'
            f'  </div>'
            f'</div>'
        )

    cases_tab, metrics_tab, optimization_tab = st.tabs(["Test cases", "Metrics", "Optimization log"])

    with cases_tab:
        if results:
            version_keys = list(results)
            default_vk = f"v{selected_v}" if selected_v is not None and f"v{selected_v}" in results else version_keys[0]
            f1, f2, f3, f4 = st.columns([1.1, 1, 1, 1.5])
            version = f1.selectbox(
                "Agent version",
                version_keys,
                index=version_keys.index(default_vk),
                format_func=lambda k: f"Version {k.removeprefix('v')}" + (" (Selected)" if selected_v is not None and k == f"v{selected_v}" else ""),
                key=f"version-{run_id}",
            )
            outcome_filter = f2.selectbox("Status", ["All", "passed", "failed", "error"])
            categories = sorted({item["case"]["category"] for item in results[version]})
            category_filter = f3.selectbox("Category", ["All", *categories])
            search_q = f4.text_input("Search", placeholder="Search test cases...", label_visibility="collapsed")

            st.caption(f'Showing test cases for **Version {version.removeprefix("v")}**')
            rows_shown = 0
            for item in results[version]:
                case = item["case"]
                if outcome_filter not in ("All", item["status"]) or category_filter not in ("All", case["category"]):
                    continue
                if search_q.strip() and search_q.strip().lower() not in f'{case["id"]} {case["question"]}'.lower():
                    continue
                rows_shown += 1
                judgment = item.get("judgment") or {}
                grounded_flag = judgment.get("grounded")
                g_text = "Grounded" if grounded_flag else (item.get("failure") or "Ungrounded")
                with st.expander(f'{case["id"]} · {case["category"]} · {item["status"].upper()} · {case["question"]}'):
                    # 1. Judge summary & dimension pills
                    top_l, top_r = st.columns([1, 3])
                    top_l.html(f'{status_pill(item["status"], item["status"].capitalize())}<div style="margin-top:0.35rem">{status_pill(g_text)}</div>')
                    top_r.markdown(f'**Judge explanation:** {item["explanation"]}')
                    if judgment:
                        dims = "".join([
                            _dim_pill("Correct", judgment.get("correct")),
                            _dim_pill("Grounded", judgment.get("grounded")),
                            _dim_pill("Citations", judgment.get("citations_relevant")),
                            _dim_pill("Refusal", judgment.get("refusal_appropriate")),
                            _dim_pill("Tools", judgment.get("tools_correct")),
                        ])
                        st.html(f'<div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin:0.35rem 0 0.6rem">{dims}</div>')

                    # 2. Expected vs Actual readable columns
                    exp_col, act_col = st.columns(2)
                    with exp_col.container(border=True):
                        st.markdown("**Expected**")
                        expected = ("Clarification" if case.get("category") == "ambiguous" else
                                    "Partial answer" if case.get("behavior") == "mixed_scope" else
                                    "Refusal" if case.get("expected_refusal") else "Grounded answer")
                        st.caption(f'Expected outcome: {expected}' + (f' · Tools: {", ".join(case["expected_tools"])}' if case.get("expected_tools") else ""))
                        for turn in case.get("history", []):
                            st.text(f'Previous question: {turn["question"]}')
                            if turn.get("clarification"):
                                st.text(f'Clarification: {turn["clarification"]}')
                        if case.get("expected_facts"):
                            for fact in case["expected_facts"]:
                                st.markdown(f'- `{fact["source_id"]}`: {fact["fact"]}')
                        else:
                            st.caption("No factual claims expected (should refuse or ask for clarification).")

                    with act_col.container(border=True):
                        st.markdown("**Actual response**")
                        execution = item.get("execution") or {}
                        ans = execution.get("answer") or {}
                        st.write(ans.get("answer") or execution.get("error") or "No answer produced.")
                        if ans.get("refused"):
                            st.caption("Agent refused / requested clarification")
                        if ans.get("citations"):
                            chips = "".join(f'<span class="forge-source-chip">{escape(c)}</span>' for c in ans["citations"])
                            st.html(f'<div><span style="font-size:0.75rem;color:#73736C">Citations:</span> {chips}</div>')

                    # 3. Tool execution (inputs & outputs) + Retrieved document evidence
                    execution = item.get("execution") or {}
                    tools_used = execution.get("tools") or []
                    retrieved = execution.get("retrieved") or []
                    if tools_used or retrieved:
                        t_col, r_col = st.columns(2)
                        with t_col:
                            st.markdown("**Tool execution**")
                            if tools_used:
                                for tool in tools_used:
                                    with st.container(border=True):
                                        st.markdown(f'**`{tool["name"]}`**')
                                        st.caption(f'Inputs: `{tool.get("arguments", {})}`')
                                        for rk, rv in (tool.get("results") or {}).items():
                                            st.markdown(f'Output (`{rk}`): `{rv}`')
                            else:
                                st.caption("No tools called.")
                        with r_col:
                            st.markdown(f'**Retrieved evidence ({len(retrieved)})**')
                            if retrieved:
                                for passage in retrieved:
                                    with st.container(border=True):
                                        st.markdown(f'`{passage["id"]}`')
                                        st.caption(passage["text"][:260] + ("…" if len(passage["text"]) > 260 else ""))
                            else:
                                st.caption("No passages retrieved.")

                    # 4. Technical raw JSON (collapsed by default)
                    with st.expander("Raw JSON (expected, execution, judgment)"):
                        st.json({"expected": case, "execution": execution, "judgment": judgment})
            if not rows_shown:
                st.info("No test cases match the current filters.")
        else:
            st.info("No scored cases yet.")
        if dataset := detail.get("eval_dataset"):
            with st.expander("Frozen evaluation dataset (raw JSON)"):
                st.json(dataset, expanded=False)

    with metrics_tab:
        if cards:
            st.subheader("Evaluation breakdown")
            if len(cards) == 1:
                c = cards[0]
                st.caption(f'Version v{c["version"]} ({c["total"]} total cases)')
                st.html(_breakdown_bar(c["passed"], c["failed"], c["error"], c["total"]))
            else:
                st.caption(f'Baseline (v{cards[0]["version"]}) vs optimization iterations ({len(cards)} versions)')
                chart_rows = [
                    {
                        "Version": f'v{c["version"]}',
                        "Passed": c["passed"],
                        "Failed": c["failed"],
                        "Infrastructure errors": c["error"],
                    }
                    for c in cards
                ]
                st.bar_chart(
                    chart_rows,
                    x="Version",
                    y=["Passed", "Failed", "Infrastructure errors"],
                    color=["#357A57", "#B43C32", "#8C8982"],
                )

            table_rows = [
                {
                    "Agent Version": f'v{c["version"]}' + (" (Selected)" if selected_v == c["version"] else ""),
                    "Passed": c["passed"],
                    "Failed": c["failed"],
                    "Infra Errors": c["error"],
                    "Total Cases": c["total"],
                    "Pass Rate": f'{c["pass_rate"]:.0%}',
                    "Duration (s)": round(c.get("seconds", 0), 1),
                }
                for c in cards
            ]
            st.dataframe(table_rows, hide_index=True, use_container_width=True)

            dim_rows = []
            for c in cards:
                row = {"Agent Version": f'v{c["version"]}'}
                for dk, dv in (c.get("dimensions") or {}).items():
                    label = dk.replace("_", " ").capitalize()
                    row[label] = f'{dv["passed"]}/{dv["scored"]} ({dv["passed"]/dv["scored"]:.0%})' if dv.get("scored") else "—"
                dim_rows.append(row)
            if dim_rows:
                st.markdown("**Dimension breakdown**")
                st.dataframe(dim_rows, hide_index=True, use_container_width=True)
        else:
            st.info("No scorecards yet.")

    with optimization_tab:
        if results:
            opt_v = next(iter(results))
            st.subheader(f'Failure classification (Version {opt_v.removeprefix("v")})')
            counts = Counter(item.get("failure") for item in results[opt_v] if item.get("failure"))
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
                base_k = f'v{step["base_version"]}'
                iter_k = f'v{step["iteration"]}'
                with st.container(border=True):
                    top_l, top_r = st.columns([3, 1], vertical_alignment="center")
                    top_l.markdown(f'**Iteration {step["iteration"]}** (`{base_k}` → `{iter_k}`)')
                    top_r.html(status_pill(step.get("outcome", "unmeasured")))
                    st.write(step["reason"])
                    before = step.get("before", {})
                    after = step.get("after", {})
                    st.caption(
                        f'Before ({base_k}): {before.get("passed", "?")}/{before.get("total", "?")} ({before.get("pass_rate", 0):.0%})'
                        + (f' → After ({iter_k}): {after.get("passed", "?")}/{after.get("total", "?")} ({after.get("pass_rate", 0):.0%})' if after else "")
                        + f' · Targeted cases: {", ".join(step.get("affected_case_ids", [])) or "None"}'
                    )

                    # Real before/after case comparison when both versions exist
                    if base_k in results and iter_k in results:
                        base_map = {r["case"]["id"]: r["status"] for r in results[base_k]}
                        iter_map = {r["case"]["id"]: r["status"] for r in results[iter_k]}
                        newly_passed = [cid for cid, st_v in iter_map.items() if st_v == "passed" and base_map.get(cid) != "passed"]
                        regressions = [cid for cid, st_v in iter_map.items() if st_v != "passed" and base_map.get(cid) == "passed"]
                        remaining = [cid for cid, st_v in iter_map.items() if st_v != "passed"]
                        c1, c2, c3 = st.columns(3)
                        c1.caption(f'**Newly passed ({len(newly_passed)}):** {", ".join(newly_passed) or "None"}')
                        c2.caption(f'**Regressions ({len(regressions)}):** {", ".join(regressions) or "None"}')
                        c3.caption(f'**Remaining failures ({len(remaining)}):** {", ".join(remaining) or "None"}')

                    # Before / After prompt or config diff
                    for field, diff in (step.get("changes") or {}).items():
                        st.markdown(f'**Changed `{field}`**')
                        if isinstance(diff, dict) and "before" in diff and "after" in diff:
                            b_col, a_col = st.columns(2)
                            b_col.caption("Before")
                            b_col.code(str(diff["before"]), language=None)
                            a_col.caption("After")
                            a_col.code(str(diff["after"]), language=None)
                        else:
                            st.json(diff)
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
