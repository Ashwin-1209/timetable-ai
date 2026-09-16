# 3. Mathematical Formulation

## 3.1 Problem Definition

The academic timetable generation problem is formulated as a constrained optimization problem in which teaching sessions are assigned to departments, class sections, teachers, and fixed classrooms across days and periods while satisfying all mandatory institutional requirements.

The institution is assumed to consist of multiple academic departments. Each department has its own set of teachers, and teachers are associated exclusively with their department. A further institutional assumption is that a teacher teaches only one subject in a given academic year, although the subject may differ across year levels. For example, a teacher may teach Subject 1 for first-year students and Subject 2 for second-year students, while remaining a staff member of the same department.

Each class group represents a specific section within a department and year level. A class group is assigned one fixed classroom for the semester. Therefore, the timetable does not dynamically move a class group between different rooms from period to period.

The complete scheduling problem is divided into two stages:

1. **Feasibility stage:** A Constraint Programming / CP-SAT model generates a timetable satisfying all hard constraints.
2. **Optimization stage:** Simulated Annealing modifies the feasible timetable to reduce the weighted soft-constraint penalty while preserving hard-constraint feasibility.

Staff absence is handled as a separate dynamic scheduling problem. Instead of regenerating the complete weekly timetable, the system solves a Minimal Perturbation Problem (MPP) to assign substitute staff to affected sessions while preserving as much of the original timetable as possible.

---

## 3.2 Sets and Indices

The model uses the following sets.

### 3.2.1 Departments

Let:

\[
DPT = \text{set of academic departments}
\]

and:

\[
dpt \in DPT
\]

represent a department.

Examples include:

- Computer Science
- Electronics
- Mechanical Engineering

Each department has its own teachers and class sections.

---

### 3.2.2 Teachers

Let:

\[
T = \text{set of teachers}
\]

and:

\[
t \in T
\]

represent a teacher.

Each teacher belongs to exactly one department.

Let:

\[
dept(t)\in DPT
\]

denote the department to which teacher \(t\) belongs.

---

### 3.2.3 Subjects

Let:

\[
S = \text{set of subjects}
\]

and:

\[
s\in S
\]

represent a subject.

A teacher is assumed to teach only one subject for a particular academic year level. Therefore, the teaching assignment is determined by the teacher, year level, and subject relationship rather than allowing arbitrary cross-subject teaching within the same year. (This assumption is formalized as a hard constraint in H6.)

---

### 3.2.4 Class Sections

Let:

\[
G = \text{set of class groups/sections}
\]

and:

\[
g\in G
\]

represent one specific section of a class.

A class group contains only the section identity rather than combining multiple sections into one group.

For each class group:

\[
dept(g)\in DPT
\]

denotes its department, and:

\[
section(g)
\]

denotes its section.

For example:

\[
g=\text{CSE-A}
\]

represents the A section of the Computer Science department rather than all Computer Science students.

---

### 3.2.5 Year Levels

Let:

\[
YL = \text{set of academic year levels}
\]

and let:

\[
yl(g)\in YL
\]

denote the year level of class group \(g\) (e.g. Year 1, Year 2). This is required to formalize the "one subject per teacher per year level" assumption in H6.

---

### 3.2.6 Days

Let:

\[
D = \text{set of working days}
\]

and:

\[
d\in D
\]

represent a day.

---

### 3.2.7 Periods

Let:

\[
P = \text{set of periods}
\]

and:

\[
p\in P
\]

represent a period within a day.

---

### 3.2.8 Time Slots

The set of time slots is:

\[
TS=D\times P
\]

A time slot is represented by:

\[
ts=(d,p)
\]

where:

\[
d\in D,\qquad p\in P
\]

---

### 3.2.9 Rooms

Let:

\[
R = \text{set of classrooms and laboratories}
\]

and:

\[
r\in R
\]

represent a room.

A class group has one fixed classroom for the semester.

Let:

\[
FR_{g,r}\in\{0,1\}
\]

indicate whether room \(r\) is the fixed classroom assigned to class group \(g\).

Thus, for each class group, exactly one room is designated as its semester-long classroom.

---

### 3.2.10 Teaching Sessions

For each class group–subject pair \((g,s)\), let:

\[
K_{g,s}=\{1,\dots,Q_{g,s}\}
\]

