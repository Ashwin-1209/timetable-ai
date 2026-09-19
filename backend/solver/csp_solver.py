from ..models.loader import SessionRequirement, Preferences, Periods, Rooms, StaffSubjects, ClassGroups, Staff, Subjects, WORKING_DAYS, get_session, main
from ..output_generator.excel_export import export_schedule_to_excel
from ..output_generator.pdf_export import export_class_pdf, export_staff_pdf
from .sa_optimizer import build_candidate_moves, attach_lab_pairs, simulated_annealing
from .config import WEIGHTS, BAD_LAB_SLOTS, PER_DAY_CAP
from .soft_constraints import calculate_objective, calculate_soft_constraints
from ortools.sat.python import cp_model

main()

session = get_session()

T = {}
for t in session.query(Staff).all():
    key = t.id
    T[key] = {
        "staff_name": t.staff_name,
        "email": t.email,
        "department": t.department,
        "max_periods_per_day": t.max_periods_per_day
    }

S = {}
for s in session.query(Subjects).all():
    key = s.id
    S[key] = {
        "subject_code": s.subject_code,
        "subject_name": s.subject_name,
        "department": s.department,
        "sessions_per_week": s.sessions_per_week,
        "needs_lab": s.needs_lab
    }

G = {}
for g in session.query(ClassGroups).all():
    key = g.id
    G[key] = {
        "department": g.department,
        "section": g.section,
        "year": g.year,
        "num_students": g.num_students,
        "assigned_room": g.assigned_room
    }

R = {}
for r in session.query(Rooms).all():
    key = r.id
    R[key] = {
        "room_number": r.room_number,
        "room_type": r.room_type,
        "capacity": r.capacity,
        "building": r.building,
        "floor": r.floor,
        "dept_preference": r.dept_preference
    }

P = {}
for p in session.query(Periods).all():
    key = p.id
    P[key] = {
        "day": p.day,
        "period_number": p.period_number,
        "start_time": p.start_time,
        "end_time": p.end_time,
        "is_break": p.is_break
    }

session_requirements = session.query(SessionRequirement).all()

K = []
instance_id = 1
for req in session_requirements:
    K.append({
        "instance_id": instance_id,
        "requirement_id": req.id,
        "group_id": req.group_id,
        "subject_id": req.subject_id,
        "is_lab": S[req.subject_id]["needs_lab"],
        "no_of_periods": req.no_of_periods
    })
    instance_id += 1

D = WORKING_DAYS

TS = sorted(
    session.query(Periods)
    .filter_by(is_break=False)
    .all(),
    key=lambda p: (D.index(p.day), p.period_number)
)

PP = []

for i in range(0, len(TS) - 1, 2):
    current = TS[i]
    next_p = TS[i + 1]
    if (
        current.day == next_p.day
        and next_p.period_number == current.period_number + 1
    ):
        PP.append((current.id, next_p.id))

StaffSub = session.query(StaffSubjects).all()

E = {}
for ss in StaffSub:
    staff = T[ss.staff_id]
    subject = S[ss.subject_id]
    if staff["department"] != subject["department"]:
        continue
    key = (ss.subject_id, ss.year)
    E.setdefault(key, []).append(ss.staff_id)

preferences = session.query(Preferences).all()

MaxConsec_t = {}
Pref = {}
Avoid = {}
for p in preferences:
    MaxConsec_t[p.staff_id] = p.max_consecutive
    Pref[p.staff_id] = set(p.preferred_periods)
    Avoid[p.staff_id] = set(p.avoid_periods)

model = cp_model.CpModel()

x = {}

for k in K:
    instance_id = k["instance_id"]
    group_id = k["group_id"]
    subject_id = k["subject_id"]
    eligible_staff = E.get(
        (subject_id, G[group_id]["year"]),
        []
    )

    for staff_id in eligible_staff:
        if T[staff_id]["department"] != G[group_id]["department"]:
            continue

        for room_id in R:
            if k["is_lab"]:
                if R[room_id]["room_type"] != "LAB":
                    continue
            else:
                assigned_room = G[group_id]["assigned_room"]
                if R[room_id]["room_number"] != assigned_room:
                    continue

            if R[room_id]["capacity"] < G[group_id]["num_students"]:
                continue

            for period_id in P:
                if P[period_id]["is_break"]:
                    continue

                x[(instance_id, staff_id, room_id, period_id)] = model.NewBoolVar(
                    f"x_{instance_id}_{staff_id}_{room_id}_{period_id}"
                )

z = {}

