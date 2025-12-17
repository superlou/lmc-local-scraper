class PhoneticReplacer:
    def __init__(self, substitutions: dict[str, list[str]]):
        self.substitutions = substitutions

    def replace(self, text: str) -> str:
        for phonetic_spelling, original_spellings in self.substitutions.items():
            for original_spelling in original_spellings:
                text = text.replace(original_spelling, phonetic_spelling)

        return text
