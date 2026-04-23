# План реализации: Интеграция конфигуратора схем с админкой и пайплайном

> **Для агентных воркеров:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (рекомендуется) или superpowers:executing-plans для реализации задача-за-задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для отслеживания.

**Цель:** Автоматическая генерация PDF схемы в пайплайне обработки заявок и отображение конфигурации в админ-панели.

**Архитектура:** Оптимистичная автогенерация: если клиент заполнил конфигуратор, система генерирует PDF в `process_client_response` без дополнительных проверок. Функция `compute_client_document_missing` обновляется для исключения `heat_scheme` из обязательных документов при наличии `scheme_config`. Админ-панель получает новую секцию в `parsed_params`.

**Tech Stack:** Python 3.11+, SQLAlchemy, Celery, FastAPI, Pydantic, WeasyPrint, vanilla JavaScript.

**Спецификация:** `docs/superpowers/specs/2026-04-23-scheme-generator-admin-integration-design.md`

---

## Карта файлов

### Изменяемые файлы

| Файл | Что меняется |
|------|-------------|
| `backend/app/services/param_labels.py` | Сигнатура `compute_client_document_missing` |
| `backend/app/services/tasks.py` | Новая функция `_auto_generate_scheme_if_configured`, обновление `process_client_response` и `check_data_completeness` |
| `backend/static/admin.html` | Новая секция "Конфигурация схемы" в `renderParsedParams` |

### Создаваемые файлы

| Файл | Назначение |
|------|-----------|
| `backend/tests/test_scheme_auto_generation.py` | Тесты автогенерации и обновлённой логики `missing_params` |

---

## Task 1: Обновить `compute_client_document_missing` для учёта `scheme_config`

**Files:**
- Modify: `backend/app/services/param_labels.py:20-22`
- Test: `backend/tests/test_scheme_auto_generation.py` (новый файл)

- [ ] **Step 1: Создать тест-файл и написать первые тесты**

Создать `backend/tests/test_scheme_auto_generation.py` со следующим содержимым:

```python
"""
@file: test_scheme_auto_generation.py
@description: Тесты автогенерации PDF схемы и обновлённой логики missing_params.
@dependencies: pytest, app.services.param_labels, app.services.tasks
@created: 2026-04-23
"""

import pytest

from app.services.param_labels import (
    CLIENT_DOCUMENT_PARAM_CODES,
    compute_client_document_missing,
)


class TestComputeClientDocumentMissing:
    """Тесты функции compute_client_document_missing с учётом scheme_config."""

    def test_all_documents_uploaded_returns_empty(self):
        uploaded = set(CLIENT_DOCUMENT_PARAM_CODES)
        result = compute_client_document_missing(uploaded)
        assert result == []

    def test_no_documents_uploaded_returns_all(self):
        result = compute_client_document_missing(set())
        assert set(result) == set(CLIENT_DOCUMENT_PARAM_CODES)

    def test_heat_scheme_excluded_when_scheme_config_present(self):
        """Если в survey_data есть scheme_config, heat_scheme не должен быть в missing."""
        uploaded = {"BALANCE_ACT", "CONNECTION_PLAN", "heat_point_plan", "company_card"}
        survey_data = {"scheme_config": {"connection_type": "dependent"}}
        result = compute_client_document_missing(uploaded, survey_data)
        assert "heat_scheme" not in result

    def test_heat_scheme_required_when_no_scheme_config(self):
        """Если scheme_config отсутствует, heat_scheme должен быть в missing."""
        uploaded = {"BALANCE_ACT", "CONNECTION_PLAN", "heat_point_plan", "company_card"}
        result = compute_client_document_missing(uploaded, survey_data=None)
        assert "heat_scheme" in result

    def test_heat_scheme_required_when_empty_survey_data(self):
        uploaded = {"BALANCE_ACT", "CONNECTION_PLAN", "heat_point_plan", "company_card"}
        result = compute_client_document_missing(uploaded, survey_data={})
        assert "heat_scheme" in result

    def test_other_missing_documents_still_reported(self):
        """heat_scheme исключается, но остальные отсутствующие документы возвращаются."""
        uploaded = {"heat_scheme"}
        survey_data = {"scheme_config": {"connection_type": "dependent"}}
        result = compute_client_document_missing(uploaded, survey_data)
        expected = {c for c in CLIENT_DOCUMENT_PARAM_CODES if c != "heat_scheme"}
        assert set(result) == expected

    def test_backward_compatible_without_survey_data(self):
        """Вызов без survey_data работает как раньше."""
        uploaded = set()
        result = compute_client_document_missing(uploaded)
        assert set(result) == set(CLIENT_DOCUMENT_PARAM_CODES)
```

