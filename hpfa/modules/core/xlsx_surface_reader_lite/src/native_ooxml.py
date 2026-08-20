from __future__ import annotations

import posixpath
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

NS = {"m": MAIN_NS, "r": DOC_REL_NS, "pr": PKG_REL_NS}
R_ID = f"{{{DOC_REL_NS}}}id"

BUILTIN_NUMFMTS = {
    0: "General",
    1: "0",
    2: "0.00",
    3: "#,##0",
    4: "#,##0.00",
    9: "0%",
    10: "0.00%",
    14: "mm-dd-yy",
    15: "d-mmm-yy",
    16: "d-mmm",
    17: "mmm-yy",
    18: "h:mm AM/PM",
    19: "h:mm:ss AM/PM",
    20: "h:mm",
    21: "h:mm:ss",
    22: "m/d/yy h:mm",
    37: "#,##0 ;[Red](#,##0)",
    38: "#,##0 ;[Red](#,##0)",
    39: "#,##0.00;[Red](#,##0.00)",
    40: "#,##0.00;[Red](#,##0.00)",
    45: "mm:ss",
    46: "[h]:mm:ss",
    47: "mmss.0",
    49: "@",
}


class InvalidFileException(ValueError):
    pass


@dataclass
class NativeDimension:
    hidden: bool = False


@dataclass
class NativeCell:
    coordinate: str
    cached_value: Any = None
    formula: str | None = None
    cell_type: str | None = None
    number_format: str = "General"
    data_only: bool = False

    @property
    def value(self) -> Any:
        if self.formula is not None and not self.data_only:
            return "=" + self.formula
        return self.cached_value

    @property
    def data_type(self) -> str:
        if self.formula is not None and not self.data_only:
            return "f"
        if isinstance(self.cached_value, bool):
            return "b"
        if isinstance(self.cached_value, (int, float)) and not isinstance(self.cached_value, bool):
            return "n"
        if self.cached_value is None:
            return "n"
        return "s"


class NativeMergedCells:
    def __init__(self, ranges: list[str]) -> None:
        self.ranges = ranges


class NativeWorksheet:
    def __init__(
        self,
        *,
        title: str,
        sheet_state: str,
        cells: dict[tuple[int, int], NativeCell],
        merged_ranges: list[str],
        hidden_rows: set[int],
        hidden_columns: set[int],
        max_row: int,
        max_column: int,
        data_only: bool,
    ) -> None:
        self.title = title
        self.sheet_state = sheet_state
        self.max_row = max_row
        self.max_column = max_column
        self.merged_cells = NativeMergedCells(merged_ranges)
        self.row_dimensions = {
            index: NativeDimension(hidden=True) for index in sorted(hidden_rows)
        }
        self.column_dimensions = {
            column_letter(index): NativeDimension(hidden=True)
            for index in sorted(hidden_columns)
        }
        self._cells = cells
        self._data_only = data_only

    def cell(self, *, row: int, column: int) -> NativeCell:
        cell = self._cells.get((row, column))
        if cell is None:
            return NativeCell(
                coordinate=f"{column_letter(column)}{row}",
                data_only=self._data_only,
            )
        return NativeCell(
            coordinate=cell.coordinate,
            cached_value=cell.cached_value,
            formula=cell.formula,
            cell_type=cell.cell_type,
            number_format=cell.number_format,
            data_only=self._data_only,
        )


class NativeWorkbook:
    def __init__(
        self,
        *,
        sheet_specs: list[dict[str, Any]],
        worksheets: dict[str, NativeWorksheet],
        data_only: bool,
        epoch: str,
        defined_names: list[str],
        calculation_mode: str | None,
        external_link_count: int,
    ) -> None:
        self.sheetnames = [item["name"] for item in sheet_specs]
        self._worksheets = worksheets
        self.data_only = data_only
        self.epoch = epoch
        self.defined_names = defined_names
        self.calculation = SimpleNamespace(calcMode=calculation_mode)
        self._external_links = [None] * external_link_count

    def __getitem__(self, name: str) -> NativeWorksheet:
        return self._worksheets[name]

    def close(self) -> None:
        return None


def column_letter(index: int) -> str:
    if index <= 0:
        return "A"
    chars: list[str] = []
    value = index
    while value:
        value, rem = divmod(value - 1, 26)
        chars.append(chr(65 + rem))
    return "".join(reversed(chars))


def column_index(letters: str) -> int:
    value = 0
    for char in letters.upper():
        if not ("A" <= char <= "Z"):
            break
        value = value * 26 + (ord(char) - 64)
    return value


