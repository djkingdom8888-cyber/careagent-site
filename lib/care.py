"""Facility-scoped data access for residents, medications (eMAR), and tasks (ADLs).

Every read/write here takes a facility_id and enforces it against the resident's
actual facility via SQL join, so one facility's staff can never touch another
facility's records even if they guess an id.
"""
import datetime

from . import db


def today_str():
    return datetime.date.today().isoformat()


# ---------------- Residents ----------------

def list_residents(facility_id, include_inactive=False):
    with db.session() as conn:
        if include_inactive:
            q = "SELECT * FROM residents WHERE facility_id = ? ORDER BY name"
            return conn.execute(q, (facility_id,)).fetchall()
        q = "SELECT * FROM residents WHERE facility_id = ? AND active = 1 ORDER BY name"
        return conn.execute(q, (facility_id,)).fetchall()


def get_resident(resident_id, facility_id):
    with db.session() as conn:
        return conn.execute(
            "SELECT * FROM residents WHERE id = ? AND facility_id = ?",
            (resident_id, facility_id),
        ).fetchone()


def create_resident(facility_id, name, room="", date_of_birth="", allergies="",
                     diagnoses="", emergency_contact="", notes=""):
    with db.session() as conn:
        cur = conn.execute(
            """INSERT INTO residents
               (facility_id, name, room, date_of_birth, allergies, diagnoses, emergency_contact, notes)
               VALUES (?,?,?,?,?,?,?,?)""",
            (facility_id, name, room, date_of_birth, allergies, diagnoses, emergency_contact, notes),
        )
        return cur.lastrowid