be the set of required teaching-session instances for subject \(s\) in class group \(g\), where \(Q_{g,s}\) is the number of required weekly sessions (defined in 3.3.8). For example, if section \(g\) requires Mathematics four times per week, \(K_{g,\text{Math}}=\{1,2,3,4\}\), and these four occurrences are treated as separate, individually schedulable teaching-session instances.

The global index \(k\) used in later sections is always understood to range over \(K_{g,s}\) for the specific \((g,s)\) pair being referenced.

---

### 3.2.11 Valid Consecutive Period Pairs

Let:

\[
PP=\{(p,p+1): p,p+1\in P \text{ and } p,p+1 \text{ are timetable-adjacent periods on the same day}\}
\]

i.e. pairs of periods that can legally form a laboratory block (excluding pairs separated by a lunch break or the end of the day). \(PP\) is used in H13 to formalize laboratory scheduling.

---

## 3.3 Parameters

### 3.3.1 Teacher Department

\[
TD_{t,dpt}\in\{0,1\}
\]

where:

\[
TD_{t,dpt}=
\begin{cases}
1 & \text{if teacher }t\text{ belongs to department }dpt\\
0 & \text{otherwise}
\end{cases}
\]

Each teacher belongs to one department.

---

### 3.3.2 Class Group Department

\[
GD_{g,dpt}\in\{0,1\}
\]

where:

\[
GD_{g,dpt}=1
\]

if class group \(g\) belongs to department \(dpt\).

A class section is therefore associated with one department.

---

### 3.3.3 Teacher Eligibility

\[
E_{t,s}\in\{0,1\}
\]

where:

\[
E_{t,s}=
\begin{cases}
1 & \text{if teacher }t\text{ is eligible to teach subject }s\\
0 & \text{otherwise}
\end{cases}
\]

Because teachers are department-specific, eligibility is restricted by the teacher's department and the subjects taught within that department.

---

### 3.3.4 Room Capacity

\[
C_r
\]

denotes the capacity of room \(r\).

---

### 3.3.5 Group Size

\[
N_g
\]

denotes the number of students in class group \(g\).

---

### 3.3.6 Laboratory Indicator

\[
L_s\in\{0,1\}
\]

where \(L_s=1\) if subject \(s\) is a laboratory subject, and \(L_s=0\) otherwise.

---

### 3.3.7 Laboratory Room Indicator

\[
LR_r\in\{0,1\}
\]

where \(LR_r=1\) if room \(r\) is a laboratory and \(LR_r=0\) otherwise.

---

### 3.3.8 Required Sessions

\[
Q_{g,s}
\]

denotes the number of sessions of subject \(s\) required for class group \(g\) during the scheduling period.

---

### 3.3.9 Teacher Availability

\[
A_{t,d,p}\in\{0,1\}
\]

where \(A_{t,d,p}=1\) if teacher \(t\) is available on day \(d\), period \(p\), and \(0\) otherwise.

---

### 3.3.10 Room Availability

\[
A_{r,d,p}\in\{0,1\}
\]

where \(A_{r,d,p}=1\) if room \(r\) is available on day \(d\), period \(p\).

---

### 3.3.11 Group Availability

\[
A_{g,d,p}\in\{0,1\}
\]

where \(A_{g,d,p}=1\) if class group \(g\) is available on day \(d\), period \(p\).

---

### 3.3.12 Fixed Classroom Assignment

\[
FR_{g,r}\in\{0,1\}
\]

where \(FR_{g,r}=1\) if room \(r\) is the fixed classroom assigned to class group \(g\) for the semester.

For every class group:

\[
\sum_{r\in R}FR_{g,r}=1
\]

This means every class group has exactly one fixed classroom.

---

### 3.3.13 Maximum Daily Teaching Load

\[
MaxLoad_t
\]

denotes the maximum number of periods teacher \(t\) may be scheduled for on a single day (drawn from the institutional "Max Periods Per Day" input). Used in H14.

---

### 3.3.14 Teacher Preference and Avoidance

\[
Pref_{t,d,p},\ Avoid_{t,d,p}\in\{0,1\}
\]

where \(Pref_{t,d,p}=1\) if teacher \(t\) has indicated (d,p) as a preferred period, and \(Avoid_{t,d,p}=1\) if teacher \(t\) has indicated (d,p) as a period to avoid. Used in the definition of \(V_1\).

---

### 3.3.15 Preferred Maximum Consecutive Sessions

\[
MaxConsec_t
\]

denotes the maximum number of consecutive periods teacher \(t\) prefers to teach without a break. Used in the definition of \(V_2\).

---

### 3.3.16 Undesirable Laboratory Slot Indicator

