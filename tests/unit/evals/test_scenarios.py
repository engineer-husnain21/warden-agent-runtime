from evals.runner import select_scenarios
from evals.scenario_loader import load_scenarios

KNOWN_SERVERS = {"warehouse", "github", "notifier"}


def test_smoke_scenarios_when_selected_cover_every_area_in_8_to_10_runs() -> None:
    smoke = select_scenarios(load_scenarios(), tag="smoke")

    assert 8 <= len(smoke) <= 10  # CI budget on the Groq free tier (docs/adr/0004)
    assert {scenario.id.split("_")[0] for scenario in smoke} == {
        "warehouse",
        "github",
        "notifier",
        "policy",
    }
    assert {scenario.approval for scenario in smoke} >= {"approve", "reject"}
    assert any(scenario.expect.denied for scenario in smoke)


def test_select_scenarios_when_ids_and_tag_given_applies_both() -> None:
    scenarios = load_scenarios()

    selected = select_scenarios(
        scenarios, only="warehouse_top_reasons_24h,warehouse_failed_count_24h", tag="smoke"
    )

    assert [scenario.id for scenario in selected] == ["warehouse_top_reasons_24h"]
    assert select_scenarios(scenarios) == scenarios


def test_all_scenarios_when_loaded_are_valid() -> None:
    scenarios = load_scenarios()

    assert len(scenarios) >= 30, "the plan asks for 30+ scenarios"
    for scenario in scenarios:
        expect = scenario.expect
        tools = [*expect.tools, *expect.executed, *expect.not_executed, *expect.denied]
        assert {tool.split(".")[0] for tool in tools} <= KNOWN_SERVERS, scenario.id
        # Approvals only make sense when the run can pause: a viewer is denied, an admin allowed.
        if scenario.approval != "none":
            assert scenario.role.value == "operator", scenario.id
