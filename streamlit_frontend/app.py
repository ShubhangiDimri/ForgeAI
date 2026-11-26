"""ForgeAI's Streamlit frontend."""
from pathlib import Path
from html import escape
from urllib.parse import urlencode

import streamlit as st

from api_client import APIError, endpoint, request


def api(*segments: str, **kwargs):
    return request(endpoint(*segments), **kwargs)


def models(providers, configured_only=False):
    return list(dict.fromkeys(model for p in providers
                              if p["configured"] or not configured_only for model in p["models"]))


def choose_run(key):
    runs = api("runs")["runs"]
    if not runs:
        st.info("Build an agent to create your first run.")
        st.stop()
    labels = {run["id"]: f'{run["id"]} · {run["status"]}' for run in runs}
    ids = list(labels)
    preferred = st.query_params.get("run") or st.session_state.get("preferred_run")
    return st.selectbox("Agent run", ids, index=ids.index(preferred) if preferred in labels else 0,
                        format_func=labels.__getitem__, key=key)


def overview():
    heading, action = st.columns([4, 1])
    with heading:
        st.header("Your workspace")
        st.caption("Generated agents, evaluation scorecards, and demonstration artifacts.")
    with action:
        st.page_link(build_page, label="Build new agent", icon=":material/add:")
    runs = api("runs")["runs"]
    if runs:
        rows = []
        for run in runs:
            rate = run["selected_pass_rate"]
            score = f'{rate:.0%} ({run["total_cases"]} cases)' if rate is not None else "—"
            query = urlencode({"run": run["id"]})
            actions = " ".join(f'<a href="{page.url_path}?{query}">{label}</a>' for page, label in (
                (playground_page, "Playground"), (evaluations_page, "Eval"), (reports_page, "Reports")))
            rows.append(f'<tr><td><strong>{escape(run["id"])}</strong><small>{escape(run["scope"])}</small></td>'
                        f'<td><code>{escape(run["model"])}</code></td><td>{escape(run["status"])}</td>'
                        f'<td>{score}</td><td>{escape(run["created_at"][:10])}</td>'
                        f'<td class="run-actions">{actions}</td></tr>')
        st.html('<div class="workspace-table"><table><thead><tr><th>Agent / Run</th><th>Model</th>'
                '<th>Status</th><th>Score</th><th>Created</th><th>Actions</th></tr></thead><tbody>'
                + "".join(rows) + '</tbody></table></div>')
    else:
        with st.container(border=True):
            st.info("Upload documents and provide a brief to build your first agent.")


def lines(value):
    return [line.strip() for line in value.splitlines() if line.strip()]


@st.fragment(run_every=3)
def build_progress(build_id):
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
    if stages:
        st.progress(sum(s["status"] == "completed" for s in stages) / len(stages),
                    text=build["current_stage"] or status)
    with st.expander("Build stages", expanded=status == "failed"):
        for stage in stages:
            st.text(f'{stage["name"]} · {stage["status"]} {stage["detail"]}'.rstrip())
    if status == "running":
        return
    st.session_state["build_snapshot"] = build
    if status in {"failed", "completed"}:
        st.session_state["preferred_run"] = build["run_id"]
    st.rerun()


def show_checkpoint(build):
    build_id = build["build_id"]
    status = build["status"]
    if status == "waiting_intake":
        st.subheader("Clarifying questions")
        with st.form(f"{build_id}-intake"):
            answers = [st.text_input(q, key=f"{build_id}-answer-{i}")
                       for i, q in enumerate(build["questions"])]
            if st.form_submit_button("Continue", type="primary"):
                api("builds", build_id, "intake", json={"answers": answers})
                st.session_state.pop("build_snapshot", None)
                st.rerun()
    elif status == "waiting_approval":
        req = build["requirements"]
        st.subheader("Review requirements")
        if build.get("coverage"):
            st.json(build["coverage"], expanded=False)
        with st.form(f"{build_id}-approval"):
            scope = st.text_area("Scope", req["scope"])
            audience = st.text_input("Audience", req["audience"])
            tone = st.text_input("Tone", req["tone"])
            allowed = st.text_area("Must answer (one topic per line)", "\n".join(req["must_answer"]))
            refused = st.text_area("Must refuse (one topic per line)", "\n".join(req["must_refuse"]))
            if st.form_submit_button("Approve requirements", type="primary"):
                revised = req | {"scope": scope.strip() or req["scope"], "audience": audience,
                                 "tone": tone, "must_answer": lines(allowed), "must_refuse": lines(refused)}
                api("builds", build_id, "approve", json={"requirements": revised})
                st.session_state.pop("build_snapshot", None)
                st.rerun()
    elif status == "failed":
        st.error(build.get("error") or "Build failed.")
        st.caption(f'Run · {build["run_id"]}')
        st.page_link(evaluations_page, label="Open evaluations")
    elif status == "completed":
        st.success(f'Agent ready · {build["run_id"]}')
        st.page_link(playground_page, label="Open Playground")
        st.page_link(reports_page, label="Open Reports")


