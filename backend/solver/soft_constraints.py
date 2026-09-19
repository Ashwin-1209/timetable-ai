import math


def calculate_v1(schedule, avoid):
    violations = 0
    for item in schedule:
        staff_id = item["staff_id"]
        period_number = item["period_number"]
        if period_number in avoid.get(staff_id, set()):
            violations += 1
    return violations


def calculate_v2(schedule, max_consecutive):
    violations = 0
    teaching = {}
    for item in schedule:
        staff_id = item["staff_id"]
        day = item["day"]
        period = item["period_number"]
        teaching.setdefault(staff_id, {}).setdefault(day, set()).add(period)
    for staff_id, days in teaching.items():
        limit = max_consecutive.get(staff_id)
        if limit is None:
            continue
        for day, periods in days.items():
            periods = sorted(periods)
            consecutive = 1
            for i in range(1, len(periods)):
                if periods[i] == periods[i - 1] + 1:
                    consecutive += 1
                    if consecutive > limit:
                        violations += 1
                else:
                    consecutive = 1
    return violations


def calculate_v3(schedule, compact_preference=None):
    """
    Penalizes idle gaps between a teacher's first and last period on a day.

    compact_preference: optional dict {staff_id: bool}. Only teachers who
    have opted in (value True) are counted. Pass None (default) to count
    every teacher, which keeps this backward-compatible until the
    Preferences table gains a real "wants_compact_schedule" column --
    at that point, load that column and pass it in here.
    """
    violations = 0
    teaching = {}

    for item in schedule:
        staff_id = item["staff_id"]
        day = item["day"]
        period = item["period_number"]
        teaching.setdefault(staff_id, {}).setdefault(day, set()).add(period)

    for staff_id, days in teaching.items():
        if compact_preference is not None and not compact_preference.get(staff_id, False):
            continue

        for day, periods in days.items():
            if not periods:
                continue

            first_period = min(periods)
            last_period = max(periods)
            total_span = last_period - first_period + 1
            teaching_count = len(periods)

            violations += total_span - teaching_count

    return violations


def _min_forced_adjacent_days(k, n):
    """
    Minimum number of adjacent-day pairs unavoidable when a subject must
    occupy k distinct days out of an n-day working week (path, not cycle).

    Derivation: to avoid an adjacent pair, selected days need a gap of at
    least one unselected day between them, which needs (k-1) unselected
    "gap" days. Only (n-k) unselected days actually exist. Any shortfall
    forces that many adjacent pairs:
        shortfall = (k - 1) - (n - k) = 2k - n - 1
    Clamped at 0 since you can never have fewer than zero forced pairs.
    """
    return max(0, 2 * k - n - 1)


def calculate_v4(schedule, working_days, subjects, per_day_cap=2):
    """
    Penalizes the same subject scheduled on two consecutive working days
    for the same group.

    This is only meaningful once a per-day cap on same-subject periods
    exists (H15 in the formal model) -- without one, a high-frequency
    subject can dodge every V4 penalty by stacking all its periods onto
    just 3 non-adjacent days (Mon/Wed/Fri in a 5-day week), which is worse
    than the thing V4 is trying to prevent. `per_day_cap` here must match
    whatever cap is actually enforced in the solver.

    For subjects whose weekly session count forces them onto enough days
    that some adjacency is mathematically unavoidable (see
    _min_forced_adjacent_days), the unavoidable portion is subtracted out.
    Only the "avoidable" remainder should feed the weighted objective --
    the raw count and the floor are both returned too, for the
    explainability report ("1 of these 2 adjacent-day pairs is structurally
    unavoidable given how often this subject meets").
    """
    subject_days = {}

    for item in schedule:
        key = (item["group_id"], item["subject_id"])
        subject_days.setdefault(key, set()).add(item["day"])

    n = len(working_days)
    raw_violations = 0
    structural_floor = 0

    for (group_id, subject_id), days in subject_days.items():
        for i in range(n - 1):
            today = working_days[i]
            tomorrow = working_days[i + 1]
            if today in days and tomorrow in days:
                raw_violations += 1

        sessions_per_week = subjects[subject_id]["sessions_per_week"]
        k_needed = math.ceil(sessions_per_week / per_day_cap)
        structural_floor += _min_forced_adjacent_days(k_needed, n)

    avoidable_violations = max(0, raw_violations - structural_floor)

    return {
        "raw": raw_violations,
        "structural_floor": structural_floor,
        "avoidable": avoidable_violations,
    }


def calculate_v5(schedule, bad_lab_slots, subjects):
    violations = 0
    for item in schedule:
        subject_id = item["subject_id"]
        period = item["period_number"]

        if not subjects[subject_id]["needs_lab"]:
            continue

        if period in bad_lab_slots:
            violations += 1

    return violations


def calculate_soft_constraints(
    schedule,
    avoid,
    max_consecutive,
    working_days,
    bad_lab_slots,
    subjects,
    compact_preference=None,
    per_day_cap=2,
):
    v1 = calculate_v1(schedule, avoid)
    v2 = calculate_v2(schedule, max_consecutive)
    v3 = calculate_v3(schedule, compact_preference)
    v4_detail = calculate_v4(schedule, working_days, subjects, per_day_cap)
    v5 = calculate_v5(schedule, bad_lab_slots, subjects)

    return {
        "V1": v1,
        "V2": v2,
        "V3": v3,
        # The weighted objective should use the avoidable count, not the
        # raw one -- see calculate_v4's docstring.
        "V4": v4_detail["avoidable"],
        "V4_detail": v4_detail,
        "V5": v5,
    }


def calculate_objective(violations, weights):
    return sum(
        weights[name] * value
        for name, value in violations.items()
        if name in weights  # skips "V4_detail", which isn't a weighted term
    )