"""Генератор договора на проектирование УУТЭ и счёта на аванс (.docx).

Использует python-docx (уже в requirements.txt) по аналогии с cover_letter.py.
Реквизиты исполнителя берутся из settings.company_*.

Функции:
- generate_contract_number(order_id) → str
- generate_contract(...)             → Path к временному .docx
- generate_invoice(...)              → Path к временному .docx

Вызывающий код обязан удалить временные файлы после отправки.
"""

import re
import tempfile
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.core.config import settings


# ═══════════════════════════════════════════════════════════════════════════════
# Вспомогательные утилиты
# ═══════════════════════════════════════════════════════════════════════════════

_RU_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

_ONES_M = ["", "один", "два", "три", "четыре", "пять",
           "шесть", "семь", "восемь", "девять"]
_ONES_F = ["", "одна", "две", "три", "четыре", "пять",
           "шесть", "семь", "восемь", "девять"]
_TEENS  = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
           "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
_TENS   = ["", "десять", "двадцать", "тридцать", "сорок", "пятьдесят",
           "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
_HUNDS  = ["", "сто", "двести", "триста", "четыреста", "пятьсот",
           "шестьсот", "семьсот", "восемьсот", "девятьсот"]


def _ru_date(dt: datetime) -> str:
    """Дата в русском формате: «15 апреля 2026 г.»"""
    return f"{dt.day}\u202f{_RU_MONTHS[dt.month]}\u202f{dt.year}\u202fг."


def _decline(n: int, one: str, few: str, many: str) -> str:
    """Склоняет слово по числу (рубль/рубля/рублей)."""
    if 11 <= n % 100 <= 19:
        return many
    m = n % 10
    if m == 1:
        return one
    if 2 <= m <= 4:
        return few
    return many


def _say_hundreds(n: int, feminine: bool = False) -> list[str]:
    """Произносит число 1–999 в виде списка слов."""
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
    """Число прописью (рубли), диапазон 0–999 999.

    Примеры:
        22500 → «двадцать две тысячи пятьсот рублей»
        11000 → «одиннадцать тысяч рублей»
        1     → «один рубль»
    """
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


def _fmt(n: int) -> str:
    """Форматирует сумму с узким неразрывным пробелом как разделителем тысяч."""
    return f"{n:,}".replace(",", "\u202f")


def _extract_city(address: str) -> str:
    """Извлекает город из адреса (первая часть до запятой, без «г. »)."""
    city_part = address.split(",")[0].strip()
    return re.sub(r"^г\.\s*", "", city_part).strip()


# ═══════════════════════════════════════════════════════════════════════════════
# XML-утилиты для таблиц
# ═══════════════════════════════════════════════════════════════════════════════


def _set_table_borders(
    table,
    *,
    outer: bool = False,
    inner_h: bool = False,
    inner_v: bool = False,
) -> None:
    """Управляет видимостью границ таблицы через XML.

    Параметры управляют включением отдельных групп границ:
      outer   — внешний контур (top, left, bottom, right)
      inner_h — горизонтальные разделители между строками
      inner_v — вертикальный разделитель между колонками
    """
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)

    borders_el = OxmlElement("w:tblBorders")
    nil = {"val": "nil"}
    single = {"val": "single", "sz": "6", "space": "0", "color": "auto"}

    mapping = {
        "top":     single if outer   else nil,
        "left":    single if outer   else nil,
        "bottom":  single if outer   else nil,
        "right":   single if outer   else nil,
        "insideH": single if inner_h else nil,
        "insideV": single if inner_v else nil,
    }
    for edge, attrs in mapping.items():
        el = OxmlElement(f"w:{edge}")
        for k, v in attrs.items():
            el.set(qn(f"w:{k}"), v)
        borders_el.append(el)
    tblPr.append(borders_el)