def cell_ref_parts(ref: str) -> tuple[int, int]:
    match = re.fullmatch(r"([A-Za-z]+)(\d+)", str(ref or "").strip())
    if not match:
        raise InvalidFileException(f"invalid_cell_reference:{ref}")
    return int(match.group(2)), column_index(match.group(1))


def _xml(archive: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        raw = archive.read(name)
    except KeyError as exc:
        raise InvalidFileException(f"missing_ooxml_part:{name}") from exc
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise InvalidFileException(f"malformed_ooxml_part:{name}") from exc


def _optional_xml(archive: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        raw = archive.read(name)
    except KeyError:
        return None
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise InvalidFileException(f"malformed_ooxml_part:{name}") from exc


def _text_content(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return "".join(text for text in element.itertext() if text is not None)


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    root = _optional_xml(archive, "xl/sharedStrings.xml")
    if root is None:
        return []
    result: list[str] = []
    for item in root.findall("m:si", NS):
        result.append(_text_content(item))
    return result


def _relationships(archive: zipfile.ZipFile) -> dict[str, str]:
    root = _xml(archive, "xl/_rels/workbook.xml.rels")
    result: dict[str, str] = {}
    for rel in root.findall("pr:Relationship", NS):
        rel_id = str(rel.attrib.get("Id") or "")
        target = str(rel.attrib.get("Target") or "")
        if not rel_id or not target:
            continue
        if target.startswith("/"):
            normalized = target.lstrip("/")
        else:
            normalized = posixpath.normpath(posixpath.join("xl", target))
        result[rel_id] = normalized
    return result


def _styles(archive: zipfile.ZipFile) -> list[str]:
    root = _optional_xml(archive, "xl/styles.xml")
    if root is None:
        return []
    custom: dict[int, str] = {}
    numfmts = root.find("m:numFmts", NS)
    if numfmts is not None:
        for item in numfmts.findall("m:numFmt", NS):
            try:
                num_id = int(item.attrib.get("numFmtId", ""))
            except ValueError:
                continue
            custom[num_id] = str(item.attrib.get("formatCode") or "General")
    result: list[str] = []
    cell_xfs = root.find("m:cellXfs", NS)
    if cell_xfs is None:
        return result
    for xf in cell_xfs.findall("m:xf", NS):
        try:
            num_id = int(xf.attrib.get("numFmtId", "0"))
        except ValueError:
            num_id = 0
        result.append(custom.get(num_id, BUILTIN_NUMFMTS.get(num_id, f"numFmtId:{num_id}")))
    return result


def _typed_value(
    *,
    cell_type: str | None,
    raw_value: str | None,
    inline_text: str,
    shared: list[str],
) -> Any:
    if cell_type == "inlineStr":
        return inline_text
    if raw_value is None:
        return None
    if cell_type == "s":
        try:
            return shared[int(raw_value)]
        except (ValueError, IndexError) as exc:
            raise InvalidFileException("shared_string_index_invalid") from exc
    if cell_type == "b":
        return raw_value == "1"
    if cell_type in {"str", "e"}:
        return raw_value
    try:
        if re.fullmatch(r"[-+]?\d+", raw_value):
            return int(raw_value)
        return float(raw_value)
    except ValueError:
        return raw_value


def _worksheet(
    archive: zipfile.ZipFile,
    *,
    part: str,
    title: str,
    state: str,
    shared: list[str],
    formats: list[str],
    data_only: bool,
) -> NativeWorksheet:
    root = _xml(archive, part)
    cells: dict[tuple[int, int], NativeCell] = {}
    hidden_rows: set[int] = set()
    hidden_columns: set[int] = set()
    merged_ranges: list[str] = []
    max_row = 0
    max_column = 0

    for row_node in root.findall(".//m:sheetData/m:row", NS):
        try:
            row_index = int(row_node.attrib.get("r", "0"))
        except ValueError:
            row_index = 0
        if str(row_node.attrib.get("hidden") or "0") in {"1", "true", "True"} and row_index > 0:
            hidden_rows.add(row_index)
        for cell_node in row_node.findall("m:c", NS):
            ref = str(cell_node.attrib.get("r") or "")
            if not ref:
                continue
            row, column = cell_ref_parts(ref)
            max_row = max(max_row, row)
            max_column = max(max_column, column)
            cell_type = cell_node.attrib.get("t")
            try:
                style_index = int(cell_node.attrib.get("s", "0"))
            except ValueError:
                style_index = 0
            number_format = formats[style_index] if 0 <= style_index < len(formats) else "General"
            formula_node = cell_node.find("m:f", NS)
            formula = _text_content(formula_node) if formula_node is not None else None
            value_node = cell_node.find("m:v", NS)
            raw_value = value_node.text if value_node is not None else None
            inline_text = _text_content(cell_node.find("m:is", NS))
            cached = _typed_value(
                cell_type=cell_type,
                raw_value=raw_value,
                inline_text=inline_text,
                shared=shared,
            )
            cells[(row, column)] = NativeCell(
                coordinate=ref,
                cached_value=cached,
                formula=formula,
                cell_type=cell_type,
                number_format=number_format,
                data_only=data_only,
            )

    columns = root.find("m:cols", NS)
    if columns is not None:
        for col in columns.findall("m:col", NS):
            hidden = str(col.attrib.get("hidden") or "0") in {"1", "true", "True"}
            if not hidden:
                continue
            try:
                first = int(col.attrib.get("min", "0"))
                last = int(col.attrib.get("max", "0"))
            except ValueError:
                continue
            for index in range(max(1, first), max(1, last) + 1):
                hidden_columns.add(index)

    merge_cells = root.find("m:mergeCells", NS)
    if merge_cells is not None:
        for merge in merge_cells.findall("m:mergeCell", NS):
            ref = str(merge.attrib.get("ref") or "").strip()
            if ref:
                merged_ranges.append(ref)

    dimension = root.find("m:dimension", NS)
    if dimension is not None:
        ref = str(dimension.attrib.get("ref") or "")
        if ref:
            last = ref.split(":")[-1]
            try:
                drow, dcol = cell_ref_parts(last)
            except InvalidFileException:
                pass
            else:
                max_row = max(max_row, drow)
                max_column = max(max_column, dcol)

    return NativeWorksheet(
        title=title,
        sheet_state=state,
        cells=cells,
        merged_ranges=merged_ranges,
        hidden_rows=hidden_rows,
        hidden_columns=hidden_columns,
        max_row=max_row,
        max_column=max_column,
        data_only=data_only,
    )


def load_workbook(
    path: str | Path,
    *,
    read_only: bool = False,
    data_only: bool = False,
    keep_links: bool = False,
) -> NativeWorkbook:
    del read_only, keep_links
    source = Path(path)
    if not source.is_file() or not zipfile.is_zipfile(source):
        raise InvalidFileException("malformed_xlsx_container")

    try:
        archive = zipfile.ZipFile(source, "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise InvalidFileException("malformed_xlsx_container") from exc

    with archive:
        workbook_root = _xml(archive, "xl/workbook.xml")
        rels = _relationships(archive)
        shared = _shared_strings(archive)
        formats = _styles(archive)

        workbook_pr = workbook_root.find("m:workbookPr", NS)
        date1904 = workbook_pr is not None and str(workbook_pr.attrib.get("date1904") or "0") in {"1", "true", "True"}
        epoch = "1904-01-01" if date1904 else "1899-12-30"

        calc_pr = workbook_root.find("m:calcPr", NS)
        calculation_mode = calc_pr.attrib.get("calcMode") if calc_pr is not None else None

        defined_names: list[str] = []
        defined_root = workbook_root.find("m:definedNames", NS)
        if defined_root is not None:
            defined_names = [
                str(item.attrib.get("name") or "")
                for item in defined_root.findall("m:definedName", NS)
                if str(item.attrib.get("name") or "")
            ]

        external_link_count = sum(
            1 for name in archive.namelist() if name.startswith("xl/externalLinks/externalLink") and name.endswith(".xml")
        )

        sheet_specs: list[dict[str, Any]] = []
        worksheets: dict[str, NativeWorksheet] = {}
        sheets_root = workbook_root.find("m:sheets", NS)
        if sheets_root is None:
            raise InvalidFileException("workbook_has_no_sheets")

        for sheet in sheets_root.findall("m:sheet", NS):
            name = str(sheet.attrib.get("name") or "").strip()
            rel_id = str(sheet.attrib.get(R_ID) or "").strip()
            state = str(sheet.attrib.get("state") or "visible")
            if not name or not rel_id or rel_id not in rels:
                raise InvalidFileException("worksheet_relationship_unresolved")
            part = rels[rel_id]
            if part not in archive.namelist():
                raise InvalidFileException(f"missing_ooxml_part:{part}")
            sheet_specs.append({"name": name, "state": state, "part": part})
            worksheets[name] = _worksheet(
                archive,
                part=part,
                title=name,
                state=state,
                shared=shared,
                formats=formats,
                data_only=data_only,
            )

        return NativeWorkbook(
            sheet_specs=sheet_specs,
            worksheets=worksheets,
            data_only=data_only,
            epoch=epoch,
            defined_names=defined_names,
            calculation_mode=calculation_mode,
            external_link_count=external_link_count,
        )