- [ ] **Step 2: Запустить тесты — должны упасть**

Run: `cd backend && python -m pytest tests/test_scheme_auto_generation.py::TestComputeClientDocumentMissing -v`

Expected: Часть тестов падает с `TypeError: compute_client_document_missing() takes 1 positional argument but 2 were given`.

- [ ] **Step 3: Обновить сигнатуру функции**

В файле `backend/app/services/param_labels.py` заменить строки 20-22:

```python
def compute_client_document_missing(
    uploaded_categories: set[str],
    survey_data: dict | None = None,
) -> list[str]:
    """Какие из обязательных документов ещё не загружены.

    Args:
        uploaded_categories: Множество кодов уже загруженных файлов.
        survey_data: Данные опросного листа. Если содержит ``scheme_config``,
            ``heat_scheme`` исключается из missing (будет сгенерирован автоматически).

    Returns:
        Список кодов недостающих документов.
    """
    missing: list[str] = []
    for code in CLIENT_DOCUMENT_PARAM_CODES:
        if code in uploaded_categories:
            continue
        if code == "heat_scheme" and survey_data and "scheme_config" in survey_data:
            continue
        missing.append(code)
    return missing
```

- [ ] **Step 4: Запустить тесты — должны пройти**

Run: `cd backend && python -m pytest tests/test_scheme_auto_generation.py::TestComputeClientDocumentMissing -v`

Expected: Все 6 тестов PASS.

- [ ] **Step 5: Коммит**

```bash
git add backend/app/services/param_labels.py backend/tests/test_scheme_auto_generation.py
git commit -m "feat(schemes): compute_client_document_missing учитывает scheme_config"
```

---

## Task 2: Реализовать `_auto_generate_scheme_if_configured`

**Files:**
- Modify: `backend/app/services/tasks.py` (добавить новую функцию перед `process_client_response`)
- Test: `backend/tests/test_scheme_auto_generation.py`

**Контекст:**
- В `scheme_generator.py` уже реализована синхронная работа с генерацией. Функция автогенерации должна повторить эту логику в контексте Celery-воркера (синхронная SQLAlchemy-сессия).
- Путь хранения: `{settings.upload_dir}/{order_id}/heat_scheme/{filename}`.
- Импорт `SchemeConfig` внутри функции, чтобы не удорожать импорт `tasks.py` при холодном старте воркера.

- [ ] **Step 1: Написать тест для успешной автогенерации**

Добавить в `backend/tests/test_scheme_auto_generation.py`:

```python
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.models.models import FileCategory


class TestAutoGenerateScheme:
    """Тесты функции _auto_generate_scheme_if_configured."""

    def _make_order_mock(self, survey_data=None, parsed_params=None):
        order = MagicMock()
        order.id = uuid.uuid4()
        order.survey_data = survey_data or {}
        order.parsed_params = parsed_params or {}
        order.object_address = "г. Москва, ул. Ленина, д. 1"
        order.client_organization = "ООО «Ромашка»"
        return order

    def test_success_with_valid_config(self, tmp_path, monkeypatch):
        """Успешная генерация создаёт файл и OrderFile."""
        from app.services import tasks

        monkeypatch.setattr(tasks.settings, "upload_dir", tmp_path)

        session = MagicMock()
        order = self._make_order_mock(
            survey_data={
                "scheme_config": {
                    "connection_type": "dependent",
                    "has_valve": False,
                    "has_gwp": False,
                    "has_ventilation": False,
                }
            }
        )

        with patch.object(
            tasks, "render_scheme_pdf", return_value=b"%PDF-fake-bytes"
        ):
            result = tasks._auto_generate_scheme_if_configured(session, order)

        assert result is True
        session.add.assert_called_once()
        added_file = session.add.call_args[0][0]
        assert added_file.category == FileCategory.HEAT_SCHEME
        assert added_file.order_id == order.id
        assert added_file.file_size == len(b"%PDF-fake-bytes")
        session.commit.assert_called()

        scheme_dir = tmp_path / str(order.id) / "heat_scheme"
        assert scheme_dir.exists()
        assert any(scheme_dir.iterdir()), "PDF file must be written"

    def test_invalid_config_returns_false(self, tmp_path, monkeypatch):
        """Недопустимая комбинация параметров → False, файл не создаётся."""
        from app.services import tasks

        monkeypatch.setattr(tasks.settings, "upload_dir", tmp_path)

        session = MagicMock()
        order = self._make_order_mock(
            survey_data={
                "scheme_config": {
                    "connection_type": "independent",
                    "has_valve": False,
                    "has_gwp": False,
                    "has_ventilation": False,
                }
            }
        )

        result = tasks._auto_generate_scheme_if_configured(session, order)
        assert result is False
        session.add.assert_not_called()

    def test_missing_scheme_config_returns_false(self, tmp_path, monkeypatch):
        from app.services import tasks

        monkeypatch.setattr(tasks.settings, "upload_dir", tmp_path)

        session = MagicMock()
        order = self._make_order_mock(survey_data={})

        result = tasks._auto_generate_scheme_if_configured(session, order)
        assert result is False
        session.add.assert_not_called()

    def test_pdf_render_exception_returns_false(self, tmp_path, monkeypatch):
        """Если WeasyPrint падает, функция возвращает False без пробрасывания."""
        from app.services import tasks

        monkeypatch.setattr(tasks.settings, "upload_dir", tmp_path)

        session = MagicMock()
        order = self._make_order_mock(
            survey_data={
                "scheme_config": {
                    "connection_type": "dependent",
                    "has_valve": False,
                    "has_gwp": False,
                    "has_ventilation": False,
                }
            }
        )

        with patch.object(
            tasks, "render_scheme_pdf", side_effect=RuntimeError("WeasyPrint error")
        ):
            result = tasks._auto_generate_scheme_if_configured(session, order)

        assert result is False
        session.add.assert_not_called()
```

