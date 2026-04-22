"""
* @file: __init__.py
* @description: Пакет генерации договора и счёта (DOCX).
* @created: 2026-04-22
"""

from __future__ import annotations

from .contract_docx import generate_contract, generate_contract_number
from .invoice import generate_invoice

__all__ = [
    "generate_contract",
    "generate_contract_number",
    "generate_invoice",
]
