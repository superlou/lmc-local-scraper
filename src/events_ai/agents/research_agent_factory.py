from events_ai.agents.event_list_agent import EventListAgent
from events_ai.agents.flat_event_page_agent import FlatEventPageAgent
from events_ai.agents.gemini_event_research_agent import GeminiEventResearchAgent


class ResearchAgentFactory:
    @staticmethod
    def build(**kwargs) -> GeminiEventResearchAgent:
        agent_type = kwargs.get("agent", "")

        if agent_type == "EventListAgent":
            return EventListAgent(
                kwargs.get("url", ""),
                use_selenium=kwargs.get("use_selenium", False),
                start_url_params=kwargs.get("url_params", None),
            )
        elif agent_type == "FlatEventPageAgent":
            return FlatEventPageAgent(
                kwargs.get("url", ""), use_selenium=kwargs.get("use_selenium", False)
            )
        else:
            raise ValueError(f"Couldn't create research agent of type '{agent_type}'")