- [ ] **Step 2: Запустить тесты — должны упасть**

Run: `cd backend && python -m pytest tests/test_scheme_auto_generation.py::TestAutoGenerateScheme -v`

Expected: `AttributeError: module 'app.services.tasks' has no attribute '_auto_generate_scheme_if_configured'` (или аналогичные ошибки импорта).

- [ ] **Step 3: Добавить импорты и функцию автогенерации в `tasks.py`**

В файле `backend/app/services/tasks.py` найти блок импортов в начале файла и добавить после существующих импортов моделей:

```python
from app.services.scheme_pdf_renderer import render_scheme_pdf
```

Затем добавить новую функцию **перед** `@celery_app.task(...)` задачей `process_client_response` (примерно на строку 610):

```python
def _auto_generate_scheme_if_configured(session: Session, order: Order) -> bool:
    """Автогенерация PDF схемы из сохранённой конфигурации.

    Использует ``order.survey_data['scheme_config']`` и ``order.parsed_params``
    для подбора шаблона и генерации PDF. Сохраняет файл в хранилище и создаёт
    запись ``OrderFile(category=HEAT_SCHEME)``.

    Args:
        session: Синхронная SQLAlchemy-сессия (Celery-воркер).
        order: Инстанс Order с загруженными связями.

    Returns:
        True при успехе, False если конфигурация невалидна или произошла ошибка.
        Не пробрасывает исключения — ошибки логируются.
    """
    try:
        from app.schemas.scheme import SchemeConfig
        from app.services.scheme_gost_frame import gost_frame_a3
        from app.services.scheme_service import (
            extract_scheme_params_from_parsed,
            resolve_scheme_type,
        )
        from app.services.scheme_svg_renderer import render_scheme

        if not order.survey_data or "scheme_config" not in order.survey_data:
            logger.info(
                "auto_generate_scheme: order=%s пропуск, нет scheme_config",
                order.id,
            )
            return False

        raw_cfg = dict(order.survey_data["scheme_config"])
        raw_cfg.pop("scheme_type", None)
        raw_cfg.pop("generated_at", None)
        scheme_config = SchemeConfig(**raw_cfg)

        scheme_type = resolve_scheme_type(scheme_config)
        if scheme_type is None:
            logger.error(
                "auto_generate_scheme: order=%s невалидная комбинация: %s",
                order.id,
                raw_cfg,
            )
            return False

        params = extract_scheme_params_from_parsed(order.parsed_params or {})
        if not params.project_number:
            params.project_number = f"УУТЭ-{str(order.id)[:8].upper()}"
        if not params.object_address and order.object_address:
            params.object_address = order.object_address
        if not params.company_name and order.client_organization:
            params.company_name = order.client_organization

        scheme_svg = render_scheme(scheme_type, params)

        stamp_data = {
            "project_number": params.project_number or "",
            "object_name": params.object_address or "",
            "sheet_name": "Схема функциональная",
            "sheet_title": "Узел учета тепловой энергии",
            "company": params.company_name or "",
            "gip": "",
            "executor": params.engineer_name or "",
            "inspector": "",
            "stage": "П",
            "sheet_num": "1",
            "total_sheets": "1",
            "format": "A3",
        }

        svg_with_frame = gost_frame_a3(scheme_svg, stamp_data)
        pdf_bytes = render_scheme_pdf(svg_with_frame, stamp_data, "A3")

        file_uuid = uuid.uuid4().hex[:12]
        filename = f"heat_scheme_{file_uuid}.pdf"
        relative_path = f"{order.id}/heat_scheme/{filename}"
        full_path = settings.upload_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as fh:
            fh.write(pdf_bytes)

        order_file = OrderFile(
            order_id=order.id,
            category=FileCategory.HEAT_SCHEME,
            original_filename=filename,
            storage_path=relative_path,
            content_type="application/pdf",
            file_size=len(pdf_bytes),
        )
        session.add(order_file)

        if order.survey_data is None:
            order.survey_data = {}
        order.survey_data.setdefault("scheme_config", {})
        order.survey_data["scheme_config"]["scheme_type"] = scheme_type.value
        order.survey_data["scheme_config"]["auto_generated"] = True

        session.commit()

        logger.info(
            "auto_generate_scheme: order=%s успех, файл=%s",
            order.id,
            filename,
        )
        return True

    except Exception as exc:
        logger.error(
            "auto_generate_scheme: order=%s ошибка: %s",
            order.id,
            exc,
            exc_info=True,
        )
        try:
            session.rollback()
        except Exception:
            pass
        return False
```