\[
BadLabSlot_p\in\{0,1\}
\]

where \(BadLabSlot_p=1\) if period \(p\) falls in a portion of the day the institution prefers not to use for laboratory sessions (e.g. the first half of the day). Used in the definition of \(V_5\).

---

## 3.4 Decision Variables

### 3.4.1 Primary Assignment Variable

\[
x_{g,s,k,t,r,d,p}\in\{0,1\},\qquad k\in K_{g,s}
\]

where \(x_{g,s,k,t,r,d,p}=1\) if teaching session \(k\) of subject \(s\), belonging to class group \(g\), is assigned to teacher \(t\), room \(r\), day \(d\), and period \(p\); otherwise it is \(0\).

\[
\boxed{
(g,s,k,t,r,d,p)
}
\]

### 3.4.2 Auxiliary Variable — Year-Level Teaching Assignment

\[
z_{t,s,yl}\in\{0,1\}
\]

where \(z_{t,s,yl}=1\) if teacher \(t\) is designated to teach subject \(s\) for year level \(yl\). Used to formalize H6.

### 3.4.3 Auxiliary Variable — Laboratory Block Start

\[
b_{g,s,k,t,r,d,p}\in\{0,1\},\qquad (p,p+1)\in PP,\ L_s=1
\]

where \(b_{g,s,k,t,r,d,p}=1\) if laboratory session \(k\) begins at period \(p\) (occupying periods \(p\) and \(p+1\)). Used to formalize H13.

### 3.4.4 Derived Quantity — Teacher Occupancy

\[
Teach_{t,d,p}=\sum_{g\in G}\sum_{s\in S}\sum_{k\in K_{g,s}}\sum_{r\in R}x_{g,s,k,t,r,d,p}
\]

By H2, \(Teach_{t,d,p}\in\{0,1\}\): it indicates whether teacher \(t\) is teaching at time \((d,p)\). Used in \(V_2\) and \(V_3\).

### 3.4.5 Derived Quantity — Subject-on-Day Indicator

\[
SubjDay_{g,s,d}=\mathbb{1}\!\left[\sum_{k\in K_{g,s}}\sum_{t\in T}\sum_{r\in R}\sum_{p\in P}x_{g,s,k,t,r,d,p}\ge1\right]
\]

Indicates whether class group \(g\) has at least one session of subject \(s\) on day \(d\). Used in \(V_4\). (Standard 0/1 linearization applies for implementation.)

### 3.4.6 Soft-Constraint Violation Measures

\[
V_i,\qquad i=1,\ldots,5
\]

denotes the violation measure associated with soft constraint \(S_i\), defined explicitly in Section 3.6.

---

## 3.5 Hard Constraints

Hard constraints must always be satisfied.

### H1 — Every Session Assigned Exactly Once

For every class group \(g\), subject \(s\), and teaching session \(k\in K_{g,s}\):

\[
\sum_{t\in T}\sum_{r\in R}\sum_{d\in D}\sum_{p\in P}x_{g,s,k,t,r,d,p}=1
\]

Every required teaching session must occur exactly once.

---

### H2 — Teacher No Double Booking

For every teacher \(t\), day \(d\), and period \(p\):

\[
\sum_{g\in G}\sum_{s\in S}\sum_{k\in K_{g,s}}\sum_{r\in R}x_{g,s,k,t,r,d,p}\le1
\]

A teacher cannot teach two sessions at the same time.

---

### H3 — Room No Double Booking

For every room \(r\), day \(d\), and period \(p\):

\[
\sum_{g\in G}\sum_{s\in S}\sum_{k\in K_{g,s}}\sum_{t\in T}x_{g,s,k,t,r,d,p}\le1
\]

A room cannot host two sessions at the same time.

---

### H4 — Group No Double Booking

For every class group \(g\), day \(d\), and period \(p\):

\[
\sum_{s\in S}\sum_{k\in K_{g,s}}\sum_{t\in T}\sum_{r\in R}x_{g,s,k,t,r,d,p}\le1
\]

A class section cannot attend two sessions at the same time.

---

### H5 — Department Consistency

A teacher can teach a class group only when the teacher belongs to the department associated with that class group:

\[
x_{g,s,k,t,r,d,p}=1
\Rightarrow
dept(t)=dept(g)
\]

Equivalently, an assignment is allowed only when there exists a department \(dpt\) such that \(TD_{t,dpt}=1\) and \(GD_{g,dpt}=1\).