def _cell_lines(cell, lines: list, font_size: int = 10) -> None:
    """Заполняет ячейку несколькими строками.

    Каждый элемент — строка или кортеж (строка, bold).
    Первая строка использует существующий параграф ячейки,
    последующие — добавляются как новые параграфы.
    """
    for i, line in enumerate(lines):
        text, bold = line if isinstance(line, tuple) else (line, False)
        para = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        run = para.add_run(text)
        run.font.size = Pt(font_size)
        run.bold = bold


def _cell_add_break_lines(cell, text: str, font_size: int = 9) -> None:
    """Добавляет текст с переносами строк (\\n) в ячейку через w:br."""
    para = cell.paragraphs[0]
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if i > 0:
            para.runs[-1].add_break() if para.runs else para.add_run().add_break()
        run = para.add_run(line)
        run.font.size = Pt(font_size)


# ═══════════════════════════════════════════════════════════════════════════════
# Публичные функции
# ═══════════════════════════════════════════════════════════════════════════════


def generate_contract_number(order_id: str) -> str:
    """Формирует номер договора: UUTE-YYYYMMDD-xxxx.

    Пример: «UUTE-20260415-a1b2»
    """
    return f"UUTE-{datetime.now().strftime('%Y%m%d')}-{order_id[:4]}"


