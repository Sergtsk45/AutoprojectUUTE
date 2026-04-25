"""
@file: test_scheme_template_renderer.py
@description: Тесты DXF-шаблонного рендера первой принципиальной схемы УУТЭ.
@dependencies: app.schemas.scheme, app.services.scheme_template_renderer
@created: 2026-04-25
"""

import builtins

from app.schemas.scheme import SchemeParams, SchemeType
from app.services import scheme_template_renderer as renderer


def test_dep_simple_template_returns_svg_content():
    svg = renderer.render_template_scheme(SchemeType.DEP_SIMPLE, SchemeParams())

    assert svg is not None
    assert '<g id="scheme-template-dep-simple"' in svg
    assert "transform=" in svg
    assert "<svg" in svg
    assert "G1" in svg or "G2" in svg


def test_missing_ezdxf_dependency_returns_none(monkeypatch, caplog):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "ezdxf" or name.startswith("ezdxf."):
            raise ImportError("ezdxf is unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    svg = renderer.render_template_scheme(SchemeType.DEP_SIMPLE, SchemeParams())

    assert svg is None
    assert "ezdxf is unavailable" in caplog.text


def test_unsupported_scheme_type_returns_none():
    svg = renderer.render_template_scheme(SchemeType.DEP_VALVE, SchemeParams())

    assert svg is None


def test_corrupt_template_returns_none(tmp_path, monkeypatch, caplog):
    bad_template = tmp_path / "bad.dxf"
    bad_template.write_text("not a dxf", encoding="utf-8")
    monkeypatch.setattr(renderer, "DEP_SIMPLE_TEMPLATE_PATH", bad_template)

    svg = renderer.render_template_scheme(SchemeType.DEP_SIMPLE, SchemeParams())

    assert svg is None
    assert "Failed to read DXF template" in caplog.text


def test_missing_template_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(renderer, "DEP_SIMPLE_TEMPLATE_PATH", tmp_path / "missing.dxf")

    svg = renderer.render_template_scheme(SchemeType.DEP_SIMPLE, SchemeParams())

    assert svg is None