---

### H6 — Teacher Eligibility and Year-Level Subject Assignment

A teacher can only teach subjects for which the teacher is designated:

\[
x_{g,s,k,t,r,d,p}\le E_{t,s}
\]

To formally enforce that a teacher teaches at most one subject per year level, the assignment must be consistent with the year-level designation variable \(z_{t,s,yl}\) (3.4.2):

\[
x_{g,s,k,t,r,d,p}\le z_{t,s,\,yl(g)}
\]

\[
\sum_{s\in S} z_{t,s,yl}\le1 \qquad \forall t\in T,\ yl\in YL
\]

The second constraint restricts each teacher to at most one designated subject per year level; the first constraint ties every timetable assignment to that designation. A teacher may hold a different designation \(z_{t,s',yl'}\) for a different year level \(yl'\neq yl\), while remaining within the same department.

---

### H7 — Laboratory Subject Requires Laboratory Room

If \(L_s=1\), the assigned room must satisfy \(LR_r=1\):

\[
x_{g,s,k,t,r,d,p}=1
\Rightarrow LR_r=1
\]

---

### H8 — Room Capacity

For every assignment:

\[
x_{g,s,k,t,r,d,p}=1
\Rightarrow
N_g\le C_r
\]

The room must be large enough for the entire class section.

---

### H9 — Teacher Availability

\[
x_{g,s,k,t,r,d,p}\le A_{t,d,p}
\]

A teacher cannot be assigned during an unavailable period.

---

### H10 — Room Availability

\[
x_{g,s,k,t,r,d,p}\le A_{r,d,p}
\]

A room cannot be used when it is unavailable.

---

### H11 — Group Availability

\[
x_{g,s,k,t,r,d,p}\le A_{g,d,p}
\]

A class group cannot be scheduled when it is unavailable.

---

### H12 — Fixed Classroom for Each Class Group

\[
\boxed{
x_{g,s,k,t,r,d,p}\le FR_{g,r}
}
\]

If \(FR_{g,r}=0\), room \(r\) cannot be assigned to class group \(g\). Consequently, the same class group remains in its designated classroom throughout the semester rather than changing classrooms from period to period.

---

### H13 — Laboratory Consecutive Periods

For a laboratory subject (\(L_s=1\)), each session must occupy a valid consecutive pair \((p,p+1)\in PP\), formalized via the block-start variable \(b_{g,s,k,t,r,d,p}\) (3.4.3):

\[
\sum_{t\in T}\sum_{r\in R}\sum_{d\in D}\sum_{(p,p+1)\in PP} b_{g,s,k,t,r,d,p}=1 \qquad \forall (g,s,k):L_s=1
\]

\[
x_{g,s,k,t,r,d,p}=b_{g,s,k,t,r,d,p}, \qquad x_{g,s,k,t,r,d,p+1}=b_{g,s,k,t,r,d,p}
\]

The first constraint requires exactly one valid block to be chosen per lab session; the second ties the two occupied periods to the same teacher and room. This prevents laboratory sessions from being split across non-consecutive periods or assigned to two different rooms/teachers.

---

### H14 — Maximum Daily Teaching Load

For every teacher \(t\) and day \(d\):

\[
\sum_{p\in P}Teach_{t,d,p}\le MaxLoad_t
\]

A teacher cannot be scheduled beyond their maximum permitted periods on a single day.

---

## 3.6 Soft Constraints

Soft constraints represent desirable timetable properties. Their violations are permitted but penalized. Each is expressed as an explicit violation measure \(V_i\) computed over the assignment variables.

### S1 — Teacher Preferences

Penalizes assignments made during periods a teacher has marked as avoided:

\[
V_1=\sum_{t\in T}\sum_{g,s,k,r}\sum_{d\in D}\sum_{p\in P}x_{g,s,k,t,r,d,p}\cdot Avoid_{t,d,p}
\]

---

### S2 — Consecutive Sessions

Penalizes runs of consecutive teaching periods longer than a teacher's preferred maximum, using a sliding window over \(Teach_{t,d,p}\) (3.4.4):

\[
V_2=\sum_{t\in T}\sum_{d\in D}\sum_{\substack{p\in P\\ p+MaxConsec_t\le \max(P)}}\ \prod_{j=0}^{MaxConsec_t} Teach_{t,d,p+j}
\]

Each term equals 1 only if teacher \(t\) teaches every period in a window one period longer than their preferred maximum, i.e. a genuine over-length run. (Implementable via a standard reified AND / auxiliary indicator per window.)

---

### S3 — Teacher Gaps

Penalizes idle periods between a teacher's first and last teaching period on a given day. Let \(first_{t,d}\) and \(last_{t,d}\) denote the earliest and latest period with \(Teach_{t,d,p}=1\):

\[
GapCount_{t,d}=\big(last_{t,d}-first_{t,d}+1\big)-\sum_{p\in P}Teach_{t,d,p}
\]

\[
V_3=\sum_{t\in T}\sum_{d\in D}GapCount_{t,d}
\]

(\(first_{t,d}\), \(last_{t,d}\) are standard min/max-of-indicator quantities, linearizable via OR-Tools' built-in `AddMinEquality`/`AddMaxEquality` or equivalent reified constraints.)

---

### S4 — Back-to-Back Subjects

Penalizes the same subject being scheduled for the same class group on two consecutive working days, using \(SubjDay_{g,s,d}\) (3.4.5):

\[
V_4=\sum_{g\in G}\sum_{s\in S}\sum_{\substack{d,d+1\in D}} SubjDay_{g,s,d}\cdot SubjDay_{g,s,d+1}
\]

---

### S5 — Laboratory Placement

Penalizes laboratory sessions placed in institutionally undesirable periods, using \(BadLabSlot_p\) (3.3.16):

\[
V_5=\sum_{g,s,k,t,r}\sum_{d\in D}\sum_{p\in P} x_{g,s,k,t,r,d,p}\cdot L_s\cdot BadLabSlot_p
\]

The laboratory's use of a laboratory room and its consecutive-period requirement remain hard constraints (H7, H13); this soft constraint concerns only the preferred *placement* of the block within the day.

---

### Note on Substitute Workload Fairness

Substitute workload fairness is **not** included as a weekly soft constraint, since no substitution has occurred at the time the base timetable is generated — there is nothing yet to balance. It is instead formalized entirely within the Minimal Perturbation Problem (Section 3.9.8–3.9.9), where it is a meaningful, measurable quantity (the historical/cumulative distribution of substitution duties). This keeps each soft term tied to a stage of the pipeline where it is actually computable.

---

## 3.7 Penalty Weights

Each soft constraint receives a non-negative penalty weight:

\[
w_i\ge0,\qquad i=1,\ldots,5
\]

representing the relative importance of the corresponding soft constraint. The weights are configurable according to institutional priorities (exposed as sliders in the system's frontend).

---

## 3.8 Objective Function

The total soft-constraint penalty is:

\[
Z=w_1V_1+w_2V_2+w_3V_3+w_4V_4+w_5V_5
\]

The scheduling objective is:

\[
\boxed{
\begin{aligned}
\min\quad & w_1V_1+w_2V_2+w_3V_3+w_4V_4+w_5V_5\\
\text{subject to}\quad& H_1,\ldots,H_{14}\\
& x_{g,s,k,t,r,d,p},\,z_{t,s,yl},\,b_{g,s,k,t,r,d,p}\in\{0,1\}
\end{aligned}
}
\]

The CP-SAT stage first obtains a feasible timetable satisfying \(H_1,\ldots,H_{14}\). Simulated Annealing then searches for an improved feasible timetable with a lower weighted soft-constraint penalty \(Z\), preserving feasibility throughout.

---

## 3.9 Staff Substitution / Minimal Perturbation Problem

Staff absence is handled independently from the complete weekly timetable.

Let \(t_a\in T\) denote the absent teacher, and let \(\mathcal{A}\) denote the set of sessions affected by the absence (i.e. sessions originally assigned to \(t_a\) on the day of absence). Let \(x^{*}\) denote the original (pre-absence) assignment for sessions in \(\mathcal{A}\). Only sessions in \(\mathcal{A}\) are eligible for reassignment; all other sessions remain fixed at their \(x^{*}\) values by construction.

### 3.9.1 Substitute Assignment Variable

\[
y_{g,s,t,r,d,p}\in\{0,1\},\qquad (g,s,d,p)\text{ ranges over }\mathcal{A}
\]

where \(y_{g,s,t,r,d,p}=1\) if teacher \(t\) is assigned as substitute for the affected session of class group \(g\), subject \(s\), in room \(r\), at day \(d\), period \(p\).

---

### 3.9.2 Substitute Department Consistency

\[
dept(t)=dept(g)
\]

---

### 3.9.3 Substitute Eligibility

\[
E_{t,s}=1
\]

---

### 3.9.4 Substitute Availability

\[
A_{t,d,p}=1
\]

---

### 3.9.5 Substitute No Double Booking

A substitute cannot already be assigned to another session (in \(x^{*}\) or in \(y\)) at the same time; the substitution solution must preserve teacher no-double-booking exactly as H2 does for the base timetable.

---

### 3.9.6 Fixed Classroom Preservation

The affected class group remains in its fixed classroom: for every \(a=(g,s,d,p)\in\mathcal{A}\), the room component of \(y_a\) must equal the room component of \(x^{*}_a\). Substitution does not move the class group to a different classroom merely because the original teacher is absent.

---

### 3.9.7 Existing-Schedule Preservation

Unaffected teachers, class groups, rooms, and sessions remain unchanged by construction, since \(y\) is only defined over \(\mathcal{A}\). The substitution process therefore changes only the minimum necessary portion of the timetable by design; Section 3.9.9 further minimizes changes *within* \(\mathcal{A}\) itself (e.g. avoiding unnecessary room or period shifts even for affected sessions).

---

### 3.9.8 Substitute Workload Fairness

Let \(SubCount_t\) denote the cumulative number of substitution duties assigned to teacher \(t\) over the tracked period (including the assignment currently being made), and let \(\overline{SubCount}\) be the mean of \(SubCount_t\) over all teachers eligible for the current substitution pool \(T_{elig}=\{t : E_{t,s}=1,\ dept(t)=dept(g),\ A_{t,d,p}=1\}\). Fairness cost is defined as the variance of substitute load across that pool:

\[
C_{\text{fairness}}=\sum_{t\in T_{elig}}\big(SubCount_t-\overline{SubCount}\big)^2
\]

(A normalized Gini coefficient over \(SubCount_t\) is an acceptable alternative formulation and may be reported alongside variance in the evaluation.)

---

### 3.9.9 Minimal Perturbation Objective

Define the cost of changes made to the existing timetable, restricted to affected sessions, as deviation in room, day, or period from the original assignment (teacher necessarily changes for every \(a\in\mathcal{A}\), so teacher identity is excluded from this term):

\[
C_{\text{changes}}=\sum_{a=(g,s,d,p)\in\mathcal{A}}\ \mathbb{1}\!\left[r(y_a)\neq r(x^{*}_a)\right]+\mathbb{1}\!\left[d(y_a)\neq d(x^{*}_a)\right]+\mathbb{1}\!\left[p(y_a)\neq p(x^{*}_a)\right]
\]

Define the cost of affected sessions left without a substitute:

\[
C_{\text{unassigned}}=\sum_{a=(g,s,d,p)\in\mathcal{A}}\left(1-\sum_{t,r} y_{g,s,t,r,d,p}\right)
\]

(a session marked SELF STUDY contributes 1 to this term).

With \(C_{\text{fairness}}\) as defined in 3.9.8, the substitution objective is:

\[
\boxed{
\min\left(\alpha\, C_{\text{changes}}+\beta\, C_{\text{unassigned}}+\gamma\, C_{\text{fairness}}\right)
}
\]

subject to 3.9.2–3.9.7, where \(\alpha,\beta,\gamma\ge0\) are substitution objective weights. The resulting solution replaces the absent teacher while preserving the existing timetable as far as possible and distributing substitution load fairly.

---

## 3.10 Overall Optimization Architecture

\[
\boxed{
\text{Institutional Data}
\rightarrow
\text{Mathematical Model}
\rightarrow
\text{CP-SAT}
\rightarrow
\text{Feasible Timetable}
}
\]

followed by:

\[
\boxed{
\text{Feasible Timetable}
\rightarrow
\text{Soft-Constraint Evaluation}
\rightarrow
\text{Simulated Annealing}
\rightarrow
\text{Optimized Timetable}
}
\]

When a teacher becomes absent:

\[
\boxed{
\text{Existing Timetable}
\rightarrow
\text{Affected Sessions}
\rightarrow
\text{MPP Substitution}
\rightarrow
\text{Minimal Timetable Changes}
}
\]

The final system therefore separates:

- **hard feasibility** (H1–H14)
- **soft optimization** (V1–V5, weighted by w1–w5)
- **dynamic staff substitution** (y, subject to 3.9.2–3.9.7)
- **timetable stability** (\(C_{\text{changes}}\), \(C_{\text{unassigned}}\))
- **substitute workload fairness** (\(C_{\text{fairness}}\))
