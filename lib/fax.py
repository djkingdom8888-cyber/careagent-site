"""Fax queue. NOTE: this stores fax requests only — it does not transmit them.

Actually sending a fax requires a real telephony/fax API provider (e.g. Twilio,
sfax, SRFax) with its own paid account and API keys, which this project doesn't
have connected. Every fax created here stays at status='queued' and says so in
the UI, rather than pretending it was delivered.
"""
from . import db


def list_faxes(facility_id):
    with db.session() as conn:
        return conn.execute(
            """SELECT f.*, r.name AS resident_name FROM faxes f
               LEFT JOIN residents r ON r.id = f.resident_id
               WHERE f.facility_id = ? ORDER BY f.created_at DESC""",
            (facility_id,),
        ).fetchall()


def create_fax(facility_id, resident_id, to_number, to_name, subject, note, user_id):
    with db.session() as conn:
        cur = conn.execute(
            """INSERT INTO faxes (facility_id, resident_id, to_number, to_name, subject, note, created_by_user_id)
               VALUES (?,?,?,?,?,?,?)""",
            (facility_id, resident_id, to_number, to_name, subject, note, user_id),
        )
        return cur.lastrowid