def update_resident(resident_id, facility_id, **fields):
    allowed = {"name", "room", "date_of_birth", "allergies", "diagnoses", "emergency_contact", "notes"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return
    with db.session() as conn:
        cols = ", ".join(f"{k} = ?" for k in sets)
        params = list(sets.values()) + [resident_id, facility_id]
        conn.execute(f"UPDATE residents SET {cols} WHERE id = ? AND facility_id = ?", params)


def set_resident_active(resident_id, facility_id, active):
    with db.session() as conn:
        conn.execute(
            "UPDATE residents SET active = ? WHERE id = ? AND facility_id = ?",
            (1 if active else 0, resident_id, facility_id),
        )


# ---------------- Medications / eMAR ----------------

def list_medications(resident_id, facility_id, include_inactive=False):
    with db.session() as conn:
        if include_inactive:
            q = """SELECT m.* FROM medications m JOIN residents r ON r.id = m.resident_id
                   WHERE m.resident_id = ? AND r.facility_id = ? ORDER BY m.name"""
        else:
            q = """SELECT m.* FROM medications m JOIN residents r ON r.id = m.resident_id
                   WHERE m.resident_id = ? AND r.facility_id = ? AND m.active = 1 ORDER BY m.name"""
        return conn.execute(q, (resident_id, facility_id)).fetchall()


def get_medication(med_id, facility_id):
    with db.session() as conn:
        return conn.execute(
            """SELECT m.* FROM medications m JOIN residents r ON r.id = m.resident_id
               WHERE m.id = ? AND r.facility_id = ?""",
            (med_id, facility_id),
        ).fetchone()


def create_medication(resident_id, facility_id, name, dose="", route="", instructions="", times=""):
    resident = get_resident(resident_id, facility_id)
    if not resident:
        raise ValueError("Resident not found for this facility")
    with db.session() as conn:
        cur = conn.execute(
            """INSERT INTO medications (resident_id, name, dose, route, instructions, times)
               VALUES (?,?,?,?,?,?)""",
            (resident_id, name, dose, route, instructions, times),
        )
        return cur.lastrowid


def update_medication(med_id, facility_id, **fields):
    med = get_medication(med_id, facility_id)
    if not med:
        raise ValueError("Medication not found for this facility")
    allowed = {"name", "dose", "route", "instructions", "times"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return
    with db.session() as conn:
        cols = ", ".join(f"{k} = ?" for k in sets)
        params = list(sets.values()) + [med_id]
        conn.execute(f"UPDATE medications SET {cols} WHERE id = ?", params)


def set_medication_active(med_id, facility_id, active):
    med = get_medication(med_id, facility_id)
    if not med:
        raise ValueError("Medication not found for this facility")
    with db.session() as conn:
        conn.execute("UPDATE medications SET active = ? WHERE id = ?", (1 if active else 0, med_id))


def _parse_times(times_csv):
    return [t.strip() for t in times_csv.split(",") if t.strip()]


def get_mar_for_date(resident_id, facility_id, date_str):
    """Return today's (or given date's) MAR rows for a resident, creating any
    missing 'due' rows for active medications' scheduled times first."""
    resident = get_resident(resident_id, facility_id)
    if not resident:
        raise ValueError("Resident not found for this facility")
    meds = list_medications(resident_id, facility_id)
    with db.session() as conn:
        for med in meds:
            for t in _parse_times(med["times"]):
                conn.execute(
                    """INSERT OR IGNORE INTO mar_logs (medication_id, scheduled_date, scheduled_time, status)
                       VALUES (?,?,?, 'due')""",
                    (med["id"], date_str, t),
                )
        rows = conn.execute(
            """SELECT ml.*, m.name AS med_name, m.dose, m.route, m.resident_id
               FROM mar_logs ml
               JOIN medications m ON m.id = ml.medication_id
               WHERE m.resident_id = ? AND ml.scheduled_date = ?
               ORDER BY ml.scheduled_time""",
            (resident_id, date_str),
        ).fetchall()
        return rows


def mark_mar(mar_log_id, facility_id, status, user_id, note=""):
    with db.session() as conn:
        row = conn.execute(
            """SELECT ml.id FROM mar_logs ml
               JOIN medications m ON m.id = ml.medication_id
               JOIN residents r ON r.id = m.resident_id
               WHERE ml.id = ? AND r.facility_id = ?""",
            (mar_log_id, facility_id),
        ).fetchone()
        if not row:
            raise ValueError("MAR entry not found for this facility")
        conn.execute(
            """UPDATE mar_logs SET status = ?, logged_by_user_id = ?, logged_at = datetime('now'), note = ?
               WHERE id = ?""",
            (status, user_id, note, mar_log_id),
        )


# ---------------- Tasks / ADLs ----------------

def list_tasks(resident_id, facility_id, include_inactive=False):
    with db.session() as conn:
        if include_inactive:
            q = """SELECT t.* FROM tasks t JOIN residents r ON r.id = t.resident_id
                   WHERE t.resident_id = ? AND r.facility_id = ? ORDER BY t.title"""
        else:
            q = """SELECT t.* FROM tasks t JOIN residents r ON r.id = t.resident_id
                   WHERE t.resident_id = ? AND r.facility_id = ? AND t.active = 1 ORDER BY t.title"""
        return conn.execute(q, (resident_id, facility_id)).fetchall()


def get_task(task_id, facility_id):
    with db.session() as conn:
        return conn.execute(
            """SELECT t.* FROM tasks t JOIN residents r ON r.id = t.resident_id
               WHERE t.id = ? AND r.facility_id = ?""",
            (task_id, facility_id),
        ).fetchone()


def create_task(resident_id, facility_id, title, shift="any"):
    resident = get_resident(resident_id, facility_id)
    if not resident:
        raise ValueError("Resident not found for this facility")
    with db.session() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (resident_id, title, shift) VALUES (?,?,?)",
            (resident_id, title, shift),
        )
        return cur.lastrowid


def set_task_active(task_id, facility_id, active):
    task = get_task(task_id, facility_id)
    if not task:
        raise ValueError("Task not found for this facility")
    with db.session() as conn:
        conn.execute("UPDATE tasks SET active = ? WHERE id = ?", (1 if active else 0, task_id))


def get_tasks_for_date(resident_id, facility_id, date_str):
    resident = get_resident(resident_id, facility_id)
    if not resident:
        raise ValueError("Resident not found for this facility")
    tasks = list_tasks(resident_id, facility_id)
    with db.session() as conn:
        for task in tasks:
            conn.execute(
                """INSERT OR IGNORE INTO task_logs (task_id, log_date, status) VALUES (?,?, 'pending')""",
                (task["id"], date_str),
            )
        rows = conn.execute(
            """SELECT tl.*, t.title, t.shift, t.resident_id
               FROM task_logs tl
               JOIN tasks t ON t.id = tl.task_id
               WHERE t.resident_id = ? AND tl.log_date = ?
               ORDER BY t.shift, t.title""",
            (resident_id, date_str),
        ).fetchall()
        return rows


def mark_task(task_log_id, facility_id, status, user_id, note=""):
    with db.session() as conn:
        row = conn.execute(
            """SELECT tl.id FROM task_logs tl
               JOIN tasks t ON t.id = tl.task_id
               JOIN residents r ON r.id = t.resident_id
               WHERE tl.id = ? AND r.facility_id = ?""",
            (task_log_id, facility_id),
        ).fetchone()
        if not row:
            raise ValueError("Task log not found for this facility")
        conn.execute(
            """UPDATE task_logs SET status = ?, completed_by_user_id = ?, completed_at = datetime('now'), note = ?
               WHERE id = ?""",
            (status, user_id, note, task_log_id),
        )


# ---------------- Billing ----------------

def dollars_to_cents(value):
    try:
        return round(float(str(value).replace("$", "").replace(",", "").strip()) * 100)
    except (ValueError, TypeError):
        raise ValueError("Invalid dollar amount")


def cents_to_dollars(cents):
    return "{:,.2f}".format((cents or 0) / 100)


def create_charge(resident_id, facility_id, description, amount_cents, category="rent",
                   charge_date=None, user_id=None):
    resident = get_resident(resident_id, facility_id)
    if not resident:
        raise ValueError("Resident not found for this facility")
    with db.session() as conn:
        cur = conn.execute(
            """INSERT INTO billing_charges (resident_id, description, category, amount_cents, charge_date, logged_by_user_id)
               VALUES (?,?,?,?,?,?)""",
            (resident_id, description, category, amount_cents, charge_date or today_str(), user_id),
        )
        return cur.lastrowid


def void_charge(charge_id, facility_id):
    with db.session() as conn:
        row = conn.execute(
            """SELECT bc.id FROM billing_charges bc
               JOIN residents r ON r.id = bc.resident_id
               WHERE bc.id = ? AND r.facility_id = ?""",
            (charge_id, facility_id),
        ).fetchone()
        if not row:
            raise ValueError("Charge not found for this facility")
        conn.execute("UPDATE billing_charges SET voided = 1 WHERE id = ?", (charge_id,))


def create_payment(resident_id, facility_id, amount_cents, method="check", payer="",
                    note="", paid_on=None, user_id=None):
    resident = get_resident(resident_id, facility_id)
    if not resident:
        raise ValueError("Resident not found for this facility")
    with db.session() as conn:
        cur = conn.execute(
            """INSERT INTO billing_payments (resident_id, amount_cents, method, payer, note, paid_on, logged_by_user_id)
               VALUES (?,?,?,?,?,?,?)""",
            (resident_id, amount_cents, method, payer, note, paid_on or today_str(), user_id),
        )
        return cur.lastrowid


def void_payment(payment_id, facility_id):
    with db.session() as conn:
        row = conn.execute(
            """SELECT bp.id FROM billing_payments bp
               JOIN residents r ON r.id = bp.resident_id
               WHERE bp.id = ? AND r.facility_id = ?""",
            (payment_id, facility_id),
        ).fetchone()
        if not row:
            raise ValueError("Payment not found for this facility")
        conn.execute("UPDATE billing_payments SET voided = 1 WHERE id = ?", (payment_id,))


def get_billing_ledger(resident_id, facility_id):
    """Returns (ledger, totals) — ledger is charges+payments merged and sorted newest first."""
    resident = get_resident(resident_id, facility_id)
    if not resident:
        raise ValueError("Resident not found for this facility")
    with db.session() as conn:
        charges = conn.execute(
            "SELECT * FROM billing_charges WHERE resident_id = ? ORDER BY charge_date DESC, id DESC",
            (resident_id,),
        ).fetchall()
        payments = conn.execute(
            "SELECT * FROM billing_payments WHERE resident_id = ? ORDER BY paid_on DESC, id DESC",
            (resident_id,),
        ).fetchall()

    ledger = []
    total_charged = 0
    total_paid = 0
    for c in charges:
        entry = dict(c)
        entry["kind"] = "charge"
        entry["date"] = c["charge_date"]
        ledger.append(entry)
        if not c["voided"]:
            total_charged += c["amount_cents"]
    for p in payments:
        entry = dict(p)
        entry["kind"] = "payment"
        entry["date"] = p["paid_on"]
        ledger.append(entry)
        if not p["voided"]:
            total_paid += p["amount_cents"]

    ledger.sort(key=lambda e: (e["date"], e["id"]), reverse=True)
    totals = {
        "charged_cents": total_charged,
        "paid_cents": total_paid,
        "balance_cents": total_charged - total_paid,
    }
    return ledger, totals


# ---------------- Facility-wide views (dashboard, Med Pass, Task Manager) ----------------

def get_med_pass_for_facility(facility_id, date_str):
    """Today's eMAR rows across every active resident in the facility, oldest time first."""
    residents = list_residents(facility_id)
    for r in residents:
        get_mar_for_date(r["id"], facility_id, date_str)  # ensures 'due' rows exist
    with db.session() as conn:
        rows = conn.execute(
            """SELECT ml.*, m.name AS med_name, m.dose, m.route, r.name AS resident_name, r.room, r.id AS resident_id
               FROM mar_logs ml
               JOIN medications m ON m.id = ml.medication_id
               JOIN residents r ON r.id = m.resident_id
               WHERE r.facility_id = ? AND ml.scheduled_date = ? AND r.active = 1
               ORDER BY ml.scheduled_time, r.name""",
            (facility_id, date_str),
        ).fetchall()
        return rows


def get_tasks_for_facility(facility_id, date_str):
    """Today's task checklist rows across every active resident in the facility."""
    residents = list_residents(facility_id)
    for r in residents:
        get_tasks_for_date(r["id"], facility_id, date_str)  # ensures 'pending' rows exist
    with db.session() as conn:
        rows = conn.execute(
            """SELECT tl.*, t.title, t.shift, r.name AS resident_name, r.room, r.id AS resident_id
               FROM task_logs tl
               JOIN tasks t ON t.id = tl.task_id
               JOIN residents r ON r.id = t.resident_id
               WHERE r.facility_id = ? AND tl.log_date = ? AND r.active = 1
               ORDER BY t.shift, r.name, t.title""",
            (facility_id, date_str),
        ).fetchall()
        return rows


def get_dashboard_stats(facility_id, date_str):
    mar_rows = get_med_pass_for_facility(facility_id, date_str)
    task_rows = get_tasks_for_facility(facility_id, date_str)
    return {
        "resident_count": len(list_residents(facility_id)),
        "meds_due": sum(1 for m in mar_rows if m["status"] == "due"),
        "meds_given": sum(1 for m in mar_rows if m["status"] == "given"),
        "meds_total": len(mar_rows),
        "tasks_due": sum(1 for t in task_rows if t["status"] == "pending"),
        "tasks_done": sum(1 for t in task_rows if t["status"] == "done"),
        "tasks_total": len(task_rows),
    }
