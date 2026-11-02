from app.schemas.agents.base_agent_output import BaseAgentOutput


class ReporterOutput(BaseAgentOutput):
    report: str
