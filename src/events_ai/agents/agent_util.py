import importlib.resources

PROMPT_DIR = importlib.resources.files(__name__).parent / "prompts"


def build_prompt(prompt_file: str, *args, **kwargs) -> str:
    template = open(PROMPT_DIR / prompt_file).read()
    return template.format(*args, **kwargs)
