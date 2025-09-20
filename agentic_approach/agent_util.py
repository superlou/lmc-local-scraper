def build_prompt(prompt_file: str, *args, **kwargs) -> str:
    template = open(prompt_file).read()
    return template.format(*args, **kwargs)
