import copy
import csv
import math
import random

from .soft_constraints import calculate_soft_constraints, calculate_objective


def schedule_to_state(schedule):
    """
    Collapse the CP-SAT schedule (one row per occupied period -- labs
    contribute two rows) into one entry per session instance, so a lab's
    two periods are always moved together.
    """
    state = {}
    for item in schedule:
        iid = item["instance_id"]
        if iid not in state:
            state[iid] = {
                "instance_id": iid,
                "group_id": item["group_id"],
                "subject_id": item["subject_id"],
                "staff_id": item["staff_id"],
                "room_id": item["room_id"],
                "periods": [],
            }
        state[iid]["periods"].append(item["period_id"])
    return state


def state_to_schedule(state, P):
    """Expand state back into one row per occupied period (the shape soft_constraints.py expects)."""
    schedule = []
    for entry in state.values():
        for period_id in entry["periods"]:
            schedule.append({
                "instance_id": entry["instance_id"],
                "group_id": entry["group_id"],
                "subject_id": entry["subject_id"],
                "staff_id": entry["staff_id"],
                "room_id": entry["room_id"],
                "period_id": period_id,
                "day": P[period_id]["day"],
                "period_number": P[period_id]["period_number"],
            })
    return schedule


def build_candidate_moves(x_keys, b_keys):
    """
    x_keys: keys of the CP-SAT `x` dict -- (instance_id, staff_id, room_id, period_id)
    b_keys: keys of the CP-SAT `b` dict -- (instance_id, staff_id, room_id, period_id),
            where period_id is the FIRST period of a lab's consecutive pair.

    Groups both into {instance_id: [(staff_id, room_id, (period_id, ...)), ...]}
    so SA only ever proposes candidates the CP-SAT model itself already
    considered individually feasible (staff eligibility, room type/capacity,
    department match, lab-room-and-pair requirement). Constraints that
    depend on OTHER sessions -- double-booking, daily load, per-day subject
    cap -- are re-checked per move in `hard_constraints_satisfied`, since
    they can't be precomputed per-instance in isolation.
    """
    # Anything that appears in b_keys is a lab instance -- CP-SAT still
    # creates single-period x variables for labs internally (constrained
    # to move in lockstep via x1==b, x2==b), but those single-period
    # entries must never be offered to SA as standalone candidates, or a
    # lab can get collapsed down to one period. Skip them here; labs only
    # ever get paired candidates from attach_lab_pairs.
    lab_instance_ids = {instance_id for instance_id, staff_id, room_id, period_id in b_keys}

    moves = {}

    for instance_id, staff_id, room_id, period_id in x_keys:
        if instance_id in lab_instance_ids:
            continue
        moves.setdefault(instance_id, []).append((staff_id, room_id, (period_id,)))

    # b_keys pair each lab instance with its consecutive-period partner.
    # The partner period isn't in the key itself, so PP (the list of valid
    # consecutive pairs) is needed to recover it.
    return moves


def attach_lab_pairs(moves, b_keys, PP):
    pair_lookup = {p: n for p, n in PP}
    for instance_id, staff_id, room_id, period_id in b_keys:
        next_period_id = pair_lookup.get(period_id)
        if next_period_id is None:
            continue
        moves.setdefault(instance_id, [])
        candidate = (staff_id, room_id, (period_id, next_period_id))
        if candidate not in moves[instance_id]:
            moves[instance_id].append(candidate)
    return moves


def period_counts_intact(state, expected_period_counts):
    """
    Every instance must keep the same number of periods it started with
    (1 for theory, 2 for a lab pair) -- SA is only allowed to change WHICH
    periods/staff/room an instance uses, never HOW MANY. This is a
    structural invariant, independent of any specific move-generation bug,
    so it's checked directly rather than trusted to hold implicitly.
    """
    for instance_id, entry in state.items():
        if len(entry["periods"]) != expected_period_counts[instance_id]:
            return False
    return True


