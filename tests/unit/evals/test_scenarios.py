from evals.scenario_loader import load_scenarios

KNOWN_SERVERS = {"warehouse", "github", "notifier"}


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
