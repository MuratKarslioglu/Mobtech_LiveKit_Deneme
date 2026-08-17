import asyncio

from app.tools.math_tools import add_numbers


def test_add_numbers_returns_sum():
    result = asyncio.run(add_numbers(a=125, b=348))
    assert result == 473


def test_add_numbers_handles_negative_values():
    result = asyncio.run(add_numbers(a=-10, b=4))
    assert result == -6


def test_add_numbers_is_registered_as_function_tool():
    assert add_numbers.info.name == "add_numbers"
    assert add_numbers.info.description
