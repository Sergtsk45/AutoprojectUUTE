# Задача: Сопроводительное письмо в РСО при отправке готового проекта

- **Статус**: Завершена
- **Описание**: При отправке готового проекта клиенту автоматически генерировать файл `.docx` — предзаполненное сопроводительное письмо в РСО (ресурсоснабжающую организацию). Данные о заявителе уже извлекаются из ТУ парсером. Тело email изменить: добавить требование оплатить в течение 2 дней или прислать скан сопроводительного письма с входящим номером РСО.

- **Шаги выполнения**:
  - [x] Добавить `python-docx` в `backend/requirements.txt`
  - [x] Создать `backend/app/services/cover_letter.py` — генерация DOCX из `TUParsedData`
  - [x] Обновить `backend/templates/emails/project_delivery.html` — добавить секцию с требованием оплаты / скана
  - [x] Обновить `render_project_delivery` в `email_service.py` — передать новый контекст в шаблон (изменений не потребовалось)
  - [x] Обновить `send_completed_project` в `tasks.py` — генерировать docx, прикладывать к письму

- **Зависимости**: Парсинг ТУ (`applicant.*`, `rso.*`) уже работает — данные хранятся в `order.parsed_params`

---

## Детальный план реализации

### Анализ текущего состояния

- `tu_schema.py`: `ApplicantInfo` (заявитель — тот, кто запросил ТУ) и `RSOInfo` (РСО — та, кто выдала ТУ) уже существуют и заполняются LLM при парсинге.
- `order.parsed_params` — JSONB, содержит полный дамп `TUParsedData` без `raw_text`.
- `send_completed_project` в `tasks.py` — точка интеграции.
- `render_project_delivery` + `project_delivery.html` — шаблон письма клиенту.
- `python-docx` — не установлен, нужно добавить.

---

### Task 1: Добавить зависимость python-docx

**Файлы:**
- Modify: `backend/requirements.txt`

- [ ] Добавить строку `python-docx==1.1.2` в `backend/requirements.txt` после `PyMuPDF`

---

### Task 2: Создать генератор сопроводительного письма

**Файлы:**
- Create: `backend/app/services/cover_letter.py`

- [ ] Создать файл `backend/app/services/cover_letter.py` со следующим содержимым:

```python
"""Генератор сопроводительного письма в РСО (.docx).

Создаёт предзаполненный шаблон письма для клиента:
  - отправитель: заявитель (данные из ТУ)
  - получатель: РСО (данные из ТУ)
  - тема: направление проекта УУТЭ на согласование
  - оставляет пустые поля для исходящего номера и даты
"""

import tempfile
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.services.tu_schema import TUParsedData


def generate_cover_letter(parsed: TUParsedData, order_id_short: str) -> Path:
    """Генерирует DOCX сопроводительного письма в РСО.

    Args:
        parsed: Извлечённые данные из ТУ (содержат applicant и rso).
        order_id_short: Первые 8 символов UUID заявки (для имени файла).

    Returns:
        Path к временному .docx файлу. Вызывающий код обязан удалить файл после отправки.
    """
    doc = Document()

    # Поля страницы
    section = doc.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)

    # ── Шапка: реквизиты отправителя (правый столбец) ───────────────────
    applicant_name = parsed.applicant.applicant_name or "________________________"
    applicant_address = parsed.applicant.applicant_address or "________________________"
    contact_person = parsed.applicant.contact_person or "________________________"

    rso_name = parsed.rso.rso_name or "________________________"
    rso_address = parsed.rso.rso_address or "________________________"

    tu_number = parsed.document.tu_number or "___"
    tu_date = parsed.document.tu_date or "________"
    object_address = parsed.object.object_address or "________________________"

    # Блок "Кому"
    to_para = doc.add_paragraph()
    to_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = to_para.add_run(f"{rso_name}\n{rso_address}")
    run.font.size = Pt(12)

    doc.add_paragraph()  # отступ

    # Блок "От кого"
    from_para = doc.add_paragraph()
    from_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = from_para.add_run(f"От: {applicant_name}\n{applicant_address}")
    run.font.size = Pt(12)

    doc.add_paragraph()  # отступ

    # ── Исходящий номер и дата ───────────────────────────────────────────
    meta_para = doc.add_paragraph()
    meta_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = meta_para.add_run("Исх. № __________ от «____» ____________ 20___ г.")
    run.font.size = Pt(12)

    doc.add_paragraph()

    # ── Заголовок письма ─────────────────────────────────────────────────
    subj_para = doc.add_paragraph()
    subj_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subj_para.add_run(
        "О направлении проекта узла учёта тепловой энергии (УУТЭ) на согласование"
    )
    run.bold = True
    run.font.size = Pt(13)

    doc.add_paragraph()

    # ── Тело письма ──────────────────────────────────────────────────────
    body_text = (
        f"В соответствии с Приказом Минстроя России №\u202f1036/пр "
        f"«Правила коммерческого учёта тепловой энергии, теплоносителя», "
        f"а также техническими условиями № {tu_number} от {tu_date}, "
        f"выданными {rso_name}, направляем на согласование проект "
        f"узла учёта тепловой энергии (УУТЭ) по объекту:\n\n"
        f"{object_address}.\n\n"
        f"Просим рассмотреть представленный проект и согласовать его "
        f"в установленные сроки в соответствии с действующим законодательством.\n\n"
        f"По вопросам согласования просим обращаться: {contact_person}."
    )

    body_para = doc.add_paragraph()
    body_para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = body_para.add_run(body_text)
    run.font.size = Pt(12)

    doc.add_paragraph()
    doc.add_paragraph()

    # ── Подпись ──────────────────────────────────────────────────────────
    sign_para = doc.add_paragraph()
    sign_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = sign_para.add_run(
        f"{contact_person or applicant_name}\n\n"
        "Подпись: ______________________\n\n"
        "М.П."
    )
    run.font.size = Pt(12)

    # ── Сохранить во временный файл ──────────────────────────────────────
    tmp = tempfile.NamedTemporaryFile(
        suffix=".docx",
        prefix=f"soprovod_{order_id_short}_",
        delete=False,
    )
    tmp.close()
    doc.save(tmp.name)

    return Path(tmp.name)
```

