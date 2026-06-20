from cmdline.output import emit_output, format_for_agent, format_grid, json_dumps, parse_columns


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


def test_format_grid_columns():
    rows = [
        {"domain": "seehart.com", "up": True, "renewal": "2027-01-01"},
        {"domain": "agi.green", "up": False, "renewal": ""},
    ]
    text = format_grid(rows, columns=["domain", "up"])
    assert "domain" in text
    assert "up" in text
    assert "renewal" not in text


def test_format_for_agent_json_columns():
    rows = [{"a": 1, "b": 2}]
    out = format_for_agent(rows, format="json", columns=["b"])
    assert '"b": 2' in out
    assert '"a"' not in out


def test_parse_columns():
    assert parse_columns("domain, up ,renewal") == ["domain", "up", "renewal"]
    assert parse_columns("") is None


def test_emit_output_json(capsys):
    emit_output({"x": 1}, json_output=True)
    assert '"x": 1' in capsys.readouterr().out


def test_json_dumps():
    assert '"name": "fish"' in json_dumps({"name": "fish"})
