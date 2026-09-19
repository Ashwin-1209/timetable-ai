from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

BASE_TABLE_STYLE_COMMANDS = [
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
]

BREAK_ROW_COLOR = colors.HexColor("#e0e0e0")


def _period_rows(P):
    """
    Returns (period_number, is_break) pairs in order, deduplicated across
    days -- Periods are duplicated per WORKING_DAYS by the loader, but a
    given period_number's is_break flag is the same on every day.
    """
    seen = {}
    for p in P.values():
        seen[p["period_number"]] = p["is_break"]
    return sorted(seen.items())


def _build_grid(entries, period_rows, cell_fn):
    """
    entries: schedule items already filtered to one group or one staff.
    Returns {period_number: {day: cell_text}}. A lab's two schedule rows
    (one per occupied period) each fill their own cell independently --
    merging identical adjacent cells happens later, in _merge_lab_cells.
    """
    grid = {p: {d: "" for d in DAY_ORDER} for p, is_break in period_rows if not is_break}
    for item in entries:
        day = item["day"]
        period_number = item["period_number"]
        if day in DAY_ORDER and period_number in grid:
            grid[period_number][day] = cell_fn(item)
    return grid


def _grid_to_table_data(grid, period_rows):
    """
    Builds the raw table rows, inserting a shaded "BREAK" row (spanning
    every day column) wherever a period is marked as a break, rather than
    silently omitting it -- the README's own PDF test criteria calls for
    breaks to be visibly marked.
    """
    header = ["Period"] + DAY_ORDER
    rows = [header]
    break_row_indices = []

    for row_idx, (period_number, is_break) in enumerate(period_rows, start=1):
        if is_break:
            rows.append([str(period_number)] + ["BREAK"] * len(DAY_ORDER))
            break_row_indices.append(row_idx)
        else:
            rows.append([str(period_number)] + [grid[period_number][d] for d in DAY_ORDER])

    return rows, break_row_indices


def _merge_lab_cells(table_data, period_rows, break_row_indices):
    """
    When two vertically adjacent period rows have identical, non-empty
    text in the same day column, that's a lab block occupying both of its
    consecutive periods -- merge them into one visual cell instead of
    printing the same subject/teacher twice ("no duplicate subject in same
    period/row", per the README's own PDF test criteria). Never merges
    across a break row.
    """
    spans = []
    num_days = len(DAY_ORDER)
    period_numbers = [p for p, _ in period_rows]

    for row_idx in range(1, len(table_data) - 1):
        if row_idx in break_row_indices or (row_idx + 1) in break_row_indices:
            continue

        current_period = period_numbers[row_idx - 1]
        next_period = period_numbers[row_idx]
        if next_period != current_period + 1:
            continue  # only ever merge truly consecutive periods

        current_row = table_data[row_idx]
        next_row = table_data[row_idx + 1]

        for col in range(1, num_days + 1):
            if current_row[col] and current_row[col] == next_row[col]:
                spans.append((col, row_idx, row_idx + 1))
                next_row[col] = ""  # SPAN displays the upper cell's text; blank the lower one

    return spans


def _build_table(table_data, break_row_indices, merge_spans):
    commands = list(BASE_TABLE_STYLE_COMMANDS)

    for row_idx in break_row_indices:
        commands.append(("BACKGROUND", (0, row_idx), (-1, row_idx), BREAK_ROW_COLOR))
        commands.append(("SPAN", (1, row_idx), (len(DAY_ORDER), row_idx)))

    for col, r1, r2 in merge_spans:
        commands.append(("SPAN", (col, r1), (col, r2)))

    return Table(table_data, style=TableStyle(commands))


def _render_grid_page(story, styles, title, entries, period_rows, cell_fn):
    grid = _build_grid(entries, period_rows, cell_fn)
    table_data, break_row_indices = _grid_to_table_data(grid, period_rows)
    merge_spans = _merge_lab_cells(table_data, period_rows, break_row_indices)
    table = _build_table(table_data, break_row_indices, merge_spans)

    story.append(Paragraph(title, styles["Heading2"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(table)
    story.append(PageBreak())


def export_class_pdf(schedule, T, S, G, P, output_path):
    """One page per class group: rows = periods, columns = days, cell = subject code + teacher."""
    period_rows = _period_rows(P)
    styles = getSampleStyleSheet()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4))
    story = []

    for group_id, group in G.items():
        entries = [item for item in schedule if item["group_id"] == group_id]
        if not entries:
            continue

        def cell_fn(item, S=S, T=T):
            subject = S[item["subject_id"]]
            teacher = T[item["staff_id"]]
            return f"{subject['subject_code']}\n{teacher['staff_name']}"

        title = f"{group['department']} - {group['section']} (Year {group['year']})"
        _render_grid_page(story, styles, title, entries, period_rows, cell_fn)

    if story:
        story.pop()  # drop trailing page break after the last page
    doc.build(story)
    return output_path


def export_staff_pdf(schedule, T, S, G, P, output_path):
    """One page per staff member: rows = periods, columns = days, cell = subject code + group."""
    period_rows = _period_rows(P)
    styles = getSampleStyleSheet()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4))
    story = []

    for staff_id, staff in T.items():
        entries = [item for item in schedule if item["staff_id"] == staff_id]
        if not entries:
            continue  # skip staff with nothing assigned rather than an empty page

        def cell_fn(item, S=S, G=G):
            subject = S[item["subject_id"]]
            group = G[item["group_id"]]
            return f"{subject['subject_code']}\n{group['department']}-{group['section']}"

        _render_grid_page(story, styles, staff["staff_name"], entries, period_rows, cell_fn)

    if story:
        story.pop()
    doc.build(story)
    return output_path