- [ ] **Step 4: Запустить тесты — должны пройти**

Run: `cd backend && python -m pytest tests/test_scheme_auto_generation.py::TestAutoGenerateScheme -v`

Expected: Все 4 теста PASS.

- [ ] **Step 5: Коммит**

```bash
git add backend/app/services/tasks.py backend/tests/test_scheme_auto_generation.py
git commit -m "feat(schemes): добавлена функция автогенерации _auto_generate_scheme_if_configured"
```

---

## Task 3: Интегрировать автогенерацию в `process_client_response`

**Files:**
- Modify: `backend/app/services/tasks.py:614-662` (функция `process_client_response`)
- Modify: `backend/app/services/tasks.py:400-456` (функция `check_data_completeness`)

**Контекст:**
- `process_client_response` вызывает `compute_client_document_missing(uploaded_categories)` — нужно передать `order.survey_data`.
- Автогенерация выполняется **перед** вычислением missing, чтобы `heat_scheme` уже был в `uploaded_categories`.
- `check_data_completeness` вызывается раньше (после парсинга ТУ) и тоже должна учитывать автогенерацию, но там реального клиентского ввода ещё нет — просто пробрасываем `survey_data` в `compute_client_document_missing`.

- [ ] **Step 1: Написать интеграционный тест**

Добавить в `backend/tests/test_scheme_auto_generation.py`:

```python
class TestProcessClientResponseIntegration:
    """Интеграционные тесты: process_client_response + автогенерация."""

    def test_heat_scheme_not_in_missing_when_auto_generated(self, tmp_path, monkeypatch):
        """После успешной автогенерации heat_scheme отсутствует в missing_params."""
        from app.services import tasks

        monkeypatch.setattr(tasks.settings, "upload_dir", tmp_path)

        session = MagicMock()
        order = MagicMock()
        order.id = uuid.uuid4()
        order.survey_data = {
            "scheme_config": {
                "connection_type": "dependent",
                "has_valve": False,
                "has_gwp": False,
                "has_ventilation": False,
            }
        }
        order.parsed_params = {}
        order.object_address = "ул. Ленина"
        order.client_organization = "ООО"

        existing_files = [
            MagicMock(category=MagicMock(value="BALANCE_ACT")),
            MagicMock(category=MagicMock(value="CONNECTION_PLAN")),
            MagicMock(category=MagicMock(value="heat_point_plan")),
            MagicMock(category=MagicMock(value="company_card")),
        ]
        order.files = list(existing_files)

        def fake_add(obj):
            order.files.append(MagicMock(category=MagicMock(value="heat_scheme")))

        session.add.side_effect = fake_add

        with patch.object(tasks, "render_scheme_pdf", return_value=b"%PDF"):
            success = tasks._auto_generate_scheme_if_configured(session, order)

        assert success is True
        uploaded = {f.category.value for f in order.files}
        assert "heat_scheme" in uploaded

        from app.services.param_labels import compute_client_document_missing

        missing = compute_client_document_missing(uploaded, order.survey_data)
        assert "heat_scheme" not in missing
```

