# Cover Letter (Сопроводительное письмо) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** При отправке готового проекта клиенту автоматически генерировать DOCX-сопроводительное письмо в РСО и обновить тело email с требованием оплаты/скана.

**Architecture:** `generate_cover_letter()` создаёт временный `.docx` из `TUParsedData` через `python-docx`; файл прикладывается к письму в `send_completed_project`; временный файл удаляется после отправки. Данные заявителя и РСО уже парсятся LLM из ТУ — изменений в парсере не требуется.

**Tech Stack:** python-docx 1.1.2, Jinja2 (HTML email), Celery (tasks.py), SQLAlchemy sync session.

---

## File Map

| Файл | Действие | Назначение |
|------|----------|-----------|
| `backend/requirements.txt` | Modify | Добавить python-docx |
| `backend/app/services/cover_letter.py` | Create | Генерация DOCX письма |
| `backend/templates/emails/project_delivery.html` | Modify | Новый текст: оплата/скан |
| `backend/app/services/tasks.py:396-448` | Modify | Генерация docx + вложение |

---

### Task 1: Добавить python-docx в зависимости

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Добавить строку в requirements.txt**

```
python-docx==1.1.2
```

После строки `PyMuPDF==1.25.1`.

- [ ] **Step 2: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore(deps): add python-docx for cover letter generation"
```

---

### Task 2: Создать генератор DOCX-письма

**Files:**
- Create: `backend/app/services/cover_letter.py`

- [ ] **Step 1: Создать файл**

```python
"""Генератор сопроводительного письма в РСО (.docx).

Создаёт предзаполненный шаблон письма:
  - отправитель: заявитель (данные из ТУ — applicant.*)
  - получатель: РСО (данные из ТУ — rso.*)
  - поля исходящего номера/даты — пустые, клиент заполняет вручную
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
        parsed: Извлечённые данные из ТУ.
        order_id_short: Первые 8 символов UUID заявки (для имени файла).

    Returns:
        Path к временному .docx. Вызывающий код удаляет файл после отправки.
    """
    doc = Document()

    section = doc.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)

    applicant_name = parsed.applicant.applicant_name or "________________________"
    applicant_address = parsed.applicant.applicant_address or "________________________"
    contact_person = parsed.applicant.contact_person or "________________________"
    rso_name = parsed.rso.rso_name or "________________________"
    rso_address = parsed.rso.rso_address or "________________________"
    tu_number = parsed.document.tu_number or "___"
    tu_date = parsed.document.tu_date or "________"
    object_address = parsed.object.object_address or "________________________"

    # Кому
    to_para = doc.add_paragraph()
    to_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = to_para.add_run(f"{rso_name}\n{rso_address}")
    run.font.size = Pt(12)

    doc.add_paragraph()

    # От кого
    from_para = doc.add_paragraph()
    from_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = from_para.add_run(f"От: {applicant_name}\n{applicant_address}")
    run.font.size = Pt(12)

    doc.add_paragraph()

    # Исходящий №
    meta_para = doc.add_paragraph()
    meta_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = meta_para.add_run("Исх. № __________ от «____» ____________ 20___ г.")
    run.font.size = Pt(12)

    doc.add_paragraph()

    # Заголовок
    subj_para = doc.add_paragraph()
    subj_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subj_para.add_run(
        "О направлении проекта узла учёта тепловой энергии (УУТЭ) на согласование"
    )
    run.bold = True
    run.font.size = Pt(13)

    doc.add_paragraph()

    # Тело
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

    # Подпись
    sign_para = doc.add_paragraph()
    sign_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = sign_para.add_run(
        f"{contact_person or applicant_name}\n\n"
        "Подпись: ______________________\n\n"
        "М.П."
    )
    run.font.size = Pt(12)

    tmp = tempfile.NamedTemporaryFile(
        suffix=".docx",
        prefix=f"soprovod_{order_id_short}_",
        delete=False,
    )
    tmp.close()
    doc.save(tmp.name)

    return Path(tmp.name)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/cover_letter.py
git commit -m "feat(cover-letter): add DOCX cover letter generator for RSO submission"
```

---

### Task 3: Обновить email-шаблон project_delivery.html

**Files:**
- Modify: `backend/templates/emails/project_delivery.html`

- [ ] **Step 1: Заменить содержимое файла**

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

- [ ] **Step 2: Commit**

```bash
git add backend/templates/emails/project_delivery.html
git commit -m "feat(email): update project_delivery template with payment/scan request and cover letter mention"
```

---

### Task 4: Обновить send_completed_project в tasks.py

**Files:**
- Modify: `backend/app/services/tasks.py:396-448`

- [ ] **Step 1: Заменить тело функции `send_completed_project`**

Найти функцию начиная со строки 396. Заменить полностью:

```python
@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def send_completed_project(self, order_id: str):
    """REVIEW → COMPLETED: Отправка готового проекта клиенту.

    Находит сгенерированный PDF проекта в файлах заявки,
    генерирует DOCX сопроводительного письма в РСО,
    отправляет клиенту письмом с вложениями.
    """
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
            # Degraded mode: отправляем без docx

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

    # Удаляем временный файл вне сессии
    if cover_letter_path and cover_letter_path.exists():
        try:
            cover_letter_path.unlink()
        except OSError as e:
            logger.warning("Не удалось удалить временный файл %s: %s", cover_letter_path, e)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/tasks.py
git commit -m "feat(pipeline): attach DOCX cover letter when sending completed project"
```

---

### Task 5: Пересборка и проверка

**Files:** нет изменений кода.

- [ ] **Step 1: Пересборка контейнеров**

```bash
cd ~/uute-project
git pull
docker compose -f docker-compose.prod.yml up -d --build backend celery-worker
```

- [ ] **Step 2: Проверить логи**

```bash
docker logs uute-backend --tail 30
docker logs uute-project-celery-worker-1 --tail 30
```
Ожидаемый результат: нет ошибок импорта, `python-docx` загружен.

- [ ] **Step 3: Протестировать вручную**

В контейнере celery-worker:
```bash
docker exec -it uute-project-celery-worker-1 python -c "
from app.services.cover_letter import generate_cover_letter
from app.services.tu_schema import TUParsedData, ApplicantInfo, RSOInfo, TUDocumentInfo, ObjectInfo
p = TUParsedData()
p.applicant.applicant_name = 'ООО Тест'
p.applicant.applicant_address = 'г. Москва, ул. Тестовая, 1'
p.applicant.contact_person = 'Иванов И.И.'
p.rso.rso_name = 'МУП Теплосеть'
p.rso.rso_address = 'г. Москва, пр. Энергетиков, 10'
p.document.tu_number = '123/2025'
p.document.tu_date = '01.03.2025'
p.object.object_address = 'г. Москва, ул. Строителей, 5'
path = generate_cover_letter(p, 'test1234')
print('OK:', path)
import os; os.unlink(path)
"
```
Ожидаемый результат: `OK: /tmp/soprovod_test1234_XXXX.docx`

---

## Итог

После выполнения всех задач:
- При вызове `POST /api/v1/pipeline/{id}/approve` → `send_completed_project` → клиент получит письмо с двумя вложениями: PDF проекта + DOCX сопроводительного письма в РСО.
- Тело письма содержит инструкцию и требование оплаты в течение 2 рабочих дней или скана с входящим номером.
- Если `parsed_params` пуст — письмо отправляется без docx (degraded mode, логируется warning).