for group_id, group in G.items():
    for subject_id, subject in S.items():
        if subject["department"] != group["department"]:
            continue
        eligible_staff = E.get(
            (subject_id, G[group_id]["year"]),
            []
        )
        for staff_id in eligible_staff:
            if T[staff_id]["department"] != G[group_id]["department"]:
                continue
            z[(group_id, subject_id, staff_id)] = model.NewBoolVar(
                f"z_{group_id}_{subject_id}_{staff_id}"
            )

b = {}

for k in K:
    if not k["is_lab"]:
        continue

    instance_id = k["instance_id"]
    group_id = k["group_id"]
    subject_id = k["subject_id"]
    eligible_staff = E.get(
        (subject_id, G[group_id]["year"]),
        []
    )

    for staff_id in eligible_staff:
        if T[staff_id]["department"] != G[group_id]["department"]:
            continue

        for room_id in R:
            if R[room_id]["room_type"] != "LAB":
                continue

            if R[room_id]["capacity"] < G[group_id]["num_students"]:
                continue

            for period_id, next_period_id in PP:
                b[(instance_id, staff_id, room_id, period_id)] = model.NewBoolVar(
                    f"b_{instance_id}_{staff_id}_{room_id}_{period_id}"
                )

instance_to_group = {
    k["instance_id"]: k["group_id"]
    for k in K
}

instance_to_subject = {
    k["instance_id"]: k["subject_id"]
    for k in K
}

for k in K:
    if k["is_lab"]:
        continue

    instance_id = k["instance_id"]

    instance_vars = [
        var
        for (i, staff_id, room_id, period_id), var in x.items()
        if i == instance_id
    ]
    model.AddExactlyOne(instance_vars)

for period_id in P:
    for staff_id in T:
        instance_vars = [
            var
            for (instance_id, t, room_id, p), var in x.items()
            if t == staff_id and p == period_id
        ]

        model.AddAtMostOne(instance_vars)

    for room_id in R:
        instance_vars = [
            var
            for (instance_id, staff_id, r, p), var in x.items()
            if r == room_id and p == period_id
        ]

        model.AddAtMostOne(instance_vars)

    for group_id in G:
        instance_vars = [
            var
            for (instance_id, staff_id, room_id, p), var in x.items()
            if instance_to_group[instance_id] == group_id and p == period_id
        ]

        model.AddAtMostOne(instance_vars)

for group_id, group in G.items():
    for subject_id, subject in S.items():
        if subject["department"] != group["department"]:
            continue
        teacher_vars = [
            var
            for (g, s, staff_id), var in z.items()
            if g == group_id and s == subject_id
        ]

        if teacher_vars:
            model.AddExactlyOne(teacher_vars)

for (instance_id, staff_id, room_id, period_id), x_vars in x.items():
    group_id = instance_to_group[instance_id]
    subject_id = instance_to_subject[instance_id]
    teacher_choice_var = z[(group_id, subject_id, staff_id)]
    model.Add(
        x_vars <= teacher_choice_var
    )

for k in K:
    if not k["is_lab"]:
        continue

    instance_id = k["instance_id"]

    instance_vars = [
        var
        for (i, staff_id, room_id, period_id), var in b.items()
        if i == instance_id
    ]
    model.AddExactlyOne(instance_vars)

for (instance_id, staff_id, room_id, period_id), b_vars in b.items():
    x1 = x[(instance_id, staff_id, room_id, period_id)]
    model.Add(
        x1 == b_vars
    )

    for p, n in PP:
        if p == period_id:
            x2 = x[(instance_id, staff_id, room_id, n)]
            model.Add(
                x2 == b_vars
            )

for staff_id in T:
    for day in D:
        daily_vars = [
            var
            for (instance_id, t, room_id, p), var in x.items()
            if t == staff_id and P[p]["day"] == day
        ]

        model.Add(
            sum(daily_vars) <= T[staff_id]["max_periods_per_day"]
        )

for group_id, group in G.items():
    lab_subjects = [
        subject_id
        for subject_id, subject in S.items()
        if subject["department"] == group["department"]
        and subject["needs_lab"]
    ]
    for day in D:
        lab_day_vars = []
        for subject_id in lab_subjects:
            subject_lab_vars = [
                var
                for (instance_id, staff_id, room_id, period_id), var in x.items()
                if (
                    instance_to_group[instance_id] == group_id
                    and instance_to_subject[instance_id] == subject_id
                    and P[period_id]["day"] == day
                )
            ]
            if subject_lab_vars:
                lab_day_var = model.NewBoolVar(
                    f"lab_day_g{group_id}_s{subject_id}_{day}"
                )

                model.AddMaxEquality(
                    lab_day_var,
                    subject_lab_vars    
                )

                lab_day_vars.append(lab_day_var)
        if lab_day_vars:
            model.AddAtMostOne(lab_day_vars)

    for subject_id, subject in S.items():
        if subject["sessions_per_week"] <= 5:
            continue
        if subject["department"] != group["department"]:
            continue
        for day in D:
            day_vars = [
                var 
                for (instance_id, staff_id, room_id, period_id), var in x.items()
                if (
                    instance_to_group[instance_id] == group_id
                    and instance_to_subject[instance_id] == subject_id
                    and P[period_id]["day"] == day
                )
            ]
            if day_vars:
                model.Add(
                    sum(day_vars) >= 1
                )

