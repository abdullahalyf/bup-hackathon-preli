"""Replace this no-op stub with the LLM interpretation pipeline."""


def interpret_notes(notes: list[str], battery: dict) -> list[dict]:
    return [
        {
            "note_index": index,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "stub",
        }
        for index, _note in enumerate(notes)
    ]