def generate_contract(
    order_id_short: str,
    contract_number: str,
    object_address: str,
    client_name: str,
    payment_amount: int,
    advance_amount: int,
    requisites: dict,
) -> Path:
    """Генерирует DOCX договора на проектирование УУТЭ с условием оплаты 50/50.

    Args:
        order_id_short: Первые 8 символов UUID заявки (для имени файла).
        contract_number: Номер договора из generate_contract_number().
        object_address:  Адрес объекта теплоснабжения.
        client_name:     ФИО/наименование клиента (запасной вариант для контактов).
        payment_amount:  Полная стоимость работ, руб.
        advance_amount:  Сумма аванса (50%), руб.
        requisites:      Реквизиты клиента из CompanyRequisites.model_dump().

    Returns:
        Path к временному .docx файлу. Вызывающий код удаляет после отправки.
    """
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2)
    sec.bottom_margin = Cm(2)
    sec.left_margin = Cm(3)
    sec.right_margin = Cm(1.5)

    s = settings
    final_amount = payment_amount - advance_amount
    city = _extract_city(s.company_address) if s.company_address else "___"
    now = datetime.now()
    client_kpp = requisites.get("kpp") or "—"
    words_total = number_to_words_ru(payment_amount)

    # ── Заголовок ────────────────────────────────────────────────────────────
    for title in [
        f"ДОГОВОР\u202f№\u202f{contract_number}",
        "на выполнение проектных работ",
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(title)
        run.bold = True
        run.font.size = Pt(14)

    doc.add_paragraph()

    # ── Город и дата ─────────────────────────────────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    # Город слева, дата справа — через табуляцию
    run = p.add_run(f"г.\u202f{city}")
    run.font.size = Pt(12)
    tab_run = p.add_run(
        f"\t\t\t«____»\u202f__________\u202f{now.year}\u202fг."
    )
    tab_run.font.size = Pt(12)

    doc.add_paragraph()

    # ── Преамбула ─────────────────────────────────────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(
        f"{s.company_full_name}, ИНН\u202f{s.company_inn}, "
        f"в лице {s.company_director_position} {s.company_director_name}, "
        f"действующего на основании свидетельства о государственной регистрации, "
        f"именуемый в дальнейшем «Исполнитель», с одной стороны, и\n\n"
        f"{requisites['full_name']}, ИНН\u202f{requisites['inn']}, "
        f"в лице {requisites['director_position']} {requisites['director_name']}, "
        f"действующего на основании Устава, "
        f"именуемый в дальнейшем «Заказчик», с другой стороны, "
        f"совместно именуемые «Стороны», заключили настоящий Договор о нижеследующем:"
    )
    run.font.size = Pt(12)

    doc.add_paragraph()

    # ── Утилита для разделов ─────────────────────────────────────────────────

    def _section(title: str, items: list[str]) -> None:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(title)
        run.bold = True
        run.font.size = Pt(12)
        for text in items:
            pp = doc.add_paragraph()
            pp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = pp.add_run(text)
            r.font.size = Pt(12)
        doc.add_paragraph()

    # ── Раздел 1 ──────────────────────────────────────────────────────────────
    _section("1. ПРЕДМЕТ ДОГОВОРА", [
        f"1.1.\u2002Исполнитель обязуется разработать проект узла учёта тепловой "
        f"энергии (УУТЭ) по объекту: {object_address}, а Заказчик обязуется "
        f"принять и оплатить работы.",
        "1.2.\u2002Проект выполняется в соответствии с Приказом Минстроя России "
        "№\u202f1036/пр «Правила коммерческого учёта тепловой энергии, теплоносителя».",
        "1.3.\u2002Состав проекта: пояснительная записка, принципиальная схема узла "
        "учёта, монтажные чертежи, спецификация оборудования, "
        "сопроводительное письмо в РСО.",
    ])

    # ── Раздел 2 ──────────────────────────────────────────────────────────────
    _section("2. СТОИМОСТЬ И ПОРЯДОК ОПЛАТЫ", [
        f"2.1.\u2002Стоимость работ по настоящему Договору составляет "
        f"{_fmt(payment_amount)}\u202fруб. "
        f"({words_total[0].upper() + words_total[1:]}). "
        f"НДС не облагается на основании ст.\u202f346.11 НК\u202fРФ (УСН).",
        f"2.2.\u2002Оплата производится в два этапа:\n"
        f"— аванс в размере 50\u202f% ({_fmt(advance_amount)}\u202fруб.) — "
        f"в течение 5\u202f(пяти) рабочих дней с момента подписания Договора;\n"
        f"— окончательный расчёт в размере 50\u202f% ({_fmt(final_amount)}\u202fруб.) — "
        f"в течение 5\u202f(пяти) рабочих дней после согласования проекта в РСО.",
        "2.3.\u2002Оплата производится безналичным переводом на расчётный счёт Исполнителя.",
    ])

    # ── Раздел 3 ──────────────────────────────────────────────────────────────
    _section("3. СРОКИ ВЫПОЛНЕНИЯ", [
        "3.1.\u2002Срок выполнения работ — 3\u202f(три) рабочих дня с момента "
        "получения аванса.",
        "3.2.\u2002Результат работ направляется Заказчику в электронном виде (PDF) "
        "на электронную почту.",
    ])

    # ── Раздел 4 ──────────────────────────────────────────────────────────────
    client_contact = requisites.get("email") or client_name
    _section("4. ПОРЯДОК СДАЧИ-ПРИЁМКИ", [
        f"4.1.\u2002Исполнитель направляет Заказчику проект на e-mail: {client_contact}.",
        "4.2.\u2002Заказчик обязан в течение 3\u202fрабочих дней рассмотреть проект "
        "и направить замечания или подписать Акт выполненных работ.",
        "4.3.\u2002Если в указанный срок замечания не поступили, работы считаются "
        "принятыми.",
    ])

    # ── Раздел 5: Реквизиты и подписи ────────────────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run("5. РЕКВИЗИТЫ И ПОДПИСИ СТОРОН")
    run.bold = True
    run.font.size = Pt(12)

    # Таблица реквизитов: 2 колонки, только вертикальный разделитель
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Cm(8)
    table.columns[1].width = Cm(8)
    _set_table_borders(table, inner_v=True)

    left_cell, right_cell = table.rows[0].cells

    _cell_lines(left_cell, [
        ("Исполнитель", True),
        "",
        s.company_full_name,
        f"ИНН\u202f{s.company_inn}",
        "КПП\u202f—",
        s.company_address or "—",
        f"р/с\u202f{s.company_settlement_account}",
        f"в {s.company_bank_name}",
        f"БИК\u202f{s.company_bik}",
        f"к/с\u202f{s.company_corr_account}",
        "",
        f"__________\u202f/\u202f{s.company_director_name}",
        "М.П.",
    ])

    _cell_lines(right_cell, [
        ("Заказчик", True),
        "",
        requisites["full_name"],
        f"ИНН\u202f{requisites['inn']}",
        f"КПП\u202f{client_kpp}",
        requisites["legal_address"],
        f"р/с\u202f{requisites['settlement_account']}",
        f"в {requisites['bank_name']}",
        f"БИК\u202f{requisites['bik']}",
        f"к/с\u202f{requisites['corr_account']}",
        "",
        f"__________\u202f/\u202f{requisites['director_name']}",
        "М.П.",
    ])

    # ── Сохранить во временный файл ───────────────────────────────────────────
    tmp = tempfile.NamedTemporaryFile(
        suffix=".docx",
        prefix=f"dogovor_{order_id_short}_",
        delete=False,
    )
    tmp.close()
    doc.save(tmp.name)
    return Path(tmp.name)


