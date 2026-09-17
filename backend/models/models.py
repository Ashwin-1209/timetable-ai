from sqlalchemy import create_engine, Column, Integer, String, JSON, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base
from pathlib import Path

Base = declarative_base()

db_path = Path(__file__).resolve().parent / "timetable.db"

engine = create_engine(f"sqlite:///{db_path}")

class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key = True)
    staff_name = Column(String)
    email = Column(String)
    department = Column(String)
    max_periods_per_day = Column(Integer)

class StaffSubjects(Base):
    __tablename__ = "staff_subjects"

    id = Column(Integer, primary_key = True)
    staff_id = Column(Integer, ForeignKey("staff.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    department = Column(String)
    year = Column(String)

class ClassGroups(Base):
    __tablename__ = "class_groups"

    id = Column(Integer, primary_key = True)
    department = Column(String)
    section = Column(String)
    year = Column(String)
    num_students = Column(Integer)
    assigned_room = Column(String)

class Subjects(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key = True)
    subject_code = Column(String)
    subject_name = Column(String)
    department = Column(String)
    sessions_per_week = Column(Integer)
    needs_lab = Column(Boolean)

class Rooms(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key = True)
    room_number = Column(String)
    room_type = Column(String)
    capacity = Column(Integer)
    building = Column(String)
    floor = Column(Integer)
    dept_preference = Column(String)

class Periods(Base):
    __tablename__ = "periods"

    id = Column(Integer, primary_key = True)
    day = Column(String)
    period_number = Column(Integer)
    start_time = Column(String)
    end_time = Column(String)
    is_break = Column(Boolean)

class Preferences(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key = True)
    staff_id = Column(Integer, ForeignKey("staff.id"))
    preferred_periods = Column(JSON)
    avoid_periods = Column(JSON)
    max_consecutive = Column(Integer)

class SessionRequirement(Base):
    __tablename__ = "session_requirements"

    id = Column(Integer, primary_key = True)
    subject_type = Column(String)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable = True)
    group_id = Column(Integer, ForeignKey("class_groups.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable = True)
    timeslot = Column(String, nullable = True)
    no_of_periods = Column(Integer)

class ScheduledSession(Base):
    __tablename__ = "scheduled_sessions"

    id = Column(Integer, primary_key = True)
    requirement_id = Column(Integer, ForeignKey("session_requirements.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    timeslot_id = Column(Integer, ForeignKey("periods.id"))
    is_locked = Column(Boolean)

class Timetable(Base):
    __tablename__ = "timetable"

    id = Column(Integer, primary_key = True)
    name = Column(String)
    status = Column(String)
    created = Column(String)
    score = Column(Integer)

def init_db():
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()