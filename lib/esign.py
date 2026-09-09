"""Digital Signature: create a document, capture a drawn signature against it."""
from . import db


def list_documents(facility_id):
    with db.session() as conn:
        return conn.execute(
            """SELECT sd.*, r.name AS resident_name,
                      (SELECT COUNT(*) FROM signatures s WHERE s.document_id = sd.id) AS signature_count
               FROM signature_documents sd
               LEFT JOIN residents r ON r.id = sd.resident_id
               WHERE sd.facility_id = ? ORDER BY sd.created_at DESC""",
            (facility_id,),
        ).fetchall()


def get_document(document_id, facility_id):
    with db.session() as conn:
        return conn.execute(
            "SELECT * FROM signature_documents WHERE id = ? AND facility_id = ?",
            (document_id, facility_id),
        ).fetchone()


def create_document(facility_id, title, body, resident_id, user_id):
    with db.session() as conn:
        cur = conn.execute(
            """INSERT INTO signature_documents (facility_id, resident_id, title, body, created_by_user_id)
               VALUES (?,?,?,?,?)""",
            (facility_id, resident_id, title, body, user_id),
        )
        return cur.lastrowid


def list_signatures(document_id, facility_id):
    doc = get_document(document_id, facility_id)
    if not doc:
        raise ValueError("Document not found for this facility")
    with db.session() as conn:
        return conn.execute(
            "SELECT * FROM signatures WHERE document_id = ? ORDER BY signed_at DESC", (document_id,)
        ).fetchall()


def add_signature(document_id, facility_id, signer_name, signer_role, signature_data, user_id):
    doc = get_document(document_id, facility_id)
    if not doc:
        raise ValueError("Document not found for this facility")
    if not signature_data or not signature_data.startswith("data:image/png;base64,"):
        raise ValueError("Invalid signature data")
    with db.session() as conn:
        cur = conn.execute(
            """INSERT INTO signatures (document_id, signer_name, signer_role, signature_data, signed_by_user_id)
               VALUES (?,?,?,?,?)""",
            (document_id, signer_name, signer_role, signature_data, user_id),
        )
        return cur.lastrowid
