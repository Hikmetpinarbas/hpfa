from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape, quoteattr
from zipfile import ZIP_DEFLATED, ZipFile


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"


def _column_letter(index: int) -> str:
    chars: list[str] = []
    value = index
    while value:
        value, rem = divmod(value - 1, 26)
        chars.append(chr(65 + rem))
    return "".join(reversed(chars)) or "A"


def _cell_xml(ref: str, value: object, *, formula: str | None = None) -> str:
    if formula is not None:
        cached = "" if value is None else f"<v>{escape(str(value))}</v>"
        return f'<c r={quoteattr(ref)}><f>{escape(formula)}</f>{cached}</c>'
    if value is None:
        return ""
    if isinstance(value, bool):
        return f'<c r={quoteattr(ref)} t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r={quoteattr(ref)}><v>{value}</v></c>'
    text = escape(str(value))
    return f'<c r={quoteattr(ref)} t="inlineStr"><is><t>{text}</t></is></c>'


def _sheet_xml(rows: list[list[object]], formulas: dict[str, tuple[str, object | None]] | None = None) -> str:
    formulas = formulas or {}
    max_row = max(len(rows), max((int("".join(ch for ch in ref if ch.isdigit())) for ref in formulas), default=0))
    max_col = 0
    row_xml: list[str] = []
    for row_index in range(1, max_row + 1):
        row = rows[row_index - 1] if row_index <= len(rows) else []
        cells: list[str] = []
        width = max(len(row), max((sum((ord(ch.upper()) - 64) * (26 ** power) for power, ch in enumerate(reversed("".join(c for c in ref if c.isalpha())))) for ref in formulas if ref.endswith(str(row_index))), default=0))
        max_col = max(max_col, width)
        for col_index in range(1, width + 1):
            ref = f"{_column_letter(col_index)}{row_index}"
            if ref in formulas:
                formula, cached = formulas[ref]
                cell = _cell_xml(ref, cached, formula=formula)
            else:
                value = row[col_index - 1] if col_index <= len(row) else None
                cell = _cell_xml(ref, value)
            if cell:
                cells.append(cell)
        if cells:
            row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    dimension = f"A1:{_column_letter(max(1, max_col))}{max(1, max_row)}"
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{MAIN_NS}">'
        f'<dimension ref="{dimension}"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        f'</worksheet>'
    )


def write_xlsx(
    path: Path,
    *,
    sheets: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet_nodes: list[str] = []
    rel_nodes: list[str] = []
    overrides: list[str] = []

    for index, spec in enumerate(sheets, start=1):
        name = str(spec["name"])
        state = str(spec.get("state") or "visible")
        state_attr = "" if state == "visible" else f' state={quoteattr(state)}'
        sheet_nodes.append(
            f'<sheet name={quoteattr(name)} sheetId="{index}" r:id="rId{index}"{state_attr}/>'
        )
        rel_nodes.append(
            f'<Relationship Id="rId{index}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )

    workbook = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<workbook xmlns="{MAIN_NS}" xmlns:r="{DOC_REL_NS}">'
        f'<sheets>{"".join(sheet_nodes)}</sheets>'
        f'</workbook>'
    )
    workbook_rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{PKG_REL_NS}">{"".join(rel_nodes)}</Relationships>'
    )
    package_rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{PKG_REL_NS}">'
        f'<Relationship Id="rId1" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        f'Target="xl/workbook.xml"/>'
        f'</Relationships>'
    )
    content_types = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Types xmlns="{CONTENT_NS}">'
        f'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        f'<Default Extension="xml" ContentType="application/xml"/>'
        f'<Override PartName="/xl/workbook.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f'{"".join(overrides)}'
        f'</Types>'
    )

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        for index, spec in enumerate(sheets, start=1):
            rows = list(spec.get("rows") or [])
            formulas = dict(spec.get("formulas") or {})
            archive.writestr(
                f"xl/worksheets/sheet{index}.xml",
                _sheet_xml(rows, formulas),
            )
