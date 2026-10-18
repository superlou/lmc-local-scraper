from datetime import date

from google import genai

from events_ai.agents.event_list_agent import EventListAgent
from events_ai.agents.flat_event_page_agent import FlatEventPageAgent
from events_ai.agents.gemini_event_research_agent import GeminiEventResearchAgent
from events_ai.agents.revize_json_agent import ReviseJSONAgent


class ResearchAgentFactory:
    @staticmethod
    def build(llm: genai.Client, events_start: date, events_finish: date, **kwargs):
        agent_type = kwargs.get("agent", "")

        if agent_type == "EventListAgent":
            return EventListAgent(
                llm,
                events_start,
                events_finish,
                kwargs.get("url", ""),
                use_selenium=kwargs.get("use_selenium", False),
                start_url_params=kwargs.get("url_params", None),
            )
        elif agent_type == "FlatEventPageAgent":
            return FlatEventPageAgent(
                llm,
                events_start,
                events_finish,
                kwargs.get("url", ""),
                use_selenium=kwargs.get("use_selenium", False),
                split_first=kwargs.get("split_first", False),
            )
        elif agent_type == "ReviseJSONAgent":
            return ReviseJSONAgent(
                events_start,
                events_finish,
                kwargs.get("url", ""),
                kwargs.get("organization", ""),
                kwargs.get("default_link", ""),
            )
        else:
            raise ValueError(f"Couldn't create research agent of type '{agent_type}'")
