import os

from google import genai
from google.genai.interactions import Interaction, Usage
from loguru import logger
from pydantic import BaseModel

from .service import Service, ServiceGenerationFailed, ServiceUse


class GeminiChatService(Service):
    def __init__(self, model: str, thinking_budget: int = 0):
        super().__init__()
        self.model = model
        self.thinking_budget = 0
        self.llm = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        # self.chat = self.llm.chats.create(model=model)
        self.previous_interaction_id = None

    def message[T: BaseModel](self, prompt: str, response_type: type[T]) -> T:
        interaction = self.llm.interactions.create(
            model=self.model,
            input=prompt,
            previous_interaction_id=self.previous_interaction_id,
            generation_config={"thinking_budget": 0},
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": response_type.model_json_schema(),
            },
        )

        if not isinstance(interaction, Interaction):
            raise ServiceGenerationFailed()
        elif interaction.output_text is None:
            raise ServiceGenerationFailed()

        self.previous_interaction_id = interaction.id

        if interaction.usage is not None:
            use = GeminiServiceUse(self.model, interaction.usage)
            logger.info(use.log_msg)
            self.usages.append(use)

        return response_type.model_validate_json(interaction.output_text)


class GeminiServiceUse(ServiceUse):
    def __init__(self, model: str, usage: Usage):
        # todo This assumes this only deals with text tokens
        self.model = model
        self.input: int = usage.total_input_tokens or 0
        self.cached: int = usage.total_cached_tokens or 0
        self.uncached_input = self.input - self.cached
        self.output: int = usage.total_output_tokens or 0
        self.total: int = usage.total_tokens or 0

    @property
    def cost(self) -> float:
        match self.model:
            case "gemini-2.5-flash":
                return (
                    0.30 * self.uncached_input / 1e6
                    + 2.50 * self.output / 1e6
                    + 0.03 * self.cached / 1e6
                )
            case "gemini-nano-banana-2.1":
                return 1.50 * self.uncached_input / 1e6 + 30.00 * self.output / 1e6
            case _:
                return 0.0

    @property
    def log_msg(self) -> str:
        return f"Used {self.model}:{self.input} input (incl. {self.cached} cached), {self.output} output, ${self.cost:.3g}"
