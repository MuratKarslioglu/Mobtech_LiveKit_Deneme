from app.tools.registry import all_tools, tool_config


def test_all_tools_includes_add_numbers():
    names = {tool.info.name for tool in all_tools()}
    assert "add_numbers" in names


def test_tool_config_returns_registered_metadata():
    config = tool_config("add_numbers")
    assert config is not None
    assert config.expected_latency == "fast"
    assert config.interim_message == "Hesaplamayı yapıyorum."


def test_tool_config_returns_none_for_unknown_tool():
    assert tool_config("does_not_exist") is None
