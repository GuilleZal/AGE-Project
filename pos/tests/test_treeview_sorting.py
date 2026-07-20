"""Tests for treeview sorting utility helpers."""

import pytest
from pos.view.widgets.treeview_sorting import _clean_value, _parse_numeric


def test_clean_value_currency():
    assert _clean_value("$1,500.50") == "1500.50"
    assert _clean_value("$-350") == "-350"


def test_clean_value_percentage():
    assert _clean_value("12.5%") == "12.5"
    assert _clean_value("  50 %  ") == "50"


def test_clean_value_warnings():
    assert _clean_value("⚠ 10") == "10"
    assert _clean_value("⚠ $5.99") == "5.99"


def test_clean_value_stock_units():
    assert _clean_value("10 Kg") == "10"
    assert _clean_value("2.5 kg") == "2.5"
    assert _clean_value("⚠ 5 u.") == "5"
    assert _clean_value("100 u") == "100"


def test_parse_numeric():
    assert _parse_numeric("$1,500.50") == 1500.50
    assert _parse_numeric("10 Kg") == 10.0
    assert _parse_numeric("⚠ 5 u.") == 5.0
    assert _parse_numeric("Invalid") == 0.0
    assert _parse_numeric("") == 0.0
