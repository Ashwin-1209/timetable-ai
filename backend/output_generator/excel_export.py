from pathlib import Path

from openpyxl import Workbook

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def _sort_key(item, P):
    period = P[item["period_id"]]
    day_index = DAY_ORDER.index(period["day"]) if period["day"] in DAY_ORDER else len(DAY_ORDER)
    return (day_index, period["period_number"])


def export_schedule_to_excel(schedule, T, S, G, R, P, output_path):
    """
    Writes the final schedule (the SA-optimized one, not the raw CP-SAT
    output) as a single flat "Schedule" sheet -- one row per occupied
    period, meant for downstream computational use (re-import, Phase 12
    analysis, MPP input), not for display. The human-facing view is
    pdf_export.py.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Schedule"

    headers = [
        "instance_id", "day", "period_number", "start_time", "end_time",
        "department", "section", "year", "subject_code", "subject_name",
        "staff_name", "room_number",
    ]
    ws.append(headers)

    for item in sorted(schedule, key=lambda x: _sort_key(x, P)):
        period = P[item["period_id"]]
        group = G[item["group_id"]]
        subject = S[item["subject_id"]]
        teacher = T[item["staff_id"]]
        room = R[item["room_id"]]

        ws.append([
            item["instance_id"],
            period["day"],
            period["period_number"],
            str(period["start_time"]),
            str(period["end_time"]),
            group["department"],
            group["section"],
            group["year"],
            subject["subject_code"],
            subject["subject_name"],
            teacher["staff_name"],
            room["room_number"],
        ])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path