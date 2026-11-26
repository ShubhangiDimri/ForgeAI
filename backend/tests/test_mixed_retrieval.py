"""Structured qualifiers and prose evidence must survive a compound query."""
from forgeai.retrieval import Index, exact_rows
from forgeai.runner import Runner
from forgeai.schema import Passage, Selection
from tests.test_factory import Encoder
from tests.test_full_factory import saved_config


def row(n, day, region, channel):
    cells = {"product_id": "A901", "date": day, "region": region, "channel": channel}
    return Passage(id=f"table.csv#r{n}:c1", file="table.csv", row=n,
                   cells=cells, text=" | ".join(f"{k}={v}" for k, v in cells.items()))


def test_exact_row_requires_joint_qualifiers():
    target = row(1, "2026-02-03", "GB", "mobile")
    rows = [target, row(2, "2026-02-03", "GB", "web"),
            row(3, "2026-02-03", "US", "mobile"), row(4, "2026-02-04", "GB", "mobile")]
    assert exact_rows("A901 on 3 February 2026 in GB mobile", rows) == [[target]]
    assert exact_rows("A901 on 2026-02-03 in GB mobile", rows) == [[target]]
    assert exact_rows("A901 in GB mobile", rows) == [[target], [rows[3]]]
    assert not exact_rows("A901 on 2026-02-06 in GB mobile", rows)
    assert not exact_rows("A9010", rows)


def test_preposition_does_not_match_short_region_code():
    target = row(1, "2026-02-03", "GB", "web")
    other = row(2, "2026-02-03", "IN", "web")
    assert exact_rows("A901 observations in the web channel", [target, other]) == [[target], [other]]
    assert exact_rows("A901 observations in GB web", [target, other]) == [[target]]
    assert exact_rows("A901 observations in IN web", [target, other]) == [[other]]


def test_mixed_question_retrieves_both_sources_before_routing():
    config = saved_config()
    config.settings.top_k = 2
    config.settings.min_score = 0
    config.tools = [Selection(name="csv_lookup", reason="Look up table records")]
    target = row(1, "2026-02-03", "GB", "mobile")
    wrong = row(2, "2026-02-04", "GB", "mobile")
    policy = Passage(id="rules.pdf#p1:c1", file="rules.pdf", text="Return within 14 calendar days.")
    stages = []

    class Client:
        def ask(self, stage, payload, schema):
            stages.append(stage)
            assert set(payload["evidence"]) == {target.id, policy.id}
            if stage == "route":
                assert payload["tools"] == {}
                return schema(decision="answer", reason="Two independent evidence sources")
            return schema(answer="Both requested facts are present.",
                          citations=[target.id, policy.id], refused=False)

    agent = Runner.__new__(Runner)
    agent.config, agent.corpus = config, [wrong, target, policy]
    agent.index = Index(agent.corpus, config.settings, "unused", Encoder())
    agent.model = Client()
    trace = agent.trace("3 February 2026 ko GB mobile channel par product A901 ka price? Aur return window?")
    assert trace.error is None
    assert trace.answer and set(trace.answer.citations) == {target.id, policy.id}
    assert [p.id for p in trace.retrieved] == [target.id, policy.id]
    assert stages == ["route", "answer"]


def test_repeated_identifier_retrieves_distinct_records_before_clarifying():
    config = saved_config()
    config.settings.top_k = 2
    config.settings.min_score = 1
    config.tools = [Selection(name="csv_lookup", reason="Look up table records")]
    records = [row(1, "2026-02-03", "GB", "mobile"), row(2, "2026-02-04", "US", "mobile"),
               row(3, "2026-02-05", "IN", "mobile")]

    class Client:
        def ask(self, stage, payload, schema):
            assert stage == "route"
            assert set(payload["evidence"]) == {p.id for p in records[:2]}
            assert "Found 3 exact matching table records and retrieved 2" in payload["retrieval_note"]
            assert payload["tools"] == {}
            return schema(decision="refuse", reason="Which region and date do you mean?")

    agent = Runner.__new__(Runner)
    agent.config, agent.corpus = config, records
    agent.index = Index(records, config.settings, "unused", Encoder())
    agent.model = Client()
    trace = agent.trace("What is the historical price for A901?")
    assert trace.error is None and trace.answer and trace.answer.refused
    assert "Which region and date" in trace.answer.answer
    assert trace.retrieved == records[:2]
    assert trace.tools == []


def test_repeated_identifier_leaves_room_for_a_separate_document():
    config = saved_config()
    config.settings.top_k = 3
    config.settings.min_score = 0
    config.tools = [Selection(name="csv_lookup", reason="Look up table records")]
    records = [row(1, "2026-02-03", "GB", "mobile"), row(2, "2026-02-04", "US", "mobile"),
               row(3, "2026-02-05", "IN", "mobile")]
    policy = Passage(id="rules.pdf#p1:c1", file="rules.pdf", text="Return within 14 calendar days.")

    class Client:
        def ask(self, stage, payload, schema):
            assert set(payload["evidence"]) == {records[0].id, records[1].id, policy.id}
            assert "Found 3 exact matching table records and retrieved 2" in payload["retrieval_note"]
            if stage == "route":
                return schema(decision="answer", reason="Policy supported, observation needs clarification")
            return schema(answer="Which date do you mean for the price? The return window is 14 days.",
                          citations=[policy.id], refused=False)

    agent = Runner.__new__(Runner)
    agent.config, agent.corpus = config, [*records, policy]
    agent.index = Index(agent.corpus, config.settings, "unused", Encoder())
    agent.model = Client()
    trace = agent.trace("What was the price of A901? Also what is the return window?")
    assert trace.error is None and trace.answer and not trace.answer.refused
    assert trace.answer.citations == [policy.id]
    assert trace.retrieved == [*records[:2], policy]