def build_agent():
    st.caption("Agents / New")
    st.header("Create an agent")
    st.caption("Define the task, provide a knowledge source, and let ForgeAI build a grounded, evaluated agent.")
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
    providers = api("providers")["providers"]
    presets = {item["id"]: item for item in examples["briefs"]}
    datasets = {item["id"]: item["files"] for item in examples["datasets"]}
    with st.form("build-agent", border=False):
        left, right = st.columns(2)
        name = left.text_input("Agent name", max_chars=60)
        model = right.selectbox("Model", ["auto", *models(providers)],
                                format_func=lambda item: "Automatic fallback" if item == "auto" else item)
        example = st.selectbox("Example brief", [None, *presets],
                               format_func=lambda item: presets[item]["label"] if item else "Write your own")
        if st.form_submit_button("Load example brief", disabled=not presets) and example:
            st.session_state["brief-template"] = presets[example]["brief"]
        brief = st.text_area("Requester brief", st.session_state.get("brief-template", ""), max_chars=4000)
        uploads, examples_column = st.columns(2)
        files = uploads.file_uploader("Upload documents", type=["pdf", "csv", "txt"], accept_multiple_files=True)
        selected = examples_column.selectbox("Or use a demo dataset", [None, *datasets],
                                            format_func=lambda item: item or "Choose a dataset")
        st.divider()
        budget, intake, scope, submit = st.columns([1.3, 1.8, 1, 1], vertical_alignment="center")
        iterations = budget.number_input("Max iterations", 0, 3, 1)
        interactive = intake.checkbox("Interactive intake")
        prototype = scope.checkbox("Prototype only")
        if submit.form_submit_button("Build agent", type="primary"):
            if len(brief.strip()) < 10 or not (files or selected) or (files and selected):
                st.error("Enter a brief of at least 10 characters and choose documents.")
                return
            payload = {"name": name.strip(), "brief": brief.strip(), "model": model,
                       "interactive": interactive, "prototype_only": prototype, "max_iterations": iterations}
            if files:
                parts = [("files", (file.name, file.getvalue(), file.type)) for file in files]
                payload["upload_id"] = api("uploads", files=parts, timeout=90)["upload_id"]
            else:
                payload["demo_dataset"] = selected
            st.session_state["build_id"] = api("builds", json=payload)["build_id"]
            st.rerun()


def show_trace(trace, *, show_evidence=True):
    answer = trace.get("answer") or {}
    st.write(answer.get("answer", "No answer was returned."))
    if answer.get("refused"):
        st.caption("Refused or clarification requested")
    if answer.get("citations"):
        st.caption("Sources · " + " · ".join(answer["citations"]))
    if trace.get("model"):
        st.caption(trace["model"])
    if show_evidence and (trace.get("retrieved") or trace.get("tools")):
        with st.expander("Grounding and tool activity"):
            for passage in trace.get("retrieved", []):
                st.text(passage["id"])
                st.text(passage["text"])
            for tool in trace.get("tools", []):
                st.json(tool, expanded=False)


