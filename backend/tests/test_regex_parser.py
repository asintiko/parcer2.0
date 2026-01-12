from decimal import Decimal

import pytest

pytz = pytest.importorskip("pytz")

from parsers.regex_parser import RegexParser


def test_parse_humo_notification_with_separators_and_timezone():
    parser = RegexParser()
    text = """💸 Оплата
➖ 400.000,00 UZS
📍 OQ P2P>TASHKENT
💳 HUMOCARD *6714
🕓 12:58 05.04.2025
💰 535.000,40 UZS"""

    parsed = parser.parse(text)

    assert parsed is not None
    assert parsed["parsing_method"] == "REGEX_HUMO"
    assert parsed["amount"] == Decimal("400000.00")
    assert parsed["balance_after"] == Decimal("535000.40")
    assert parsed["operator_raw"] == "OQ P2P>TASHKENT"
    assert parsed["card_last_4"] == "6714"
    assert parsed["transaction_type"] == "DEBIT"
    tz = pytz.timezone("Asia/Tashkent")
    assert parsed["transaction_date"].tzinfo == tz


def test_parse_sms_inline_and_two_digit_year():
    parser = RegexParser()
    text = "Pokupka: XK FAMILY SHOP, TOSHKENT, 02.04.25 11:48 karta ***0907. summa:80000.00 UZS, balans:2527792.14 UZS"

    parsed = parser.parse(text)

    assert parsed is not None
    assert parsed["parsing_method"] == "REGEX_SMS"
    assert parsed["amount"] == Decimal("80000.00")
    assert parsed["balance_after"] == Decimal("2527792.14")
    assert parsed["card_last_4"] == "0907"
    assert parsed["operator_raw"] == "XK FAMILY SHOP"
    assert parsed["transaction_type"] == "DEBIT"
    assert parsed["transaction_date"].year == 2025


def test_parse_semicolon_format_with_noise():
    parser = RegexParser()
    text = "FW: HUMOCARD *6921: oplata 200000.00 UZS; SmartBank P2P HUMO U; 25-04-02 15:33; Dostupno: 1852200.28 UZS"

    parsed = parser.parse(text)

    assert parsed is not None
    assert parsed["parsing_method"] == "REGEX_SEMICOLON"
    assert parsed["amount"] == Decimal("200000.00")
    assert parsed["application_mapped"] is None  # mapping happens later
    assert parsed["operator_raw"] == "SmartBank P2P HUMO U"
    assert parsed["transaction_date"].year == 2025
    assert parsed["transaction_date"].month == 4
    assert parsed["transaction_date"].day == 2


def test_parse_returns_none_when_amount_missing():
    parser = RegexParser()
    text = "Оплата без суммы и нужных маркеров"

    parsed = parser.parse(text)

    assert parsed is None
