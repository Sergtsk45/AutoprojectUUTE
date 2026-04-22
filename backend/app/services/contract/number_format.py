"""
* @file: number_format.py
* @description: Пропись сумм и дат по-русски, форматирование для договора/счёта.
* @created: 2026-04-22
"""

from __future__ import annotations

import re
from datetime import datetime

_RU_MONTHS = [
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]

_ONES_M = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_ONES_F = ["", "одна", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_TEENS = [
    "десять",
    "одиннадцать",
    "двенадцать",
    "тринадцать",
    "четырнадцать",
    "пятнадцать",
    "шестнадцать",
    "семнадцать",
    "восемнадцать",
    "девятнадцать",
]
_TENS = [
    "",
    "десять",
    "двадцать",
    "тридцать",
    "сорок",
    "пятьдесят",
    "шестьдесят",
    "семьдесят",
    "восемьдесят",
    "девяносто",
]
_HUNDS = [
    "",
    "сто",
    "двести",
    "триста",
    "четыреста",
    "пятьсот",
    "шестьсот",
    "семьсот",
    "восемьсот",
    "девятьсот",
]


def ru_date(dt: datetime) -> str:
    """Дата в русском формате: «15 апреля 2026 г.»"""
    return f"{dt.day}\u202f{_RU_MONTHS[dt.month]}\u202f{dt.year}\u202fг."


def _decline(n: int, one: str, few: str, many: str) -> str:
    if 11 <= n % 100 <= 19:
        return many
    m = n % 10
    if m == 1:
        return one
    if 2 <= m <= 4:
        return few
    return many


def _say_hundreds(n: int, feminine: bool = False) -> list[str]:
    ones = _ONES_F if feminine else _ONES_M
    words: list[str] = []
    h, r = divmod(n, 100)
    if h:
        words.append(_HUNDS[h])
    if 10 <= r <= 19:
        words.append(_TEENS[r - 10])
    else:
        t, u = divmod(r, 10)
        if t:
            words.append(_TENS[t])
        if u:
            words.append(ones[u])
    return words


def number_to_words_ru(n: int) -> str:
    """Число прописью (рубли), диапазон 0–999 999."""
    if n == 0:
        return "ноль рублей"
    parts: list[str] = []
    thousands, remainder = divmod(n, 1000)
    if thousands:
        parts.extend(_say_hundreds(thousands, feminine=True))
        parts.append(_decline(thousands, "тысяча", "тысячи", "тысяч"))
    if remainder:
        parts.extend(_say_hundreds(remainder, feminine=False))
    parts.append(_decline(n, "рубль", "рубля", "рублей"))
    return " ".join(parts)


def fmt_rub(n: int) -> str:
    """Форматирует сумму с узким неразрывным пробелом как разделителем тысяч."""
    return f"{n:,}".replace(",", "\u202f")


def extract_city(address: str) -> str:
    """Извлекает город из адреса (первая часть до запятой, без «г. »)."""
    city_part = address.split(",")[0].strip()
    return re.sub(r"^г\.\s*", "", city_part).strip()
