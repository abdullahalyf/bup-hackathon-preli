from app.interpreter import interpret_notes


def test_stub_returns_one_no_op_per_note():
    entries = interpret_notes(["a", "b"], {"capacity_kwh": 10})
    assert [entry["note_index"] for entry in entries] == [0, 1]
    assert all(entry["directive_type"] == "no_op" and not entry["applies"] for entry in entries)
