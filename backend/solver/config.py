# Shared between csp_solver.py (hard constraint H15) and sa_optimizer.py
# (soft constraint V4's floor calculation) so both always agree on the rule
# instead of relying on the same literal being kept in sync by hand in two
# files.
PER_DAY_CAP = 2

# Soft-constraint weights for the SA objective. Per your patent spec's
# "administrator-configurable soft constraint weights" novelty, this is
# the file an institution would actually edit -- keep it isolated here
# rather than inline in sa_optimizer.py so that claim is literally true of
# your implementation, not just your writeup.
WEIGHTS = {
    "V1": 5,  # teacher preference (avoided periods)
    "V2": 3,  # consecutive-session overrun
    "V3": 2,  # teacher gaps (only counted for opted-in staff -- see soft_constraints.calculate_v3)
    "V4": 2,  # back-to-back subject on consecutive days (avoidable portion only)
    "V5": 4,  # lab placed in an undesirable period
}

# Periods considered institutionally undesirable for lab placement (V5).
# 1-indexed period numbers, matching Periods.period_number.
BAD_LAB_SLOTS = {7, 8}