"""Build the synthetic university database deterministically.

Usage:
    python data/generate_db.py            # writes data/university.db
    python data/generate_db.py --out x.db

Everything is driven by one seed (42), so running it twice gives identical
data. The script prints row counts, a few sanity queries and a content
fingerprint (SHA-256 over every row) that you can compare across machines.

Reference point: the "current" academic year is 2026-27 (odd semester in
progress, so attendance exists for it but exam results do not yet).
"""

import argparse
import hashlib
import random
import sqlite3
from pathlib import Path

from faker import Faker

SEED = 42
DATA_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = DATA_DIR / "schema.sql"
DEFAULT_DB = DATA_DIR / "university.db"

CURRENT_YEAR_START = 2026          # academic year 2026-27
HOSTEL_FEE = 110_000               # per year, added to amount_due for hostel residents

# (program_name, department, duration_years, course_code_prefix, students, annual tuition)
PROGRAMS = [
    ("B.Tech CSE", "Computer Science & Engineering", 4, "CSE", 120, 325_000),
    ("B.Tech ECE", "Electronics & Communication Engineering", 4, "ECE", 60, 295_000),
    ("B.Tech ME", "Mechanical Engineering", 4, "MEC", 45, 275_000),
    ("BCA", "Computer Applications", 3, "BCA", 60, 185_000),
    ("BBA", "Management", 3, "BBA", 70, 210_000),
    ("B.Com (Hons)", "Commerce", 3, "COM", 55, 145_000),
    ("B.Sc Physics", "Physics", 3, "PHY", 35, 120_000),
    ("MBA", "Management", 2, "MBA", 55, 450_000),
]

# Two courses per semester, listed semester by semester.
COURSES = {
    "B.Tech CSE": [
        "Programming in C", "Engineering Mathematics I",
        "Data Structures", "Engineering Mathematics II",
        "Object Oriented Programming", "Discrete Mathematics",
        "Database Management Systems", "Computer Organisation",
        "Operating Systems", "Design and Analysis of Algorithms",
        "Computer Networks", "Theory of Computation",
        "Machine Learning", "Compiler Design",
        "Cloud Computing", "Major Project",
    ],
    "B.Tech ECE": [
        "Basic Electrical Engineering", "Engineering Mathematics I",
        "Electronic Devices", "Engineering Mathematics II",
        "Network Analysis", "Signals and Systems",
        "Analog Circuits", "Digital Electronics",
        "Microprocessors", "Electromagnetic Theory",
        "Communication Systems", "Control Systems",
        "VLSI Design", "Digital Signal Processing",
        "Embedded Systems", "Major Project",
    ],
    "B.Tech ME": [
        "Engineering Mechanics", "Engineering Mathematics I",
        "Engineering Drawing", "Engineering Mathematics II",
        "Thermodynamics", "Strength of Materials",
        "Fluid Mechanics", "Manufacturing Processes",
        "Theory of Machines", "Heat Transfer",
        "Machine Design", "IC Engines",
        "CAD/CAM", "Refrigeration and Air Conditioning",
        "Automobile Engineering", "Major Project",
    ],
    "BCA": [
        "Programming Fundamentals", "Mathematics for Computing",
        "Data Structures using C", "Digital Logic",
        "Java Programming", "Database Systems",
        "Web Technologies", "Software Engineering",
        "Python Programming", "Computer Networks",
        "Mobile App Development", "Project Work",
    ],
    "BBA": [
        "Principles of Management", "Business Economics",
        "Financial Accounting", "Business Communication",
        "Marketing Management", "Organisational Behaviour",
        "Human Resource Management", "Business Statistics",
        "Financial Management", "Business Law",
        "Entrepreneurship", "Strategic Management",
    ],
    "B.Com (Hons)": [
        "Financial Accounting", "Business Economics",
        "Corporate Accounting", "Business Mathematics",
        "Cost Accounting", "Income Tax Law",
        "Company Law", "Banking and Insurance",
        "Auditing", "Goods and Services Tax",
        "Financial Markets", "Management Accounting",
    ],
    "B.Sc Physics": [
        "Mechanics", "Calculus",
        "Electricity and Magnetism", "Waves and Optics",
        "Thermal Physics", "Mathematical Physics",
        "Quantum Mechanics", "Analog Electronics",
        "Solid State Physics", "Nuclear Physics",
        "Statistical Mechanics", "Physics Project",
    ],
    "MBA": [
        "Managerial Economics", "Accounting for Managers",
        "Marketing Management", "Corporate Finance",
        "Operations Management", "Business Analytics",
        "Strategic Management", "Capstone Project",
    ],
}