for group_id, group in G.items():
    for subject_id, subject in S.items():
        for day in D:
            day_vars = [
                var
                for (instance_id, staff_id, room_id, period_id), var in x.items()
                if instance_to_group[instance_id] == group_id
                and instance_to_subject[instance_id] == subject_id
                and P[period_id]["day"] == day
            ]
            if day_vars:
                model.Add(sum(day_vars) <= 2)

schedule = []

solver = cp_model.CpSolver()

status = solver.Solve(model)

if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print("Solution found!")

    for (instance_id, staff_id, room_id, period_id), var in x.items():

        if solver.Value(var) == 1:

            group_id = instance_to_group[instance_id]
            subject_id = instance_to_subject[instance_id]

            group = G[group_id]
            subject = S[subject_id]

            schedule.append({
                "instance_id": instance_id,
                "staff_id": staff_id,
                "room_id": room_id,
                "period_id": period_id,
                "group_id": group_id,
                "subject_id": subject_id,
                "day": P[period_id]["day"],
                "period_number": P[period_id]["period_number"]
            })

            print(
                "Instance:", instance_id,
                "| Group:", f'{group["department"]} {group["section"]}',
                "| Year:", group["year"],
                "| Subject:", subject["subject_code"],
                "| Teacher:", T[staff_id]["staff_name"],
                "| Room:", R[room_id]["room_number"],
                "| Day:", P[period_id]["day"],
                "| Period:", P[period_id]["period_number"]
            )

    cpsat_cost, _ = None, None  # optional: score the CP-SAT-only schedule for your Phase 12 comparison table

    candidate_moves = attach_lab_pairs(
        build_candidate_moves(x.keys(), b.keys()),
        b.keys(),
        PP,
    )

    max_periods_per_day = {
        staff_id: staff["max_periods_per_day"]
        for staff_id, staff in T.items()
    }

    sa_result = simulated_annealing(
        initial_schedule=schedule,
        candidate_moves=candidate_moves,
        P=P,
        weights=WEIGHTS,
        soft_constraint_kwargs=dict(
            avoid=Avoid,
            max_consecutive=MaxConsec_t,
            working_days=D,
            bad_lab_slots=BAD_LAB_SLOTS,
            subjects=S,
        ),
        max_periods_per_day=max_periods_per_day,
        per_day_cap=PER_DAY_CAP,
        seed=42,  # drop this once you move to the >=5 unseeded runs for Phase 12
        log_path="logs/sa_convergence_run1.csv",
    )

    final_schedule = sa_result["schedule"]

    print("\n--- SA-optimized schedule ---")
    for item in final_schedule:
        print(
            "Instance:", item["instance_id"],
            "| Subject:", S[item["subject_id"]]["subject_code"],
            "| Teacher:", T[item["staff_id"]]["staff_name"],
            "| Room:", R[item["room_id"]]["room_number"],
            "| Day:", item["day"],
            "| Period:", item["period_number"],
        )

    cpsat_violations = calculate_soft_constraints(
        schedule,
        avoid=Avoid,
        max_consecutive=MaxConsec_t,
        working_days=D,
        bad_lab_slots=BAD_LAB_SLOTS,
        subjects=S,
        per_day_cap=PER_DAY_CAP,
    )
    cpsat_cost = calculate_objective(cpsat_violations, WEIGHTS)
    print("CP-SAT-only objective score:", cpsat_cost)

    print("SA-optimized objective score:", sa_result["cost"])

    print("\nSA finished. Best objective score:", sa_result["cost"])

    export_schedule_to_excel(final_schedule, T, S, G, R, P, "output/timetable.xlsx")
    export_class_pdf(final_schedule, T, S, G, P, "output/timetable_by_class.pdf")
    export_staff_pdf(final_schedule, T, S, G, P, "output/timetable_by_staff.pdf")

else:
    print("No feasible solution found.")