def playground():
    title, run_control, model_control, actions = st.columns([1.5, 2, 2, 1.4], vertical_alignment="center")
    title.header("Interactive chat")
    with run_control:
        run_id = choose_run("chat-run")
    with model_control:
        options = [None, *models(api("providers")["providers"], configured_only=True)]
        model = st.selectbox("Chat model", options, format_func=lambda item: item or "Saved run model")
    detail = api("runs", run_id)
    config = detail["agent_config"]
    conversations = st.session_state.setdefault("conversations", {})
    history = conversations.setdefault(run_id, [])
    if actions.button("New conversation"):
        history.clear()
    actions.toggle("Grounding", value=True, key="chat-grounding")
    st.divider()
    if st.session_state["chat-grounding"]:
        chat, grounding = st.columns([3, 1.05], gap="medium")
        with grounding.container(key="grounding-panel"):
            st.subheader("Grounding")
            latest = history[-1][1] if history else {}
            with st.container(border=True):
                manifest = detail.get("document_manifest") or config.get("document_manifest") or {}
                st.caption(f"{len(manifest)} documents")
                st.code(latest.get("model") or model or config["model"], language=None)
            sources = latest.get("retrieved", [])
            if sources:
                st.markdown(f"**Retrieved sources ({len(sources)})**")
                for passage in sources:
                    with st.container(border=True):
                        st.text(passage["id"])
                        st.caption(passage["text"][:240])
            if latest.get("tools"):
                with st.expander("Tool activity"):
                    st.json(latest["tools"])
            with st.expander("Configuration"):
                st.json(config["settings"])
    else:
        chat = st.container()
    with chat:
        st.markdown(f"**{run_id}**")
        st.caption(config["requirements"]["scope"])
        with st.container(height=470, border=False):
            for question, trace in history:
                st.chat_message("user").write(question)
                with st.chat_message("assistant"):
                    show_trace(trace, show_evidence=not st.session_state["chat-grounding"])
        if prompt := st.chat_input("Ask a question…", max_chars=2000):
            question = prompt.strip()
            if question:
                with st.spinner("Retrieving evidence and generating an answer…"):
                    trace = api("runs", run_id, "chat", json={"question": question, "model": model}, timeout=240)
                history.append((question, trace))
                st.rerun()


def evaluations():
    heading, control = st.columns([3, 1], vertical_alignment="center")
    with heading:
        st.header("Agent evaluation")
        st.caption("Automated tests to verify accuracy, grounding, and refusal adherence.")
    with control:
        run_id = choose_run("evaluation-run")
    detail = api("runs", run_id)
    metadata = detail.get("run_metadata") or {}
    status = metadata.get("status", "prototype")
    if reason := metadata.get("stop_reason"):
        st.caption(reason)
    if status == "incomplete":
        mode = "scoring" if detail.get("eval_dataset") else "generation"
        if st.button(f"Resume {mode}", type="primary"):
            result = api("runs", run_id, "resume", json={"mode": mode})
            st.success(f'Resume requested · {result["status"]}')
    if status == "running":
        st.button("Refresh results")
    cards = detail["scorecards"]
    if cards:
        card = next((c for c in cards if c["version"] == metadata.get("selected_version")), cards[0])
        left, right = st.columns(2)
        with left.container(border=True):
            st.caption(f'Selected version (v{card["version"]})')
            st.markdown(f'**{card["passed"]} / {card["total"]} tests passed**')
            st.caption(f'{card["failed"]} failed · {card["error"]} infrastructure errors')
            st.html(f'<span class="score-badge">{card["pass_rate"]:.0%}</span>')
        with right.container(border=True):
            st.caption("Grounding")
            grounded = card.get("dimensions", {}).get("grounded")
            if grounded and grounded["scored"]:
                st.markdown(f'**{grounded["passed"] / grounded["scored"]:.0%} grounded**')
                st.caption(f'{grounded["passed"]}/{grounded["scored"]} scored cases')
            else:
                st.markdown("—")
    cases_tab, metrics_tab, optimization_tab = st.tabs(["Test cases", "Metrics", "Optimization log"])
    with cases_tab:
        if results := detail["case_results"]:
            iteration, outcome, category = st.columns(3)
            version = iteration.selectbox("Iteration", list(results), key=f"version-{run_id}")
            outcome_filter = outcome.selectbox("Filter case status", ["All", "passed", "failed", "error"])
            categories = sorted({item["case"]["category"] for item in results[version]})
            category_filter = category.selectbox("Category", ["All", *categories])
            for item in results[version]:
                case = item["case"]
                if outcome_filter not in ("All", item["status"]) or category_filter not in ("All", case["category"]):
                    continue
                with st.expander(f'{case["id"]} · {item["status"]} · {case["question"]}'):
                    st.text(item["explanation"])
                    show_trace(item["execution"])
                    st.json({"expected": case, "judgment": item.get("judgment")}, expanded=False)
        else:
            st.info("No scored cases yet.")
        if dataset := detail.get("eval_dataset"):
            with st.expander("Frozen evaluation dataset"):
                st.json(dataset, expanded=False)
    with metrics_tab:
        if cards:
            st.dataframe([{k: v for k, v in card.items() if k != "dimensions"} for card in cards],
                         hide_index=True, width="stretch")
            st.json({f'v{c["version"]}': c["dimensions"] for c in cards}, expanded=False)
        else:
            st.info("No scorecards yet.")
    with optimization_tab:
        if logs := detail["iteration_logs"]:
            for step in logs:
                with st.container(border=True):
                    st.markdown(f'**Iteration {step["iteration"]}**')
                    st.text(step["reason"])
                    st.json(step, expanded=False)
        else:
            st.info("No optimization iterations recorded.")


