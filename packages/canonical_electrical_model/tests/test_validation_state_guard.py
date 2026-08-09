"""Guard test: ``ValidationState.CALIBRATED`` is never assigned.

``CALIBRATED`` is a reserved terminal validation state. No code path in this
repository may assign it; only an out-of-band, operator-governed calibration
process is permitted to do so. This test statically scans every Python source
file in the repository (excluding the enum *definition* and this test itself)
and asserts that the literal ``ValidationState.CALIBRATED`` never appears on
either side of an assignment statement.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Repo root is four levels up: tests -> canonical_electrical_model -> packages -> root.
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Files exempt from the scan: the enum definition and this guard test.
_ENUM_DEFINITION = (
    _REPO_ROOT / "packages" / "canonical_electrical_model" / "enums.py"
).resolve()
_THIS_FILE = Path(__file__).resolve()

# Directory fragments that are never part of first-party source.
_SKIP_DIR_PARTS = {".git", ".venv", "venv", "__pycache__", "site-packages", ".tox", "build", "dist"}


def _iter_source_files() -> list[Path]:
    files: list[Path] = []
    for path in _REPO_ROOT.rglob("*.py"):
        resolved = path.resolve()
        if resolved in (_ENUM_DEFINITION, _THIS_FILE):
            continue
        if any(part in _SKIP_DIR_PARTS for part in resolved.parts):
            continue
        files.append(resolved)
    return files


def _node_references_calibrated(node: ast.AST) -> bool:
    """True if any ``ValidationState.CALIBRATED`` attribute access is inside *node*."""
    for inner in ast.walk(node):
        if isinstance(inner, ast.Attribute) and inner.attr == "CALIBRATED":
            base = inner.value
            if isinstance(base, ast.Name) and base.id == "ValidationState":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "ValidationState":
                return True
    return False


def _assignment_parts(stmt: ast.AST) -> list[ast.AST]:
    if isinstance(stmt, ast.Assign):
        return [*stmt.targets, stmt.value]
    if isinstance(stmt, ast.AugAssign):
        return [stmt.target, stmt.value]
    if isinstance(stmt, ast.AnnAssign):
        parts: list[ast.AST] = [stmt.target]
        if stmt.value is not None:
            parts.append(stmt.value)
        return parts
    return []


def _find_calibrated_assignments(source: str) -> list[int]:
    tree = ast.parse(source)
    hits: list[int] = []
    for stmt in ast.walk(tree):
        if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            if any(_node_references_calibrated(part) for part in _assignment_parts(stmt)):
                hits.append(stmt.lineno)
    return hits


def test_calibrated_never_assigned_outside_enum_definition() -> None:
    violations: list[str] = []
    for path in _iter_source_files():
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno in _find_calibrated_assignments(source):
            violations.append(f"{path.relative_to(_REPO_ROOT)}:{lineno}")

    assert violations == [], (
        "ValidationState.CALIBRATED must never be assigned by repository code; "
        f"found assignment(s) at: {violations}"
    )


def test_guard_detects_a_synthetic_assignment() -> None:
    """Sanity check that the scanner would catch a real violation."""
    sample = "x: object = ValidationState.CALIBRATED\n"
    assert _find_calibrated_assignments(sample) == [1]

    sample_aug = "acc += ValidationState.CALIBRATED\n"
    assert _find_calibrated_assignments(sample_aug) == [1]

    sample_qualified = "y = enums.ValidationState.CALIBRATED\n"
    assert _find_calibrated_assignments(sample_qualified) == [1]

    # A non-assignment reference (e.g. a comparison) must NOT be flagged.
    sample_cmp = "if state == ValidationState.CALIBRATED:\n    pass\n"
    assert _find_calibrated_assignments(sample_cmp) == []