def hard_constraints_satisfied(state, P, max_periods_per_day, per_day_cap):
    """
    Full re-check of every hard constraint that spans multiple session
    instances (H2, H3, H4, H14, H15). Constraints that only concern a
    single instance in isolation (staff eligibility, room type/capacity,
    lab consecutive-pair shape) are already guaranteed by only ever
    drawing candidates from build_candidate_moves/attach_lab_pairs, so they
    are not re-checked here.
    """
    period_staff = set()
    period_room = set()
    period_group = set()
    daily_staff_load = {}
    day_subject_count = {}

    for entry in state.values():
        staff_id = entry["staff_id"]
        room_id = entry["room_id"]
        group_id = entry["group_id"]
        subject_id = entry["subject_id"]

        for period_id in entry["periods"]:
            day = P[period_id]["day"]

            key_sp = (staff_id, period_id)
            if key_sp in period_staff:
                return False
            period_staff.add(key_sp)

            key_rp = (room_id, period_id)
            if key_rp in period_room:
                return False
            period_room.add(key_rp)

            key_gp = (group_id, period_id)
            if key_gp in period_group:
                return False
            period_group.add(key_gp)

            daily_staff_load[(staff_id, day)] = daily_staff_load.get((staff_id, day), 0) + 1
            day_subject_count[(group_id, subject_id, day)] = (
                day_subject_count.get((group_id, subject_id, day), 0) + 1
            )

    for (staff_id, day), count in daily_staff_load.items():
        limit = max_periods_per_day.get(staff_id)
        if limit is not None and count > limit:
            return False

    for count in day_subject_count.values():
        if count > per_day_cap:
            return False

    return True


def group_instances_by_shape(state):
    """
    Groups instance_ids by how many periods they occupy (1 = theory,
    2 = lab pair), so swap moves only ever exchange periods between
    instances of the same kind -- a theory session can never be swapped
    with a lab block.
    """
    by_shape = {}
    for instance_id, entry in state.items():
        shape = len(entry["periods"])
        by_shape.setdefault(shape, []).append(instance_id)
    return by_shape


def propose_swap(by_shape):
    """
    Picks two distinct same-shape instances and proposes exchanging their
    period assignments (staff_id and room_id stay put -- only WHEN each
    instance happens changes, not WHO teaches it or WHERE).

    This is the move type your master plan actually specified for Phase 5
    ("swap -> accept/reject via Metropolis criterion"). It matters
    specifically because RELOCATE moves (move one instance to a new,
    currently-free period) are structurally impossible once a group's week
    is 100% occupied -- as in testcase_1.xlsx, where ECE-A and ECE-B each
    use all 40 of 40 available periods. Every relocate target is already
    occupied by another session of the same group, so every relocate
    proposal fails the group-no-double-booking check, always, for every
    instance -- that's a deadlock, not evidence of already being optimal.
    A swap between two instances of the SAME group can never violate that
    group's own uniqueness constraint, since it's just a permutation of
    periods the group already owns; staff/room clashes against OTHER
    groups are still verified normally by hard_constraints_satisfied.
    """
    eligible_shapes = [shape for shape, ids in by_shape.items() if len(ids) >= 2]
    if not eligible_shapes:
        return None

    shape = random.choice(eligible_shapes)
    instance_a, instance_b = random.sample(by_shape[shape], 2)
    return instance_a, instance_b


def apply_swap(state, instance_a, instance_b):
    new_state = copy.deepcopy(state)
    new_state[instance_a]["periods"], new_state[instance_b]["periods"] = (
        new_state[instance_b]["periods"],
        new_state[instance_a]["periods"],
    )
    return new_state


def propose_move(state, candidate_moves):
    eligible_instances = [iid for iid, options in candidate_moves.items() if options]
    if not eligible_instances:
        return None

    instance_id = random.choice(eligible_instances)
    staff_id, room_id, periods = random.choice(candidate_moves[instance_id])
    return instance_id, staff_id, room_id, periods


def apply_move(state, instance_id, staff_id, room_id, periods):
    new_state = copy.deepcopy(state)
    new_state[instance_id]["staff_id"] = staff_id
    new_state[instance_id]["room_id"] = room_id
    new_state[instance_id]["periods"] = list(periods)
    return new_state