- [ ] **Step 2: Запустить тест — должен пройти (проверка связности модулей)**

Run: `cd backend && python -m pytest tests/test_scheme_auto_generation.py::TestProcessClientResponseIntegration -v`

Expected: PASS (использует функции, реализованные в Task 1 и Task 2).

- [ ] **Step 3: Обновить `process_client_response`**

В `backend/app/services/tasks.py` заменить фрагмент начиная со строки `uploaded_categories = {f.category.value for f in order.files}` до `order.missing_params = missing` внутри `process_client_response`:

**Найти:**
```python
        uploaded_categories = {f.category.value for f in order.files}
        missing = compute_client_document_missing(uploaded_categories)
        if (
            FileCategory.COMPANY_CARD.value not in uploaded_categories
            and FileCategory.COMPANY_CARD.value not in missing
        ):
            missing.append(FileCategory.COMPANY_CARD.value)
        order.missing_params = missing
        session.commit()
```

**Заменить на:**
```python
        uploaded_categories = {f.category.value for f in order.files}

        if (
            order.survey_data
            and "scheme_config" in order.survey_data
            and FileCategory.HEAT_SCHEME.value not in uploaded_categories
        ):
            if _auto_generate_scheme_if_configured(session, order):
                session.refresh(order)
                uploaded_categories = {f.category.value for f in order.files}

        missing = compute_client_document_missing(
            uploaded_categories, order.survey_data
        )
        if (
            FileCategory.COMPANY_CARD.value not in uploaded_categories
            and FileCategory.COMPANY_CARD.value not in missing
        ):
            missing.append(FileCategory.COMPANY_CARD.value)
        order.missing_params = missing
        session.commit()
```

- [ ] **Step 4: Обновить `check_data_completeness`**

В `backend/app/services/tasks.py` найти строку в `check_data_completeness`:

```python
        uploaded_categories = {f.category.value for f in order.files}
        missing = compute_client_document_missing(uploaded_categories)
```

Заменить на:

```python
        uploaded_categories = {f.category.value for f in order.files}
        missing = compute_client_document_missing(
            uploaded_categories, order.survey_data
        )
```

- [ ] **Step 5: Проверить, что существующие тесты не сломались**

Run: `cd backend && python -m pytest tests/ -v`

Expected: Все тесты PASS. Если `test_tu_parsed_engineer_notification.py` падает из-за изменения сигнатуры — значит `compute_client_document_missing` вызывается с позиционным аргументом, что допустимо (см. mock в test_tu_parsed_engineer_notification.py:48-51 — он мокает функцию целиком, сигнатура не затрагивается).

- [ ] **Step 6: Коммит**

```bash
git add backend/app/services/tasks.py backend/tests/test_scheme_auto_generation.py
git commit -m "feat(schemes): автогенерация схемы в process_client_response и check_data_completeness"
```

---

## Task 4: Отображение конфигурации схемы в админ-панели

**Files:**
- Modify: `backend/static/admin.html:2083` (вызов `renderParsedParams`)
- Modify: `backend/static/admin.html:2401-2450` (функция `renderParsedParams`)
- Modify: `backend/static/admin.html` — добавить новую функцию `renderSchemeConfigSection` перед `renderParsedParams`

**Контекст:**
- Функция `renderParsedParams(params, missing)` вызывается со строки 2083 как `renderParsedParams(order.parsed_params, order.missing_params)`.
- Для отображения секции схемы нужен доступ к `order.survey_data` и `order.files`.
- Расширяем сигнатуру: `renderParsedParams(params, missing, surveyData, files)`.

- [ ] **Step 1: Добавить функцию `renderSchemeConfigSection` перед `renderParsedParams`**

В файле `backend/static/admin.html` найти строку `function renderParsedParams(params, missing) {` (строка 2401) и **перед** ней вставить:

```javascript
    function renderSchemeConfigSection(schemeConfig, files) {
      if (!schemeConfig || typeof schemeConfig !== 'object') return '';

      const connectionType = schemeConfig.connection_type;
      const typeLabel = connectionType === 'dependent'
        ? 'Зависимая'
        : connectionType === 'independent' ? 'Независимая' : '—';

      let valveLabel = 'Нет';
      if (schemeConfig.has_valve) {
        valveLabel = connectionType === 'dependent'
          ? 'Да (3-ходовой с насосом на перемычке)'
          : 'Да (2-ходовой с насосом)';
      }

      const gwpLabel = schemeConfig.has_gwp ? 'Да' : 'Нет';
      const ventLabel = schemeConfig.has_ventilation ? 'Да' : 'Нет';

      const schemeFile = (files || []).find(f => f.category === 'heat_scheme');
      const statusLabel = schemeFile
        ? '\u2713 Сгенерирована'
        : '\u23F3 Ожидает генерации';

      const rows = [
        parsedTableRow('Тип присоединения', `<td class="parsed-value-cell"><span class="parsed-value">${esc(typeLabel)}</span></td>`),
        parsedTableRow('Регулирующий клапан', `<td class="parsed-value-cell"><span class="parsed-value">${esc(valveLabel)}</span></td>`),
        parsedTableRow('Система ГВС', `<td class="parsed-value-cell"><span class="parsed-value">${esc(gwpLabel)}</span></td>`),
        parsedTableRow('Вентиляция (параллельная)', `<td class="parsed-value-cell"><span class="parsed-value">${esc(ventLabel)}</span></td>`),
        parsedTableRow('Статус PDF', `<td class="parsed-value-cell"><span class="parsed-value">${esc(statusLabel)}</span></td>`),
      ];

      let sectionHtml = parsedSectionHtml('Конфигурация схемы', rows);

      if (schemeFile) {
        const downloadUrl = `${API_BASE}/admin/files/${schemeFile.id}/download`;
        sectionHtml += `
          <div style="margin-top:10px;">
            <a href="${downloadUrl}"
               class="btn btn-primary btn-sm"
               style="font-size:12px; padding:6px 14px;"
               target="_blank"
               onclick="this.href = addKeyToUrl(this.href)">
              \u2193 Скачать PDF схемы
            </a>
          </div>
        `;
      }

      return sectionHtml;
    }
```

- [ ] **Step 2: Расширить сигнатуру `renderParsedParams` и встроить новую секцию**

В той же строке найти:

```javascript
    function renderParsedParams(params, missing) {
      const card = document.getElementById('parsedCard');
      const content = document.getElementById('parsedContent');
      card.style.display = 'block';

      const empty = isParsedParamsEmpty(params);
```

Заменить сигнатуру и сразу после неё добавить вывод секции конфигурации (см. результат в Step 3).

- [ ] **Step 3: Применить полный патч для `renderParsedParams`**

Полная новая версия функции (заменяем строки 2401-2450):

```javascript
    function renderParsedParams(params, missing, surveyData, files) {
      const card = document.getElementById('parsedCard');
      const content = document.getElementById('parsedContent');
      card.style.display = 'block';

      const empty = isParsedParamsEmpty(params);
      const warnings = (!empty && params.warnings) ? params.warnings : [];
      const confidence = !empty ? params.parse_confidence : undefined;

      let html = '';

      if (confidence !== undefined && confidence !== null) {
        const pct = Math.round(Number(confidence) * 100);
        const color = pct >= 80 ? '#16a34a' : pct >= 60 ? '#d97706' : '#dc2626';
        html += `
          <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
            <span style="font-size:13px; color:var(--c-text-secondary);">\u0423\u0432\u0435\u0440\u0435\u043d\u043d\u043e\u0441\u0442\u044c \u043f\u0430\u0440\u0441\u0438\u043d\u0433\u0430:</span>
            <span style="font-size:18px; font-weight:700; color:${color};">${pct}%</span>
          </div>
        `;
      }

      if (empty) {
        html += '<p class="parsed-empty-msg">\u041f\u0430\u0440\u0441\u0438\u043d\u0433 \u043d\u0435 \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d</p>';
      } else {
        html += buildParsedParamsTablesHtml(params);
      }

      if (surveyData && surveyData.scheme_config) {
        html += renderSchemeConfigSection(surveyData.scheme_config, files || []);
      }

      if (missing && missing.length > 0) {
        html += `
          <div style="margin-top:14px;">
            <div style="font-size:13px; font-weight:600; color:var(--c-warn); margin-bottom:8px;">
              \u041d\u0435\u0434\u043e\u0441\u0442\u0430\u044e\u0449\u0438\u0435 \u0434\u0430\u043d\u043d\u044b\u0435 (${missing.length}):
            </div>
            <div style="font-size:13px; color:var(--c-text-secondary);">${missing.map(esc).join(', ')}</div>
          </div>
        `;
      }

      if (warnings.length > 0) {
        html += `
          <div class="warnings-list" style="margin-top:14px;">
            <div style="font-size:13px; font-weight:600; color:var(--c-warn); margin-bottom:6px;">\u041f\u0440\u0435\u0434\u0443\u043f\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u044f:</div>
            ${warnings.map(w => `<div class="warning-item">${esc(w)}</div>`).join('')}
          </div>
        `;
      }

      content.innerHTML = html;
    }
```