# (hostel_name, gender, capacity)
HOSTELS = [
    ("Aryabhatta Hall", "M", 110),
    ("C.V. Raman Hall", "M", 90),
    ("Homi Bhabha Hall", "M", 40),
    ("Kalpana Chawla Hall", "F", 90),
    ("Sarojini Naidu Hall", "F", 70),
]

HOSTEL_PROBABILITY = 0.62          # chance a student applies for a hostel


def academic_year(start: int) -> str:
    """2026 -> '2026-27'."""
    return f"{start}-{str(start + 1)[-2:]}"


def grade_for(total: int) -> str:
    for cutoff, grade in [(90, "O"), (80, "A+"), (70, "A"), (60, "B+"),
                          (50, "B"), (45, "C"), (40, "P")]:
        if total >= cutoff:
            return grade
    return "F"


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def build(db_path: Path) -> None:
    rng = random.Random(SEED)
    fake = Faker("en_IN")
    Faker.seed(SEED)

    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_PATH.read_text())

    # programs + courses
    program_ids = {}
    course_rows = []                 # (course_id, program_name, semester)
    course_id = 0
    for pid, (name, dept, duration, prefix, _, _) in enumerate(PROGRAMS, start=1):
        conn.execute("INSERT INTO programs VALUES (?,?,?,?)", (pid, name, dept, duration))
        program_ids[name] = pid
        names = COURSES[name]
        assert len(names) == duration * 4, name
        for i, cname in enumerate(names):
            semester = i // 2 + 1
            code = f"{prefix}{semester}0{i % 2 + 1}"
            credits = 6 if "Project" in cname else rng.choice([3, 4, 4])
            course_id += 1
            conn.execute("INSERT INTO courses VALUES (?,?,?,?,?,?)",
                         (course_id, code, cname, pid, semester, credits))
            course_rows.append((course_id, name, semester))

    # hostels
    hostel_free = {}
    for hid, (hname, hgender, cap) in enumerate(HOSTELS, start=1):
        conn.execute("INSERT INTO hostels VALUES (?,?,?,?)", (hid, hname, hgender, cap))
        hostel_free[hid] = cap

    # students
    students = []                    # dicts kept for fees / enrollments
    sid = 0
    for name, _, duration, _, count, tuition in PROGRAMS:
        first_admission = CURRENT_YEAR_START - duration + 1
        for _ in range(count):
            sid += 1
            male_share = 0.75 if name == "B.Tech ME" else 0.55
            gender = "M" if rng.random() < male_share else "F"
            first = fake.first_name_male() if gender == "M" else fake.first_name_female()
            last = fake.last_name()
            admission = rng.randint(first_admission, CURRENT_YEAR_START)
            current_year = CURRENT_YEAR_START - admission + 1

            hostel_id = None
            if rng.random() < HOSTEL_PROBABILITY:
                options = [h for h, (_, g, _) in enumerate(HOSTELS, start=1)
                           if g == gender and hostel_free[h] > 0]
                if options:
                    hostel_id = rng.choice(options)
                    hostel_free[hostel_id] -= 1

            handle = f"{first}.{last}".lower().replace(" ", "").replace("'", "")
            email = f"{handle}{sid}@students.univ.example"
            conn.execute("INSERT INTO students VALUES (?,?,?,?,?,?,?,?)",
                         (sid, f"{first} {last}", gender, program_ids[name],
                          admission, current_year, hostel_id, email))
            students.append({
                "id": sid, "program": name, "admission": admission,
                "current_year": current_year, "hostel": hostel_id, "tuition": tuition,
                # latent traits that make attendance and marks correlated
                "attend_base": clamp(rng.gauss(83, 9), 40, 99),
                "ability": clamp(rng.gauss(64, 13), 25, 95),
                "payer": rng.random(),
            })

    # enrollments, attendance, exam results
    courses_by_prog_sem = {}
    for cid, pname, sem in course_rows:
        courses_by_prog_sem.setdefault((pname, sem), []).append(cid)

    eid = 0
    for s in students:
        for year_no in range(1, s["current_year"] + 1):
            start = s["admission"] + year_no - 1
            is_current = start == CURRENT_YEAR_START
            # current year: only the odd semester has started
            semesters = [2 * year_no - 1] if is_current else [2 * year_no - 1, 2 * year_no]
            for sem in semesters:
                for cid in courses_by_prog_sem[(s["program"], sem)]:
                    eid += 1
                    conn.execute("INSERT INTO enrollments VALUES (?,?,?,?)",
                                 (eid, s["id"], cid, academic_year(start)))
                    held = rng.randint(28, 34) if is_current else rng.randint(40, 48)
                    pct = clamp(s["attend_base"] + rng.gauss(0, 6), 20, 100)
                    attended = min(held, round(held * pct / 100))
                    conn.execute("INSERT INTO attendance VALUES (?,?,?)", (eid, held, attended))
                    if not is_current:
                        total = clamp(round(s["ability"] + (pct - 80) * 0.3 + rng.gauss(0, 8)), 12, 98)
                        internal = clamp(round(total * 0.4 + rng.gauss(0, 2)), 0, 40)
                        external = clamp(total - internal, 0, 60)
                        conn.execute("INSERT INTO exam_results VALUES (?,?,?,?)",
                                     (eid, internal, external, grade_for(internal + external)))

    # fees: one row per student per academic year attended
    fid = 0
    for s in students:
        for year_no in range(1, s["current_year"] + 1):
            start = s["admission"] + year_no - 1
            due = s["tuition"] + (HOSTEL_FEE if s["hostel"] else 0)
            if start == CURRENT_YEAR_START:
                # current year: plenty of pending dues
                r = (s["payer"] + rng.random()) / 2
                status = "PAID" if r < 0.62 else ("PARTIAL" if r < 0.85 else "UNPAID")
                due_date = "2026-08-20" if year_no == 1 else "2026-07-31"
            else:
                r = rng.random()
                status = "PAID" if r < 0.95 else ("PARTIAL" if r < 0.99 else "UNPAID")
                due_date = f"{start}-07-31"
            if status == "PAID":
                paid = due
            elif status == "PARTIAL":
                paid = round(due * rng.uniform(0.3, 0.8) / 1000) * 1000
            else:
                paid = 0
            fid += 1
            conn.execute("INSERT INTO fees VALUES (?,?,?,?,?,?,?)",
                         (fid, s["id"], academic_year(start), due, paid, due_date, status))

    conn.commit()
    conn.close()