def simulated_annealing(
    initial_schedule,
    candidate_moves,
    P,
    weights,
    soft_constraint_kwargs,
    max_periods_per_day,
    per_day_cap=2,
    swap_probability=0.7,
    initial_temp=100.0,
    cooling_rate=0.995,
    min_temp=0.01,
    max_iterations=5000,
    seed=None,
    log_path=None,
):
    """
    soft_constraint_kwargs: dict with the non-schedule args
    calculate_soft_constraints needs -- avoid, max_consecutive,
    working_days, bad_lab_slots, subjects, compact_preference (optional),
    per_day_cap. Kept as one dict rather than a long positional list so
    this signature doesn't need to change every time a soft constraint
    gains a new parameter.

    seed: pass an int for reproducible runs (useful while developing/
    debugging a single instance); leave as None and run >=5 times per
    dataset size for the averaged results Phase 12 needs -- a single
    seeded run is not sufficient evidence for a stochastic method.
    """
    if seed is not None:
        random.seed(seed)

    state = schedule_to_state(initial_schedule)
    by_shape = group_instances_by_shape(state)  # static -- period counts never change

    # The CP-SAT schedule is trusted to have the right period count per
    # instance already -- capture it once as the invariant every later
    # state must preserve.
    expected_period_counts = {
        instance_id: len(entry["periods"]) for instance_id, entry in state.items()
    }

    def cost_of(candidate_state):
        candidate_schedule = state_to_schedule(candidate_state, P)
        violations = calculate_soft_constraints(
            candidate_schedule,
            per_day_cap=per_day_cap,
            **soft_constraint_kwargs,
        )
        return calculate_objective(violations, weights), violations

    current_cost, current_violations = cost_of(state)
    best_state = copy.deepcopy(state)
    best_cost = current_cost

    temp = initial_temp
    log_rows = []
    iteration = 0

    while temp > min_temp and iteration < max_iterations:
        use_swap = random.random() < swap_probability

        if use_swap:
            swap = propose_swap(by_shape)
            if swap is None:
                use_swap = False  # fall through to relocate below

        if use_swap:
            instance_a, instance_b = swap
            candidate_state = apply_swap(state, instance_a, instance_b)
            move_description = f"swap {instance_a}<->{instance_b}"
        else:
            move = propose_move(state, candidate_moves)
            if move is None:
                break  # nothing left to try -- exhausted or empty candidate set
            instance_id, staff_id, room_id, periods = move
            candidate_state = apply_move(state, instance_id, staff_id, room_id, periods)
            move_description = f"relocate {instance_id}"

        if not period_counts_intact(candidate_state, expected_period_counts):
            raise AssertionError(
                f"Move ({move_description}) changed a period count -- this should be "
                "impossible given build_candidate_moves/attach_lab_pairs/propose_swap "
                "and indicates a bug in candidate generation, not a normal rejected move."
            )

        if not hard_constraints_satisfied(candidate_state, P, max_periods_per_day, per_day_cap):
            log_rows.append({
                "iteration": iteration,
                "temperature": temp,
                "current_cost": current_cost,
                "best_cost": best_cost,
                "accepted": False,
                "reason": "hard_constraint_violation",
                "move": move_description,
            })
            iteration += 1
            temp *= cooling_rate
            continue

        candidate_cost, candidate_violations = cost_of(candidate_state)
        delta = candidate_cost - current_cost

        if delta <= 0:
            accept = True
        else:
            accept = random.random() < math.exp(-delta / temp)

        if accept:
            state = candidate_state
            current_cost = candidate_cost
            current_violations = candidate_violations
            if current_cost < best_cost:
                best_state = copy.deepcopy(state)
                best_cost = current_cost

        log_rows.append({
            "iteration": iteration,
            "temperature": temp,
            "current_cost": current_cost,
            "best_cost": best_cost,
            "accepted": accept,
            "reason": "soft_constraint_evaluation",
            "move": move_description,
        })

        iteration += 1
        temp *= cooling_rate

    if log_path:
        with open(log_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["iteration", "temperature", "current_cost", "best_cost", "accepted", "reason", "move"],
            )
            writer.writeheader()
            writer.writerows(log_rows)

    return {
        "schedule": state_to_schedule(best_state, P),
        "cost": best_cost,
        "iterations_run": iteration,
        "log": log_rows,
    }