- [ ] Убедиться, что файл сохранён корректно (проверить импорты вручную).

---

### Task 3: Обновить HTML-шаблон письма «Проект готов»

**Файлы:**
- Modify: `backend/templates/emails/project_delivery.html`

- [ ] Заменить секцию «Дальнейшие действия» на новый текст с требованием оплаты/скана:

```html
{% extends "emails/base.html" %}

{% block content %}
<p>{{ client_name }}, здравствуйте!</p>

<p>Проект узла учёта тепловой энергии по адресу
<strong>{{ object_address or "—" }}</strong> готов.</p>

<h2>Состав проекта</h2>
<div class="list-block">
  <ul>
  {% for doc in project_documents %}
    <li>{{ doc }}</li>
  {% endfor %}
  </ul>
</div>

{% if download_url %}
<p>Скачайте проект по ссылке:</p>
<div class="btn-center">
  <a href="{{ download_url }}" class="btn">Скачать проект</a>
</div>
{% endif %}

{% if has_attachments %}
<p>Проектная документация и сопроводительное письмо приложены к этому письму.</p>
{% endif %}

<h2>Дальнейшие действия</h2>
<p>К письму приложено предзаполненное <strong>сопроводительное письмо</strong>
в ресурсоснабжающую организацию. Вам необходимо:</p>

<div class="list-block">
  <ul>
    <li>Распечатать сопроводительное письмо, подписать и поставить печать.</li>
    <li>Передать его вместе с проектом в РСО для согласования.</li>
    <li>После получения согласования — прислать нам скан письма
        с входящим номером РСО.</li>
  </ul>
</div>

<div class="note" style="background:#fff8e1; border-left: 4px solid #f59e0b; padding: 12px 16px; margin: 16px 0;">
  <strong>Оплата услуг:</strong> просим произвести оплату в течение
  <strong>2 рабочих дней</strong> с момента получения проекта
  <em>или</em> прислать скан сопроводительного письма с входящим
  номером ресурсоснабжающей организации.
</div>

<div class="note">
  Проект выполнен в соответствии с Приказом Минстроя России
  №1036/пр (Правила коммерческого учёта тепловой энергии).
</div>
{% endblock %}
```

---

### Task 4: Обновить `render_project_delivery` в `email_service.py`

**Файлы:**
- Modify: `backend/app/services/email_service.py:125-148`

- [ ] Убедиться что `has_attachments` в контексте учитывает сопроводительное письмо.
  Изменение минимально — логика `has_attachments = len(attachments) > 0` уже корректна,
  так как docx будет добавлен в `attachment_paths` до вызова `render_project_delivery`.
  Никаких изменений в `email_service.py` не требуется — шаблон получает `has_attachments=True`
  автоматически при наличии вложений.

