"""Form Builder: facility-defined custom forms, filled out per resident (or facility-wide)."""
import json

from . import db


def list_forms(facility_id, include_inactive=False):
    with db.session() as conn:
        if include_inactive:
            q = "SELECT * FROM forms WHERE facility_id = ? ORDER BY name"
        else:
            q = "SELECT * FROM forms WHERE facility_id = ? AND active = 1 ORDER BY name"
        return conn.execute(q, (facility_id,)).fetchall()


def get_form(form_id, facility_id):
    with db.session() as conn:
        return conn.execute(
            "SELECT * FROM forms WHERE id = ? AND facility_id = ?", (form_id, facility_id)
        ).fetchone()


def get_fields(form_id):
    with db.session() as conn:
        return conn.execute(
            "SELECT * FROM form_fields WHERE form_id = ? ORDER BY position, id", (form_id,)
        ).fetchall()


def create_form(facility_id, name, description=""):
    with db.session() as conn:
        cur = conn.execute(
            "INSERT INTO forms (facility_id, name, description) VALUES (?,?,?)",
            (facility_id, name, description),
        )
        return cur.lastrowid


def set_form_active(form_id, facility_id, active):
    form = get_form(form_id, facility_id)
    if not form:
        raise ValueError("Form not found for this facility")
    with db.session() as conn:
        conn.execute("UPDATE forms SET active = ? WHERE id = ?", (1 if active else 0, form_id))


def add_field(form_id, facility_id, label, field_type="text", options="", required=False):
    form = get_form(form_id, facility_id)
    if not form:
        raise ValueError("Form not found for this facility")
    with db.session() as conn:
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) AS m FROM form_fields WHERE form_id = ?", (form_id,)
        ).fetchone()["m"]
        cur = conn.execute(
            "INSERT INTO form_fields (form_id, label, field_type, options, required, position) VALUES (?,?,?,?,?,?)",
            (form_id, label, field_type, options, 1 if required else 0, max_pos + 1),
        )
        return cur.lastrowid


def remove_field(field_id, form_id, facility_id):
    form = get_form(form_id, facility_id)
    if not form:
        raise ValueError("Form not found for this facility")
    with db.session() as conn:
        conn.execute("DELETE FROM form_fields WHERE id = ? AND form_id = ?", (field_id, form_id))


def submit_form(form_id, facility_id, resident_id, user_id, values_by_field_id):
    form = get_form(form_id, facility_id)
    if not form:
        raise ValueError("Form not found for this facility")
    with db.session() as conn:
        cur = conn.execute(
            "INSERT INTO form_submissions (form_id, resident_id, submitted_by_user_id, data_json) VALUES (?,?,?,?)",
            (form_id, resident_id, user_id, json.dumps(values_by_field_id)),
        )
        return cur.lastrowid


def list_submissions(form_id, facility_id):
    form = get_form(form_id, facility_id)
    if not form:
        raise ValueError("Form not found for this facility")
    with db.session() as conn:
        rows = conn.execute(
            """SELECT fs.*, r.name AS resident_name, u.username AS submitted_by_username
               FROM form_submissions fs
               LEFT JOIN residents r ON r.id = fs.resident_id
               LEFT JOIN app_users u ON u.id = fs.submitted_by_user_id
               WHERE fs.form_id = ? ORDER BY fs.submitted_at DESC""",
            (form_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d["data_json"])
            out.append(d)
        return out