def generate_invoice(
    order_id_short: str,
    contract_number: str,
    object_address: str,
    payment_amount: int,
    advance_amount: int,
    requisites: dict,
    is_advance: bool = True,
) -> Path:
    """Генерирует DOCX счёта на оплату (аванс или окончательный расчёт).

    Args:
        order_id_short: Первые 8 символов UUID заявки (для имени файла).
        contract_number: Номер договора.
        object_address:  Адрес объекта.
        payment_amount:  Полная стоимость работ, руб.
        advance_amount:  Сумма аванса (50%), руб.
        requisites:      Реквизиты клиента из CompanyRequisites.model_dump().
        is_advance:      True = счёт на 50% аванс, False = счёт на остаток 50%.

    Returns:
        Path к временному .docx файлу. Вызывающий код удаляет после отправки.
    """
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2)
    sec.bottom_margin = Cm(2)
    sec.left_margin = Cm(2)
    sec.right_margin = Cm(1.5)

    s = settings
    amount = advance_amount if is_advance else (payment_amount - advance_amount)
    invoice_label = "аванс 50%" if is_advance else "окончательный расчёт 50%"
    now = datetime.now()
    client_kpp = requisites.get("kpp") or "—"
    words_amount = number_to_words_ru(amount)

    # ── Шапка: реквизиты банка получателя ────────────────────────────────────
    # Стандартный формат российского счёта: 4 строки, 2 колонки
    hdr = doc.add_table(rows=4, cols=2)
    hdr.style = "Table Grid"
    hdr.autofit = False
    hdr.columns[0].width = Cm(10)
    hdr.columns[1].width = Cm(7.5)

    def _hdr(row: int, col: int, lines: str, bold: bool = False) -> None:
        cell = hdr.rows[row].cells[col]
        cell.paragraphs[0].clear()
        _cell_add_break_lines(cell, lines)
        if bold:
            for run in cell.paragraphs[0].runs:
                run.bold = True

    _hdr(0, 0, f"Банк получателя:\n{s.company_bank_name}")
    _hdr(0, 1, f"БИК\n{s.company_bik}")
    _hdr(1, 0, "")
    _hdr(1, 1, f"Сч.\u202f№\n{s.company_corr_account}")
    _hdr(2, 0, f"ИНН\u202f{s.company_inn}")
    _hdr(2, 1, "")
    _hdr(3, 0, f"Получатель:\n{s.company_full_name}", bold=True)
    _hdr(3, 1, f"Сч.\u202f№\n{s.company_settlement_account}")

    doc.add_paragraph()

    # ── Заголовок счёта ───────────────────────────────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        f"СЧЁТ НА ОПЛАТУ\u202f№\u202f{contract_number}\n"
        f"от {_ru_date(now)}"
    )
    run.bold = True
    run.font.size = Pt(14)

    doc.add_paragraph()

    # ── Поставщик и покупатель ────────────────────────────────────────────────
    def _info_line(label: str, value: str) -> None:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r1 = p.add_run(f"{label}:\u2003")
        r1.bold = True
        r1.font.size = Pt(11)
        r2 = p.add_run(value)
        r2.font.size = Pt(11)

    _info_line(
        "Поставщик (Исполнитель)",
        f"{s.company_full_name}, ИНН\u202f{s.company_inn}, "
        f"{s.company_address or '—'}",
    )
    _info_line(
        "Покупатель (Заказчик)",
        f"{requisites['full_name']}, ИНН\u202f{requisites['inn']}, "
        f"КПП\u202f{client_kpp}, {requisites['legal_address']}",
    )
    _info_line("Основание", f"Договор\u202f№\u202f{contract_number}")

    doc.add_paragraph()

    # ── Таблица услуг ─────────────────────────────────────────────────────────
    # Ширины: 1.0 + 8.5 + 1.5 + 1.5 + 2.5 + 2.5 = 17.5 см
    col_headers = ["№", "Наименование работ (услуг)", "Кол.", "Ед.", "Цена, руб.", "Сумма, руб."]
    col_widths = [Cm(1.0), Cm(8.5), Cm(1.5), Cm(1.5), Cm(2.5), Cm(2.5)]

    svc_tbl = doc.add_table(rows=2, cols=6)
    svc_tbl.style = "Table Grid"
    svc_tbl.autofit = False

    # Заголовок таблицы
    for i, (header, width) in enumerate(zip(col_headers, col_widths)):
        cell = svc_tbl.rows[0].cells[i]
        cell.width = width
        cell.paragraphs[0].clear()
        run = cell.paragraphs[0].add_run(header)
        run.bold = True
        run.font.size = Pt(10)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Строка с услугой
    service_name = (
        f"Разработка проекта УУТЭ по объекту:\n{object_address} ({invoice_label})"
    )
    row_data = [
        ("1",              WD_ALIGN_PARAGRAPH.CENTER),
        (service_name,     WD_ALIGN_PARAGRAPH.LEFT),
        ("1",              WD_ALIGN_PARAGRAPH.CENTER),
        ("усл.",           WD_ALIGN_PARAGRAPH.CENTER),
        (_fmt(amount),     WD_ALIGN_PARAGRAPH.RIGHT),
        (_fmt(amount),     WD_ALIGN_PARAGRAPH.RIGHT),
    ]
    for i, (text, align) in enumerate(row_data):
        cell = svc_tbl.rows[1].cells[i]
        cell.paragraphs[0].clear()
        run = cell.paragraphs[0].add_run(text)
        run.font.size = Pt(10)
        cell.paragraphs[0].alignment = align

    doc.add_paragraph()

    # ── Итого ─────────────────────────────────────────────────────────────────
    for text, bold in [
        (f"Итого:\u2003{_fmt(amount)}\u202fруб.", True),
        ("В том числе НДС: не облагается (УСН, ст.\u202f346.11 НК\u202fРФ).", False),
        (
            f"Всего к оплате:\u2003{_fmt(amount)}\u202fруб. "
            f"({words_amount[0].upper() + words_amount[1:]}).",
            True,
        ),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = p.add_run(text)
        run.bold = bold
        run.font.size = Pt(12)

    doc.add_paragraph()
    doc.add_paragraph()

    # ── Подпись ───────────────────────────────────────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(
        f"{s.company_director_position}:\u2003"
        f"__________\u202f/\u202f{s.company_director_name}"
    )
    run.font.size = Pt(12)

    # ── Сохранить во временный файл ───────────────────────────────────────────
    tmp = tempfile.NamedTemporaryFile(
        suffix=".docx",
        prefix=f"schet_{order_id_short}_",
        delete=False,
    )
    tmp.close()
    doc.save(tmp.name)
    return Path(tmp.name)