- [ ] **Step 4: Обновить вызов `renderParsedParams` в строке ~2083**

Найти в `backend/static/admin.html`:

```javascript
        renderParsedParams(order.parsed_params, order.missing_params);
```

Заменить на:

```javascript
        renderParsedParams(order.parsed_params, order.missing_params, order.survey_data, order.files);
```

- [ ] **Step 5: Ручное тестирование в браузере**

1. Запустить backend: `cd backend && uvicorn app.main:app --reload`
2. Открыть админку: `http://localhost:8000/admin.html?_k=<api_key>`
3. Выбрать заявку, у которой:
   - **Случай A:** есть `survey_data.scheme_config` и файл `heat_scheme` → секция отображается со статусом "✓ Сгенерирована" и кнопкой скачивания.
   - **Случай B:** есть `survey_data.scheme_config`, нет файла `heat_scheme` → секция отображается со статусом "⏳ Ожидает генерации" без кнопки.
   - **Случай C:** нет `survey_data.scheme_config` → секция отсутствует.
4. Проверить, что остальные секции `parsed_params` рендерятся как раньше.

Зафиксировать: "[x] UI tested manually — case A / B / C verified".

- [ ] **Step 6: Коммит**

```bash
git add backend/static/admin.html
git commit -m "feat(admin): отображение конфигурации схемы в карточке parsed_params"
```

---

## Task 5: Обновить документацию

**Files:**
- Modify: `docs/changelog.md`
- Modify: `docs/tasktracker.md`
- Modify: `docs/project.md`
- Modify: `docs/scheme-generator-roadmap.md:300-310` (отметить задачу 7 как выполненную)

- [ ] **Step 1: Добавить запись в `docs/changelog.md`**

Вставить в начало раздела с датами:

```markdown
## [2026-04-23] - Интеграция конфигуратора схем с пайплайном и админкой

### Добавлено
- Автоматическая генерация PDF схемы в `process_client_response`, если клиент заполнил конфигуратор, но PDF ещё не сгенерирован
- Секция "Конфигурация схемы" в админ-панели (parsed_params) с маппингом параметров на русский и кнопкой скачивания PDF
- Тесты `backend/tests/test_scheme_auto_generation.py`

### Изменено
- `compute_client_document_missing(uploaded_categories, survey_data=None)` — второй аргумент исключает `heat_scheme` из missing при наличии `scheme_config`
- `process_client_response` и `check_data_completeness` передают `order.survey_data` в `compute_client_document_missing`
- `renderParsedParams(params, missing, surveyData, files)` — расширенная сигнатура

### Исправлено
- Клиенты больше не обязаны вручную загружать PDF схемы, если заполнили конфигуратор
```

- [ ] **Step 2: Обновить `docs/tasktracker.md`**

Добавить запись:

```markdown
## Задача: Интеграция конфигуратора схем (roadmap задача 7)
- **Статус**: Завершена
- **Описание**: Автогенерация PDF схемы в пайплайне + отображение конфигурации в админке + исключение heat_scheme из missing при наличии scheme_config
- **Шаги выполнения**:
  - [x] Обновлена сигнатура `compute_client_document_missing(uploaded_categories, survey_data=None)`
  - [x] Добавлена функция `_auto_generate_scheme_if_configured` в `tasks.py`
  - [x] Интеграция автогенерации в `process_client_response`
  - [x] Обновлён `check_data_completeness` — передача `survey_data`
  - [x] UI: новая секция "Конфигурация схемы" в админке
  - [x] Тесты: `backend/tests/test_scheme_auto_generation.py`
  - [x] Обновлена документация
- **Зависимости**: Задачи 1–6 roadmap
```

- [ ] **Step 3: Обновить `docs/project.md`**

Найти раздел про пайплайн обработки заявок (или создать блок "Пайплайн: автогенерация схемы"), добавить:

```markdown
### Автогенерация принципиальной схемы

В `process_client_response` (Celery-задача) перед вычислением `missing_params` выполняется проверка:

```
if order.survey_data.get('scheme_config') and 'heat_scheme' not in uploaded_categories:
    _auto_generate_scheme_if_configured(session, order)
```

Функция читает конфигурацию из `survey_data`, подбирает шаблон SVG (одна из 8 типовых схем), рендерит PDF через WeasyPrint и сохраняет как `OrderFile(category=HEAT_SCHEME)`. Ошибки не блокируют пайплайн — `heat_scheme` остаётся в `missing_params`, клиент получает стандартный запрос на ручную загрузку.

`compute_client_document_missing(uploaded_categories, survey_data)` исключает `heat_scheme` из списка обязательных документов при наличии `scheme_config`, даже если файл ещё не создан (автогенерация выполнится при обработке).
```

- [ ] **Step 4: Отметить задачу 7 в roadmap**

В `docs/scheme-generator-roadmap.md` найти блок задачи 7 (строка 300) и заменить статус:

**Найти:**
```markdown
### Задача 7: Интеграция с пайплайном и админкой
- **Статус**: Не начата
```

**Заменить на:**
```markdown
### Задача 7: Интеграция с пайплайном и админкой ✅
- **Статус**: Завершена (2026-04-23)
```

Также отметить чекбоксы шагов:

**Найти:**
```markdown
- **Шаги**:
  - [ ] `admin.html`: в карточке файлов показывать «Схема: сгенерирована (конфиг: зависимая, ГВС, без вент.)»
  - [ ] `admin.html`: ссылка на скачивание PDF схемы
  - [ ] `tasks.py`: при `process_client_response` если `scheme_config` в survey_data и нет файла heat_scheme → авто-генерация
  - [ ] Обновить `compute_client_document_missing` — не требовать `heat_scheme` если схема сгенерирована
```

**Заменить на:**
```markdown
- **Шаги**:
  - [x] `admin.html`: секция "Конфигурация схемы" в parsed_params с маппингом параметров
  - [x] `admin.html`: ссылка на скачивание PDF схемы
  - [x] `tasks.py`: автогенерация в `process_client_response` и `check_data_completeness`
  - [x] `param_labels.py`: `compute_client_document_missing` учитывает `scheme_config`
```

- [ ] **Step 5: Коммит документации**

```bash
git add docs/changelog.md docs/tasktracker.md docs/project.md docs/scheme-generator-roadmap.md
git commit -m "docs: задача 7 — интеграция конфигуратора схем с пайплайном и админкой"
```

---

## Task 6: Финальная проверка

- [ ] **Step 1: Запустить полный прогон тестов**

Run: `cd backend && python -m pytest tests/ -v`

Expected: Все тесты PASS, включая новые из `test_scheme_auto_generation.py`.

- [ ] **Step 2: Проверить линтер**

Run:
```bash
cd backend && python -m ruff check app/services/param_labels.py app/services/tasks.py
python -m ruff check tests/test_scheme_auto_generation.py
```

Expected: Нет ошибок (или только существующие, не связанные с изменениями).

- [ ] **Step 3: Проверить импорты**

Run: `cd backend && python -c "from app.services import tasks; print('ok')"`

Expected: `ok` без ошибок импорта.

- [ ] **Step 4: Проверить историю коммитов**

Run: `git log --oneline -10`

Expected: Видны коммиты Task 1–5 в правильном порядке.

---

## Приложение: Проверочный список спецификации

Сверка с `docs/superpowers/specs/2026-04-23-scheme-generator-admin-integration-design.md`:

| Требование спецификации | Таск |
|-------------------------|------|
| Автогенерация в `process_client_response` | Task 3 |
| Функция `_auto_generate_scheme_if_configured` | Task 2 |
| Обработка ошибок без блокировки пайплайна | Task 2 (try/except + False) |
| `compute_client_document_missing(survey_data)` | Task 1 |
| Обновление всех вызовов `compute_client_document_missing` | Task 3 (tasks.py) |
| Секция "Конфигурация схемы" в админке | Task 4 |
| Маппинг значений на русский | Task 4 |
| Статус генерации и кнопка скачивания | Task 4 |
| Модульные тесты для автогенерации | Task 2 |
| Модульные тесты для `compute_client_document_missing` | Task 1 |
| Интеграционный тест | Task 3 (Step 1) |
| Обновление changelog, tasktracker, project.md, roadmap | Task 5 |
