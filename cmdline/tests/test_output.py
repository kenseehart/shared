from cmdline.output import emit_output, format_grid, json_dumps


def test_format_grid_scalar_dict():
    text = format_grid({"message_count": 42, "openai_configured": True})
    assert "message_count  42" in text
    assert "openai_configured  true" in text


def test_format_grid_list_of_dicts_markdown():
    text = format_grid(
        [{"email": "a@b.com", "ok": True}],
        markdown=True,
    )
    assert "| email | ok |" in text
    assert "| a@b.com | true |" in text


def test_emit_output_json(capsys):
    emit_output({"x": 1}, json_output=True)
    assert '"x": 1' in capsys.readouterr().out


def test_json_dumps():
    assert '"name": "fish"' in json_dumps({"name": "fish"})
