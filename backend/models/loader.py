from sqlalchemy.orm import sessionmaker
from pathlib import Path
from ..excel_reader.reader import read_excel
from .models import engine, Staff, Rooms, Subjects, ClassGroups, Periods, Preferences, StaffSubjects, SessionRequirement

WORKING_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

def get_session():
    Session = sessionmaker(bind=engine)
    return Session()

def load_staffs(session, data):
    for row in data["Staff"]:
        session.add(Staff(
            staff_name = row["staff_name"],
            email = row["email"],
            department = row["department"],
            max_periods_per_day = row["max_periods_per_day"]
        ))

def load_class_groups(session, data):
    for row in data["ClassGroups"]:
        session.add(ClassGroups(
            department=row["department"],
            section=row["section"],
            year=row["year"],
            num_students=row["num_students"],
            assigned_room=row["assigned_room"],
        ))

def load_subjects(session, data):
    for row in data["Subjects"]:
        session.add(Subjects(
            subject_code=row["subject_code"],
            subject_name=row["subject_name"],
            department=row["department"],
            sessions_per_week=row["sessions_per_week"],
            needs_lab=row["needs_lab"] == "Yes",
        ))

def load_rooms(session, data):
    for row in data["Rooms"]:
        session.add(Rooms(
            room_number=row["room_number"],
            room_type=row["room_type"],
            capacity=row["capacity"],
            building=row["building"],
            floor=row["floor"],
            dept_preference=row["dept_preference"],
        ))

def load_periods(session, data):
    for day in WORKING_DAYS:
        for row in data["Periods"]:
            session.add(Periods(
                day=day,
                period_number=row["period_number"],
                start_time=str(row["start_time"]),
                end_time=str(row["end_time"]),
                is_break=row["is_break"] == "Yes",
            ))

def load_staff_subjects(session, data):
    unmatched = []

    for row in data["StaffSubjects"]:
        staff = (
            session.query(Staff)
            .filter_by(staff_name = row["staff_name"])
            .first()
        )
        subject = (
            session.query(Subjects)
            .filter_by(subject_code = row["subject_code"])
            .first()
        )
        if staff and subject:
            session.add(StaffSubjects(
                staff_id = staff.id,
                subject_id = subject.id,
                department = row["department"],
                year = row["year"]
            ))
        else:
            unmatched.append(row)

    if unmatched:
        raise ValueError(
            "StaffSubjects rows could not be matched to existing Staff/Subjects"
            f"records (check for typos/whitespace): {unmatched}"
        )

def load_preferences(session, data):
    for row in data["Preferences"]:
        staff = (
            session.query(Staff)
            .filter_by(staff_name = row["staff_name"])
            .first()
        )

        if not staff:
            raise ValueError(f"Preferences row references unknown staff: {row["staff_name"]!r}")

        session.add(Preferences(
            staff_id = staff.id,
            preferred_periods = [
                int(x.strip()) for x in str(row["preferred_periods"]).split(",")
            ],
            avoid_periods = [
                int(x.strip()) for x in str(row["avoid_periods"]).split(",")
            ],
            max_consecutive = row["max_consecutive"]
        ))

def room_id_for(session, room_number):
    room = (
        session.query(Rooms)
        .filter_by(room_number = room_number)
        .first()
    )
    return room.id if room else None

def load_session_requirements(session):
    class_groups = session.query(ClassGroups).all()

    for group in class_groups:
        offerings = (
            session.query(StaffSubjects)
            .filter_by(department = group.department, year = group.year)
            .all()
        )

        seen_subject_ids = set()
        for offering in offerings:
            if offering.subject_id in seen_subject_ids:
                continue
            seen_subject_ids.add(offering.subject_id)

            subject = session.get(Subjects, offering.subject_id)
            if subject is None:
                continue

            room_id = None if subject.needs_lab else room_id_for(session, group.assigned_room)
            periods_per_instance = 2 if subject.needs_lab else 1

            for _ in range(subject.sessions_per_week):
                session.add(SessionRequirement(
                    subject_type = "LAB" if subject.needs_lab else "THEORY",
                    subject_id = subject.id,
                    staff_id = None,
                    group_id = group.id,
                    room_id = room_id,
                    timeslot = None,
                    no_of_periods = periods_per_instance
                ))

def main():
    session = get_session()

    file_path = Path(__file__).resolve().parent.parent / "excel_reader" / "testcase_1.xlsx"
    data = read_excel(file_path)

    session.query(Preferences).delete()
    session.query(SessionRequirement).delete()
    session.query(StaffSubjects).delete()
    session.query(Periods).delete()
    session.query(Rooms).delete()
    session.query(Subjects).delete()
    session.query(ClassGroups).delete()
    session.query(Staff).delete()

    session.commit()

    load_staffs(session, data)
    load_class_groups(session, data)
    load_subjects(session, data)
    load_rooms(session, data)
    load_periods(session, data)
    session.commit()

    load_staff_subjects(session, data)
    load_preferences(session, data)
    session.commit()

    load_session_requirements(session)
    session.commit()

    session.close()

    #print("Data loaded successfully!")

if __name__ == "__main__":
    main()