def fingerprint(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    h = hashlib.sha256()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for t in tables:
        h.update(t.encode())
        for row in conn.execute(f"SELECT * FROM {t} ORDER BY 1"):
            h.update(repr(row).encode())
    conn.close()
    return h.hexdigest()


def report(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    print(f"Database: {db_path}")
    print("\nRow counts:")
    for t in ["programs", "hostels", "students", "courses", "enrollments",
              "attendance", "exam_results", "fees"]:
        print(f"  {t:<13} {conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")

    checks = {
        "Day scholars (no hostel)":
            "SELECT COUNT(*) FROM students WHERE hostel_id IS NULL",
        "Fee status, 2026-27":
            "SELECT status, COUNT(*) FROM fees WHERE academic_year='2026-27' GROUP BY status",
        "Total pending dues, all years (Rs)":
            "SELECT SUM(amount_due - amount_paid) FROM fees",
        "Enrollments under 75% attendance, 2026-27":
            "SELECT COUNT(*) FROM attendance a JOIN enrollments e USING(enrollment_id) "
            "WHERE e.academic_year='2026-27' AND 100.0*a.classes_attended/a.classes_held < 75",
        "Grade distribution":
            "SELECT grade, COUNT(*) FROM exam_results GROUP BY grade ORDER BY grade",
        "Hostel occupancy":
            "SELECT h.hostel_name, COUNT(s.student_id), h.capacity FROM hostels h "
            "LEFT JOIN students s ON s.hostel_id = h.hostel_id GROUP BY h.hostel_id",
    }
    print("\nSanity queries:")
    for label, q in checks.items():
        print(f"  {label}: {conn.execute(q).fetchall()}")
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    print(f"\nForeign key violations: {len(fk)}")
    conn.close()
    print(f"Content fingerprint (sha256): {fingerprint(db_path)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    build(args.out)
    report(args.out)


if __name__ == "__main__":
    main()
