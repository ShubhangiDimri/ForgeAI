from unittest.mock import Mock
import pytest
from forgeai.coverage import Assessment, assess
from forgeai.intake import interview
from forgeai.schema import Finding, Passage, Questions, Requirements


def requirements():
    return Requirements(scope="Catalog", audience="Buyers", tone="Brief", must_answer=["dimensions"],
                        must_refuse=[], assumptions=[], unresolved=[])


@pytest.mark.parametrize("number,status", [(1, "partial"), (9, "unsupported")])
def test_mocked_partial_and_invented_evidence(number, status):
    passages = [Passage(id="spec#p1:c1", file="spec", text="width 10 cm")]
    model = Mock()
    model.ask.return_value = Assessment(status="partial", sentence_numbers=[number],
                                     limitation="Height is missing")
    index = Mock()
    index.search.return_value = passages
    result = assess(requirements(), index, model)["dimensions"]
    assert result.status == status
    assert bool(result.evidence) == (status == "partial")


def test_mocked_interactive_clarification(monkeypatch):
    model = Mock()
    model.ask.side_effect = [Questions(questions=["Which audience?", "Which audience?"]), requirements()]
    replies = []
    def reply(question):
        replies.append(question)
        return "Buyers"
    monkeypatch.setattr("builtins.input", reply)
    result = interview("Catalog", [Passage(id="1", file="spec", text="width 10 cm")], False, model)
    assert len(replies) == 1
    assert model.ask.call_args.args[1]["user_answers"] == {"Which audience?": "Buyers"}
    assert not result.unresolved



def test_relevance_filter_needs_brief_capability():
    from forgeai.schema import Selection
    from forgeai.tools import select_tools
    proposals = [Selection(name=n, reason="Proposed by the model") for n in
                 ["current_date", "calculator", "csv_lookup"]]
    assert select_tools(proposals, "Explain attendance requirements") == []
    assert [t.name for t in select_tools(proposals, "Calculate totals from a catalog lookup")] == [
        "calculator", "csv_lookup"]


def test_coverage_distinguishes_fallback_evidence_from_absence():
    record = Passage(id="spec#p1:c1", file="spec", text="width 10 cm")
    index = Mock()
    index.search.return_value = []
    index.passages = [record]
    model = Mock()
    model.ask.return_value = Assessment(status="supported", sentence_numbers=[1], limitation="")
    found = assess(requirements(), index, model)["dimensions"]
    assert found.status == "supported" and found.retrieval_miss and not found.inconclusive
    model.ask.return_value = Assessment(status="unsupported", sentence_numbers=[], limitation="Absent")
    absent = assess(requirements(), index, model)["dimensions"]
    assert not absent.retrieval_miss and not absent.inconclusive
    index.passages = [record.model_copy(update={"text": "word " * 2000})]
    uncertain = assess(requirements(), index, model)["dimensions"]
    assert uncertain.inconclusive and uncertain.retrieval_miss


def test_tabular_coverage_checks_real_lookup_and_arithmetic_inputs():
    from forgeai.coverage import tabular_support
    row = Passage(id="catalog.csv#r1:c1", file="catalog.csv", text="sku=AB1 | price=2.5",
                  cells={"sku": "AB1", "price": "2.5"})
    assert tabular_support("SKU lookup", [row]).status == "supported"
    assert tabular_support("Calculate order subtotals", [row]).status == "partial"
    assert tabular_support("Customer name lookup", [row]) is None
