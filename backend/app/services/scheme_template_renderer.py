"""
@file: scheme_template_renderer.py
@description: DXF-шаблонный рендер принципиальных схем УУТЭ в SVG-фрагменты.
@dependencies: ezdxf, app.schemas.scheme
@created: 2026-04-25
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.schemas.scheme import SchemeParams, SchemeType

logger = logging.getLogger(__name__)

# Исходник в репозитории: docs/scheme/1_2_Сх_зависимая без ГВС без клапана 2.dxf
# (при правке копировать в runtime-путь ниже — Docker и prod читают только его).
DEP_SIMPLE_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[2] / "templates" / "schemes" / "dxf" / "1_2_dep_simple.dxf"
)

_TEMPLATE_PAGE_WIDTH_MM = 420
_TEMPLATE_PAGE_HEIGHT_MM = 297
_TEMPLATE_TRANSFORM = "translate(40 40) scale(0.82)"


def _strip_xml_declaration(svg_string: str) -> str:
    if svg_string.startswith("<?xml"):
        return svg_string.split("?>", 1)[1].lstrip()
    return svg_string


def _load_ezdxf_renderer() -> tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any] | None:
    try:
        import ezdxf
        from ezdxf.addons.drawing import Frontend, RenderContext, layout, svg
        from ezdxf.addons.drawing.config import (
            BackgroundPolicy,
            ColorPolicy,
            Configuration,
            ImagePolicy,
        )
    except ImportError as exc:
        logger.warning("ezdxf is unavailable, DXF template render skipped: %s", exc)
        return None

    return (
        ezdxf,
        Frontend,
        RenderContext,
        layout,
        svg,
        Configuration,
        ImagePolicy,
        BackgroundPolicy,
        ColorPolicy,
    )


def render_template_scheme(scheme_type: SchemeType, params: SchemeParams) -> str | None:
    """Рендерит поддерживаемую DXF-схему в SVG-фрагмент для ГОСТ-рамки."""
    del params

    if scheme_type is not SchemeType.DEP_SIMPLE:
        return None

    renderer_deps = _load_ezdxf_renderer()
    if renderer_deps is None:
        return None
    (
        ezdxf,
        Frontend,
        RenderContext,
        layout,
        svg,
        Configuration,
        ImagePolicy,
        BackgroundPolicy,
        ColorPolicy,
    ) = renderer_deps

    if not DEP_SIMPLE_TEMPLATE_PATH.exists():
        logger.warning("DXF template is missing: %s", DEP_SIMPLE_TEMPLATE_PATH)
        return None

    try:
        doc = ezdxf.readfile(DEP_SIMPLE_TEMPLATE_PATH)
    except Exception as exc:
        logger.warning("Failed to read DXF template %s: %s", DEP_SIMPLE_TEMPLATE_PATH, exc)
        return None

    try:
        backend = svg.SVGBackend()
        config = Configuration(
            image_policy=ImagePolicy.IGNORE,
            background_policy=BackgroundPolicy.OFF,
            color_policy=ColorPolicy.BLACK,
        )
        Frontend(RenderContext(doc), backend, config=config).draw_layout(doc.modelspace())
        page = layout.Page(
            _TEMPLATE_PAGE_WIDTH_MM,
            _TEMPLATE_PAGE_HEIGHT_MM,
            layout.Units.mm,
            margins=layout.Margins.all(0),
        )
        svg_string = backend.get_string(page)
    except Exception as exc:
        logger.warning("Failed to render DXF template %s: %s", DEP_SIMPLE_TEMPLATE_PATH, exc)
        return None

    svg_payload = _strip_xml_declaration(svg_string)
    return (
        f'<g id="scheme-template-dep-simple" transform="{_TEMPLATE_TRANSFORM}">'
        "<desc>DXF template 1_2_dep_simple: G1 G2</desc>"
        f"{svg_payload}</g>"
    )