---

### Task 5: Обновить `send_completed_project` в `tasks.py`

**Файлы:**
- Modify: `backend/app/services/tasks.py:396-448`

- [ ] Заменить тело `send_completed_project` на следующее:

```python
@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_completed_project(self, order_id: str):
    """REVIEW → COMPLETED: Отправка готового проекта клиенту.

    Находит сгенерированный PDF проекта в файлах заявки,
    генерирует DOCX сопроводительного письма в РСО,
    отправляет клиенту письмом с вложениями.
    """
    import os
    from app.services.email_service import send_project
    from app.services.cover_letter import generate_cover_letter
    from app.services.tu_schema import TUParsedData

    oid = uuid.UUID(order_id)
    order_id_short = order_id[:8]
    logger.info("send_completed_project: order=%s", oid)

    cover_letter_path = None

    with SyncSession() as session:
        order = _get_order(session, oid)
        if order is None:
            return

        # Собираем PDF-файлы проекта для вложения
        project_files = [
            f for f in order.files
            if f.category.value == "generated_project"
        ]
        attachment_paths = [
            str(settings.upload_dir / f.storage_path)
            for f in project_files
            if (settings.upload_dir / f.storage_path).exists()
        ]

        if not attachment_paths:
            logger.warning(
                "send_completed_project: order=%s — нет вложений (записи generated_project в БД: %s, "
                "файлы на диске отсутствуют или пути неверны)",
                oid,
                len(project_files),
            )

        # Генерируем сопроводительное письмо из parsed_params
        try:
            if order.parsed_params:
                parsed = TUParsedData.model_validate(order.parsed_params)
                cover_letter_path = generate_cover_letter(parsed, order_id_short)
                attachment_paths.append(str(cover_letter_path))
                logger.info(
                    "send_completed_project: сопроводительное письмо создано: %s",
                    cover_letter_path,
                )
            else:
                logger.warning(
                    "send_completed_project: order=%s — parsed_params пуст, "
                    "сопроводительное письмо не создано",
                    oid,
                )
        except Exception as e:
            logger.error(
                "send_completed_project: ошибка генерации сопроводительного письма "
                "для order=%s: %s",
                oid,
                e,
                exc_info=True,
            )
            # Не прерываем отправку — продолжаем без письма

        success = send_project(
            session, order,
            attachment_paths=attachment_paths,
        )

        if success:
            _transition(session, order, OrderStatus.COMPLETED)
            logger.info("Проект отправлен клиенту: order=%s", oid)
        else:
            logger.error("Не удалось отправить проект для order=%s", oid)
            try:
                self.retry()
            except self.MaxRetriesExceededError:
                logger.error(
                    "Исчерпаны попытки отправки проекта для order=%s", oid
                )

    # Удаляем временный файл после сессии (независимо от успеха/неуспеха)
    if cover_letter_path and cover_letter_path.exists():
        try:
            cover_letter_path.unlink()
        except OSError as e:
            logger.warning("Не удалось удалить временный файл %s: %s", cover_letter_path, e)
```

---

### Task 6: Пересборка и проверка

- [ ] Добавить `python-docx==1.1.2` в `requirements.txt` и пересобрать образ:
  ```bash
  docker compose -f docker-compose.prod.yml up -d --build backend celery-worker
  ```
- [ ] Проверить логи после пересборки:
  ```bash
  docker logs uute-backend --tail 20
  docker logs uute-project-celery-worker-1 --tail 20
  ```
- [ ] Вручную запустить `send_completed_project` для тестовой заявки через Celery:
  ```python
  # в python shell внутри контейнера
  from app.services.tasks import send_completed_project
  send_completed_project.delay("<order_id>")
  ```
- [ ] Убедиться что письмо получено с двумя вложениями: PDF проекта + .docx письмо.

---

## Примечания

- `ApplicantInfo` и `RSOInfo` уже извлекаются LLM при парсинге ТУ — изменений в `tu_parser.py` и `tu_schema.py` не требуется.
- Если у заявки пустой `parsed_params` (ошибка парсинга) — письмо отправляется без docx (degraded mode).
- Временный файл docx удаляется после отправки (вне `SyncSession`, чтобы session не держала файл).
- Поля исходящего номера и даты оставлены пустыми — клиент заполняет их вручную перед сдачей в РСО.
