# DXF Scheme Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unacceptable programmatic drawing for `SchemeType.DEP_SIMPLE` with a template-based renderer that uses Sergey's DXF scheme as the visual source.

**Architecture:** Keep the existing question/configurator flow and PDF generation pipeline. Add a DXF-template renderer for the first scheme only (`dependent without valve/GVS/ventilation`), while the remaining seven schemes keep the current `scheme_svg_renderer.py` implementation until their source templates are provided.

**Tech Stack:** Python 3.12, FastAPI, WeasyPrint, existing SVG/PDF pipeline, `ezdxf` for reading/rendering the DXF source to SVG.

---

### Task 1: DXF Template Renderer

**Files:**
- Create: `backend/app/services/scheme_template_renderer.py`
- Create/Copy: `backend/templates/schemes/dxf/1_2_dep_simple.dxf`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_scheme_template_renderer.py`

- [ ] **Step 1: Add `ezdxf` dependency**

Add `ezdxf` to `backend/requirements.txt` after the existing PDF/vector dependencies.

- [ ] **Step 2: Add the DXF source template**

Use `docs/scheme/1_2_Сх_зависимая без ГВС без клапана коррект .dxf` as the source and place a runtime copy at:

`backend/templates/schemes/dxf/1_2_dep_simple.dxf`

- [ ] **Step 3: Write failing tests**

Create tests that verify:

- `render_template_scheme(SchemeType.DEP_SIMPLE, SchemeParams())` returns SVG content.
- The returned content contains an embedded `<svg`/`<g` payload and recognizable scheme text such as `G1` or `G2`.
- Unsupported scheme types return `None` so callers can fall back to the old renderer.

- [ ] **Step 4: Implement the renderer**

Implement `render_template_scheme(scheme_type, params) -> str | None`.

Rules:
- Support only `SchemeType.DEP_SIMPLE` in this task.
- Read the DXF from `backend/templates/schemes/dxf/1_2_dep_simple.dxf`.
- Use `ezdxf.readfile()`, `RenderContext`, `SVGBackend`, `Frontend.draw_layout(doc.modelspace())`.
- Return SVG markup wrapped in a scaled `<g id="scheme-template-dep-simple">...</g>` that can be embedded into the existing `gost_frame_a3()` output.
- Preserve old behavior for missing/unsupported templates by returning `None`.

- [ ] **Step 5: Verify**

Run:

`SMTP_PASSWORD=0123456789 ADMIN_API_KEY=1234567890123456 OPENROUTER_API_KEY=0123456789 pytest backend/tests/test_scheme_template_renderer.py`

Expected: all tests pass.

### Task 2: Integrate Template Renderer Into Existing Scheme Flow

**Files:**
- Modify: `backend/app/services/scheme_svg_renderer.py`
- Modify: `backend/tests/test_scheme_auto_generation.py`

- [ ] **Step 1: Write failing integration test**

Add a test proving `render_scheme(SchemeType.DEP_SIMPLE, SchemeParams())` uses the template renderer when it returns content, and falls back to the existing Python renderer when it returns `None`.

- [ ] **Step 2: Implement minimal integration**

At the start of `render_scheme()`, call `render_template_scheme(scheme_type, params)`. If it returns a non-empty string, return it. Otherwise continue with the existing renderer dispatch.

- [ ] **Step 3: Verify**

Run:

`SMTP_PASSWORD=0123456789 ADMIN_API_KEY=1234567890123456 OPENROUTER_API_KEY=0123456789 pytest backend/tests/test_scheme_template_renderer.py backend/tests/test_scheme_auto_generation.py`

Expected: all tests pass.

### Task 3: Documentation, API Types, and Final Checks

**Files:**
- Modify: `docs/changelog.md`
- Modify: `docs/tasktracker.md`
- Modify: `docs/project.md`
- Modify: `docs/scheme-generator-roadmap.md`

- [ ] **Step 1: Add changelog summary**

Add a short `2026-04-25` changelog entry explaining that the first scheme now uses a DXF-based template path and the remaining schemes still use legacy programmatic rendering.

- [ ] **Step 2: Update project documentation**

Document the template pipeline:

`DXF source -> ezdxf SVG rendering -> gost_frame_a3 -> WeasyPrint PDF`

- [ ] **Step 3: Update scheme roadmap**

Mark the first DXF-template migration as started/done and note that the remaining seven schemes require source DXF/SVG templates.

- [ ] **Step 4: Run final checks**

Run:

- `SMTP_PASSWORD=0123456789 ADMIN_API_KEY=1234567890123456 OPENROUTER_API_KEY=0123456789 pytest backend/tests/test_scheme_template_renderer.py backend/tests/test_scheme_auto_generation.py`
- `ruff check backend/app/services/scheme_template_renderer.py backend/app/services/scheme_svg_renderer.py backend/tests/test_scheme_template_renderer.py backend/tests/test_scheme_auto_generation.py`
- `python -m compileall backend/app/services/scheme_template_renderer.py backend/app/services/scheme_svg_renderer.py`

Expected: all checks pass.