def reports():
    heading, control = st.columns([3, 1], vertical_alignment="center")
    with heading:
        st.header("Reports")
        st.caption("Inspect and download generated definitions, scorecards, and quality reports.")
    with control:
        run_id = choose_run("report-run")
    detail = api("runs", run_id)
    menu, preview = st.columns([1, 3])
    formats = {"final_report": "Final quality report", "agent_config": "Agent definition",
               "requirements": "Requirements", "coverage": "Groundability", "scorecards": "Scorecards"}
    with menu:
        with st.container(border=True):
            selected = st.radio("Preview", list(formats), format_func=formats.__getitem__)
        with st.container(border=True):
            files = ["All artifacts (ZIP)", *[f["name"] for f in detail["files"]]]
            filename = st.selectbox("Files", files)
            zip_file = filename == files[0]
            if st.button("Prepare ZIP" if zip_file else "Prepare download", type="primary"):
                path = ("download-zip",) if zip_file else ("artifacts", filename)
                data = api("runs", run_id, *path, binary=True, timeout=90)
                st.session_state["download"] = (run_id, filename, data)
            download = st.session_state.get("download")
            if download and download[:2] == (run_id, filename):
                st.download_button("Download ZIP" if zip_file else "Download", download[2],
                                   file_name=f"{run_id}-artifacts.zip" if zip_file else filename,
                                   mime="application/zip" if zip_file else "application/octet-stream")
    with preview.container(border=True):
        if selected == "final_report":
            if report := detail.get(selected):
                st.markdown(report)
            else:
                st.info("This run has no final quality report.")
        else:
            st.json(detail.get(selected) or {})


def settings():
    st.header("Settings")
    st.caption("Backend provider configuration and fallback order. API credentials remain on the backend.")
    data = api("providers")
    with st.container(key="settings-content"):
        with st.container(border=True):
            for i, provider in enumerate(data["providers"]):
                if i:
                    st.divider()
                label, status = st.columns([3, 1], vertical_alignment="center")
                label.markdown(f'**{provider["name"]}**')
                label.caption(provider["default_model"])
                status.caption("Configured" if provider["configured"] else "Not configured")
        with st.container(border=True):
            st.text("Fallback order: " + " → ".join(data["fallback_order"]))
            st.text(f'Default embedding: {data["default_embedding"]}')


def docs():
    st.header("Documentation")
    st.caption("Architecture, CLI commands, and local development workflow.")
    with st.container(key="docs-content"):
        with st.container(border=True):
            st.markdown("**Backend API**")
            st.code("cd backend\npython -m uvicorn api.main:app --reload --port 8000", language="bash")
            st.markdown("**Frontend Dev**")
            st.code("python -m streamlit run streamlit_frontend/app.py", language="bash")
            st.markdown("**CLI Commands**")
            st.code("cd backend\npython -m pytest -q\n"
                    "python -m forgeai chat --config artifacts/groq-academic-final/agent_config.json\n"
                    "python -m forgeai evaluate --resume-scoring --run artifacts/groq-academic-final",
                    language="bash")


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
build_page = st.Page(build_agent, title="Build Agent", url_path="build", icon=":material/add_circle:")
playground_page = st.Page(playground, title="Playground", icon=":material/chat:")
evaluations_page = st.Page(evaluations, title="Evaluations", icon=":material/fact_check:")
reports_page = st.Page(reports, title="Reports", icon=":material/description:")
main_pages = [st.Page(overview, title="Overview", default=True, icon=":material/dashboard:"),
              build_page, playground_page, evaluations_page, reports_page]
secondary_pages = [st.Page(settings, title="Settings", url_path="settings", icon=":material/settings:"),
                   st.Page(docs, title="Documentation", url_path="docs", icon=":material/menu_book:")]
navigation = st.navigation([*main_pages, *secondary_pages], position="hidden")
with st.sidebar:
    st.markdown('<div class="forge-brand"><span></span>ForgeAI</div>', unsafe_allow_html=True)
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
