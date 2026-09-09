import datetime
import os
import secrets

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort

from lib import store, auth, formkit, db, app_auth, care, forms, esign, fax
from lib.sections import SECTIONS, SECTION_GROUPS

app = Flask(__name__)


def _get_or_create_secret_key():
    env_key = os.environ.get("CA_SECRET_KEY", "").strip()
    if env_key:
        return env_key
    path = os.path.join(store.DATA_DIR, "secret_key.txt")
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(path, "w") as f:
        f.write(key)
    return key


app.secret_key = _get_or_create_secret_key()
auth.bootstrap_admin()
auth.apply_env_password_reset()
db.init_db()


@app.context_processor
def inject_globals():
    return dict(csrf_token=auth.get_csrf_token, groups=SECTION_GROUPS, sections=SECTIONS)


@app.before_request
def csrf_protect():
    protected = request.method == "POST" and (
        (request.path.startswith("/admin") and request.path != "/admin/login")
        or (request.path.startswith("/app") and request.path != "/app/login")
    )
    if protected:
        token = request.form.get("csrf_token")
        if not auth.verify_csrf(token):
            abort(400, description="Invalid or missing security token. Please refresh the page and try again.")


# ------------------------------------------------------------------
# Public site
# ------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", c=store.load_content())


@app.route("/about")
def about():
    return render_template("about.html", c=store.load_content())


@app.route("/pricing")
def pricing():
    return render_template("pricing.html", c=store.load_content())


# ------------------------------------------------------------------
# Admin auth
# ------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if auth.verify_login(username, password):
            session.clear()
            session["is_admin"] = True
            session["username"] = username
            next_url = request.args.get("next") or url_for("admin_dashboard")
            return redirect(next_url, code=303)
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@auth.login_required
def admin_dashboard():
    return render_template("admin/dashboard.html")


@app.route("/admin/settings", methods=["GET", "POST"])
@auth.login_required
def admin_settings():
    if request.method == "POST":
        action = request.form.get("_action")
        if action == "password":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not auth.verify_login(session.get("username", ""), current):
                flash("Current password is incorrect.", "error")
            elif len(new) < 8:
                flash("New password must be at least 8 characters.", "error")
            elif new != confirm:
                flash("New password and confirmation don't match.", "error")
            else:
                auth.set_password(new)
                flash("Password updated.", "success")
        elif action == "username":
            new_username = request.form.get("username", "").strip()
            if new_username:
                auth.set_username(new_username)
                session["username"] = new_username
                flash("Username updated.", "success")
        return redirect(url_for("admin_settings"), code=303)
    return render_template("admin/settings.html", admin=store.load_admin())


# ------------------------------------------------------------------
# Vendor-side: client facility accounts (who gets to log into /app)
# ------------------------------------------------------------------

@app.route("/admin/facilities", methods=["GET", "POST"])
@auth.login_required
def admin_facilities():
    if request.method == "POST":
        facility_name = request.form.get("facility_name", "").strip()
        owner_username = request.form.get("owner_username", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        owner_password = request.form.get("owner_password", "").strip()
        if not facility_name or not owner_username or not owner_password:
            flash("Facility name, owner username, and owner password are all required.", "error")
        elif len(owner_password) < 8:
            flash("Owner password must be at least 8 characters.", "error")
        elif app_auth.username_exists(owner_username):
            flash("That username is already taken.", "error")
        else:
            facility_id = app_auth.create_facility(facility_name)
            app_auth.create_user(facility_id, owner_username, owner_password, owner_name, role="owner")
            flash(
                "Client account created. Username: {} — share the password you set with your client "
                "and have them change it after their first login.".format(owner_username),
                "success",
            )
        return redirect(url_for("admin_facilities"), code=303)

    with db.session() as conn:
        facilities = conn.execute("SELECT * FROM facilities ORDER BY created_at DESC").fetchall()
        users_by_facility = {}
        for u in conn.execute("SELECT * FROM app_users ORDER BY role DESC, username").fetchall():
            users_by_facility.setdefault(u["facility_id"], []).append(u)
    return render_template("admin/facilities.html", facilities=facilities, users_by_facility=users_by_facility)


@app.route("/admin/facilities/<int:facility_id>/add-user", methods=["POST"])
@auth.login_required
def admin_facility_add_user(facility_id):
    username = request.form.get("username", "").strip()
    full_name = request.form.get("full_name", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "caregiver")
    if role not in ("owner", "caregiver"):
        role = "caregiver"
    if not username or not password:
        flash("Username and password are required.", "error")
    elif len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
    elif app_auth.username_exists(username):
        flash("That username is already taken.", "error")
    else:
        app_auth.create_user(facility_id, username, password, full_name, role=role)
        flash("Staff login created for {}.".format(username), "success")
    return redirect(url_for("admin_facilities"), code=303)


@app.route("/admin/facilities/reset-password/<int:user_id>", methods=["POST"])
@auth.login_required
def admin_facility_reset_password(user_id):
    new_password = request.form.get("new_password", "").strip()
    if len(new_password) < 8:
        flash("New password must be at least 8 characters.", "error")
    else:
        app_auth.set_password(user_id, new_password)
        flash("Password reset.", "success")
    return redirect(url_for("admin_facilities"), code=303)


@app.route("/admin/facilities/<int:facility_id>/open", methods=["POST"])
@auth.login_required
def admin_facility_open(facility_id):
    """Let the vendor admin jump straight into a client's dashboard, no password needed."""
    with db.session() as conn:
        user = conn.execute(
            "SELECT * FROM app_users WHERE facility_id = ? ORDER BY (role = 'owner') DESC, id ASC LIMIT 1",
            (facility_id,),
        ).fetchone()
    if not user:
        flash("This facility has no staff logins yet — add one first.", "error")
        return redirect(url_for("admin_facilities"), code=303)
    session["app_user_id"] = user["id"]
    session["app_facility_id"] = user["facility_id"]
    session["app_role"] = user["role"]
    session["app_full_name"] = user["full_name"] or user["username"]
    return redirect(url_for("app_dashboard"), code=303)


# ------------------------------------------------------------------
# Generic section editor
# ------------------------------------------------------------------

def _get_schema_or_404(slug):
    schema = SECTIONS.get(slug)
    if not schema:
        abort(404)
    return schema


@app.route("/admin/section/<slug>", methods=["GET", "POST"])
@auth.login_required
def admin_section(slug):
    schema = _get_schema_or_404(slug)
    data = store.load_content()
    node = store.get_path(data, schema["path"])

    if request.method == "POST":
        if schema["kind"] == "object":
            flat = formkit.parse_flat(request.form, schema["fields"])
            for k, v in flat.items():
                node[k] = v
            for sub in schema.get("sublists", []):
                prefix = "sub-" + sub["key"]
                if sub["kind"] == "objectlist":
                    node[sub["key"]] = formkit.parse_objectlist(request.form, prefix, sub["fields"])
                else:
                    node[sub["key"]] = formkit.parse_stringlist(request.form, prefix)
        elif schema["kind"] == "objectlist":
            new_list = formkit.parse_objectlist(request.form, "item", schema["fields"])
            store.set_path(data, schema["path"], new_list)
        elif schema["kind"] == "stringlist":
            new_list = formkit.parse_stringlist(request.form, "item")
            store.set_path(data, schema["path"], new_list)

        store.save_content(data)
        flash("Changes saved.", "success")
        return redirect(url_for("admin_section", slug=slug), code=303)

    template = "admin/edit_object.html" if schema["kind"] == "object" else "admin/edit_list.html"
    return render_template(template, slug=slug, schema=schema, node=node)


@app.route("/admin/section/<slug>/add", methods=["POST"])
@auth.login_required
def admin_section_add(slug):
    schema = _get_schema_or_404(slug)
    if schema["kind"] not in ("objectlist", "stringlist"):
        abort(404)
    data = store.load_content()
    lst = store.get_path(data, schema["path"])
    if schema["kind"] == "objectlist":
        lst.append(formkit.parse_new_object(request.form, schema["fields"]))
    else:
        val = request.form.get("new", "").strip()
        if val:
            lst.append(val)
    store.save_content(data)
    flash("Item added.", "success")
    return redirect(url_for("admin_section", slug=slug), code=303)


@app.route("/admin/section/<slug>/delete/<int:idx>", methods=["POST"])
@auth.login_required
def admin_section_delete(slug, idx):
    schema = _get_schema_or_404(slug)
    if schema["kind"] not in ("objectlist", "stringlist"):
        abort(404)
    data = store.load_content()
    if schema["kind"] == "objectlist":
        new_list = formkit.parse_objectlist(request.form, "item", schema["fields"])
    else:
        new_list = formkit.parse_stringlist(request.form, "item")
    if 0 <= idx < len(new_list):
        new_list.pop(idx)
    store.set_path(data, schema["path"], new_list)
    store.save_content(data)
    flash("Item removed.", "success")
    return redirect(url_for("admin_section", slug=slug), code=303)


def _find_sublist(schema, subkey):
    for sub in schema.get("sublists", []):
        if sub["key"] == subkey:
            return sub
    abort(404)


@app.route("/admin/section/<slug>/sublist/<subkey>/add", methods=["POST"])
@auth.login_required
def admin_sublist_add(slug, subkey):
    schema = _get_schema_or_404(slug)
    if schema["kind"] != "object":
        abort(404)
    sub = _find_sublist(schema, subkey)
    data = store.load_content()
    node = store.get_path(data, schema["path"])
    node.setdefault(subkey, [])
    if sub["kind"] == "objectlist":
        node[subkey].append(formkit.parse_new_object(request.form, sub["fields"]))
    else:
        val = request.form.get("new", "").strip()
        if val:
            node[subkey].append(val)
    store.save_content(data)
    flash("Item added.", "success")
    return redirect(url_for("admin_section", slug=slug), code=303)


@app.route("/admin/section/<slug>/sublist/<subkey>/delete/<int:idx>", methods=["POST"])
@auth.login_required
def admin_sublist_delete(slug, subkey, idx):
    schema = _get_schema_or_404(slug)
    if schema["kind"] != "object":
        abort(404)
    _find_sublist(schema, subkey)
    data = store.load_content()
    node = store.get_path(data, schema["path"])

    flat = formkit.parse_flat(request.form, schema["fields"])
    for k, v in flat.items():
        node[k] = v

    for sub in schema.get("sublists", []):
        prefix = "sub-" + sub["key"]
        if sub["kind"] == "objectlist":
            lst = formkit.parse_objectlist(request.form, prefix, sub["fields"])
        else:
            lst = formkit.parse_stringlist(request.form, prefix)
        if sub["key"] == subkey and 0 <= idx < len(lst):
            lst.pop(idx)
        node[sub["key"]] = lst

    store.save_content(data)
    flash("Item removed.", "success")
    return redirect(url_for("admin_section", slug=slug), code=303)


# ------------------------------------------------------------------
# Client-facing care app (/app) — residents, eMAR, tasks
# ------------------------------------------------------------------

@app.route("/app/login", methods=["GET", "POST"])
def app_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = app_auth.verify_app_login(username, password)
        if user:
            session.clear()
            session["app_user_id"] = user["id"]
            session["app_facility_id"] = user["facility_id"]
            session["app_role"] = user["role"]
            session["app_full_name"] = user["full_name"] or user["username"]
            next_url = request.args.get("next") or url_for("app_dashboard")
            return redirect(next_url, code=303)
        flash("Invalid username or password.", "error")
    return render_template("app/login.html")


@app.route("/app/logout")
def app_logout():
    session.clear()
    return redirect(url_for("app_login"))


@app.context_processor
def inject_app_globals():
    return dict(current_facility=app_auth.get_current_facility, current_app_user=app_auth.get_current_user)


@app.route("/app/")
@app_auth.app_login_required
def app_dashboard():
    facility_id = session["app_facility_id"]
    today = care.today_str()
    residents = care.list_residents(facility_id)
    stats = care.get_dashboard_stats(facility_id, today)
    facility = app_auth.get_current_facility()
    facility_age_days = 0
    if facility and facility["created_at"]:
        created = datetime.datetime.strptime(facility["created_at"], "%Y-%m-%d %H:%M:%S")
        facility_age_days = (datetime.datetime.utcnow() - created).days
    with db.session() as conn:
        staff = conn.execute(
            "SELECT * FROM app_users WHERE facility_id = ? ORDER BY role DESC, username", (facility_id,)
        ).fetchall()
    return render_template(
        "app/dashboard.html", residents=residents, stats=stats, today=today,
        facility_age_days=facility_age_days, staff=staff,
    )


@app.route("/app/residents")
@app_auth.app_login_required
def app_residents_list():
    facility_id = session["app_facility_id"]
    residents = care.list_residents(facility_id)
    return render_template("app/residents_list.html", residents=residents)


@app.route("/app/med-pass")
@app_auth.app_login_required
def app_med_pass():
    facility_id = session["app_facility_id"]
    today = care.today_str()
    rows = care.get_med_pass_for_facility(facility_id, today)
    return render_template("app/med_pass.html", rows=rows, today=today)


@app.route("/app/task-manager")
@app_auth.app_login_required
def app_task_manager():
    facility_id = session["app_facility_id"]
    today = care.today_str()
    rows = care.get_tasks_for_facility(facility_id, today)
    return render_template("app/task_manager.html", rows=rows, today=today)


@app.route("/app/reports")
@app_auth.app_login_required
def app_reports():
    facility_id = session["app_facility_id"]
    today = care.today_str()
    stats = care.get_dashboard_stats(facility_id, today)
    return render_template("app/reports.html", stats=stats, today=today)


@app.route("/app/manage-facility", methods=["GET", "POST"])
@app_auth.owner_required
def app_manage_facility():
    facility_id = session["app_facility_id"]
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "caregiver")
        if role not in ("owner", "caregiver"):
            role = "caregiver"
        if not username or not password:
            flash("Username and password are required.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif app_auth.username_exists(username):
            flash("That username is already taken.", "error")
        else:
            app_auth.create_user(facility_id, username, password, full_name, role=role)
            flash("Staff login created for {}.".format(username), "success")
        return redirect(url_for("app_manage_facility"), code=303)
    facility = app_auth.get_current_facility()
    with db.session() as conn:
        staff = conn.execute(
            "SELECT * FROM app_users WHERE facility_id = ? ORDER BY role DESC, username", (facility_id,)
        ).fetchall()
    return render_template("app/manage_facility.html", facility=facility, staff=staff)


@app.route("/app/coming-soon/<label>")
@app_auth.app_login_required
def app_coming_soon(label):
    return render_template("app/coming_soon.html", label=label)


# ------------------------------------------------------------------
# Form Builder
# ------------------------------------------------------------------

@app.route("/app/forms")
@app_auth.app_login_required
def app_forms():
    facility_id = session["app_facility_id"]
    form_list = forms.list_forms(facility_id, include_inactive=(session.get("app_role") == "owner"))
    return render_template("app/forms.html", form_list=form_list)


@app.route("/app/forms/new", methods=["GET", "POST"])
@app_auth.owner_required
def app_form_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Form name is required.", "error")
        else:
            form_id = forms.create_form(session["app_facility_id"], name, request.form.get("description", "").strip())
            flash("Form created — now add fields to it.", "success")
            return redirect(url_for("app_form_detail", form_id=form_id), code=303)
    return render_template("app/form_new.html")


@app.route("/app/forms/<int:form_id>")
@app_auth.app_login_required
def app_form_detail(form_id):
    facility_id = session["app_facility_id"]
    form = forms.get_form(form_id, facility_id)
    if not form:
        abort(404)
    fields = forms.get_fields(form_id)
    submissions = forms.list_submissions(form_id, facility_id) if session.get("app_role") == "owner" else []
    residents = care.list_residents(facility_id)
    return render_template(
        "app/form_detail.html", form=form, fields=fields, submissions=submissions, residents=residents,
    )


@app.route("/app/forms/<int:form_id>/fields/add", methods=["POST"])
@app_auth.owner_required
def app_form_field_add(form_id):
    facility_id = session["app_facility_id"]
    label = request.form.get("label", "").strip()
    if not label:
        flash("Field label is required.", "error")
    else:
        try:
            forms.add_field(
                form_id, facility_id, label,
                field_type=request.form.get("field_type", "text"),
                options=request.form.get("options", "").strip(),
                required=request.form.get("required") == "on",
            )
            flash("Field added.", "success")
        except ValueError:
            abort(404)
    return redirect(url_for("app_form_detail", form_id=form_id), code=303)


@app.route("/app/forms/<int:form_id>/fields/<int:field_id>/delete", methods=["POST"])
@app_auth.owner_required
def app_form_field_delete(form_id, field_id):
    try:
        forms.remove_field(field_id, form_id, session["app_facility_id"])
    except ValueError:
        abort(404)
    flash("Field removed.", "success")
    return redirect(url_for("app_form_detail", form_id=form_id), code=303)


@app.route("/app/forms/<int:form_id>/deactivate", methods=["POST"])
@app_auth.owner_required
def app_form_deactivate(form_id):
    try:
        forms.set_form_active(form_id, session["app_facility_id"], False)
    except ValueError:
        abort(404)
    flash("Form deactivated.", "success")
    return redirect(url_for("app_forms"), code=303)


@app.route("/app/forms/<int:form_id>/fill", methods=["GET", "POST"])
@app_auth.app_login_required
def app_form_fill(form_id):
    facility_id = session["app_facility_id"]
    form = forms.get_form(form_id, facility_id)
    if not form:
        abort(404)
    fields = forms.get_fields(form_id)
    if request.method == "POST":
        resident_id = request.form.get("resident_id") or None
        values = {}
        for f in fields:
            key = "field-{}".format(f["id"])
            values[str(f["id"])] = request.form.get(key) == "on" if f["field_type"] == "checkbox" else request.form.get(key, "")
        forms.submit_form(form_id, facility_id, resident_id, session["app_user_id"], values)
        flash("Form submitted.", "success")
        return redirect(url_for("app_form_detail", form_id=form_id), code=303)
    residents = care.list_residents(facility_id)
    return render_template("app/form_fill.html", form=form, fields=fields, residents=residents)


# ------------------------------------------------------------------
# Digital Signature
# ------------------------------------------------------------------

@app.route("/app/signatures")
@app_auth.app_login_required
def app_signatures():
    facility_id = session["app_facility_id"]
    documents = esign.list_documents(facility_id)
    return render_template("app/signatures.html", documents=documents)


@app.route("/app/signatures/new", methods=["GET", "POST"])
@app_auth.owner_required
def app_signature_new():
    facility_id = session["app_facility_id"]
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Document title is required.", "error")
        else:
            doc_id = esign.create_document(
                facility_id, title, request.form.get("body", "").strip(),
                request.form.get("resident_id") or None, session["app_user_id"],
            )
            flash("Document created — ready to collect signatures.", "success")
            return redirect(url_for("app_signature_detail", document_id=doc_id), code=303)
    residents = care.list_residents(facility_id)
    return render_template("app/signature_new.html", residents=residents)


@app.route("/app/signatures/<int:document_id>", methods=["GET", "POST"])
@app_auth.app_login_required
def app_signature_detail(document_id):
    facility_id = session["app_facility_id"]
    document = esign.get_document(document_id, facility_id)
    if not document:
        abort(404)
    if request.method == "POST":
        signer_name = request.form.get("signer_name", "").strip()
        signer_role = request.form.get("signer_role", "").strip()
        signature_data = request.form.get("signature_data", "")
        if not signer_name or not signature_data:
            flash("A signer name and an actual drawn signature are required.", "error")
        else:
            try:
                esign.add_signature(document_id, facility_id, signer_name, signer_role, signature_data, session["app_user_id"])
                flash("Signature captured.", "success")
            except ValueError:
                flash("Couldn't save that signature — try signing again.", "error")
        return redirect(url_for("app_signature_detail", document_id=document_id), code=303)
    signatures = esign.list_signatures(document_id, facility_id)
    return render_template("app/signature_detail.html", document=document, signatures=signatures)


# ------------------------------------------------------------------
# Fax (queue only — see lib/fax.py docstring for why it doesn't send)
# ------------------------------------------------------------------

@app.route("/app/fax", methods=["GET", "POST"])
@app_auth.app_login_required
def app_fax():
    facility_id = session["app_facility_id"]
    if request.method == "POST":
        to_number = request.form.get("to_number", "").strip()
        if not to_number:
            flash("A fax number is required.", "error")
        else:
            fax.create_fax(
                facility_id, request.form.get("resident_id") or None, to_number,
                request.form.get("to_name", "").strip(), request.form.get("subject", "").strip(),
                request.form.get("note", "").strip(), session["app_user_id"],
            )
            flash("Fax queued. Reminder: no fax provider is connected, so this is saved but not actually transmitted.", "success")
        return redirect(url_for("app_fax"), code=303)
    residents = care.list_residents(facility_id)
    fax_list = fax.list_faxes(facility_id)
    return render_template("app/fax.html", fax_list=fax_list, residents=residents)


@app.route("/app/residents/new", methods=["GET", "POST"])
@app_auth.owner_required
def app_resident_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Resident name is required.", "error")
        else:
            resident_id = care.create_resident(
                session["app_facility_id"],
                name=name,
                room=request.form.get("room", "").strip(),
                date_of_birth=request.form.get("date_of_birth", "").strip(),
                allergies=request.form.get("allergies", "").strip(),
                diagnoses=request.form.get("diagnoses", "").strip(),
                emergency_contact=request.form.get("emergency_contact", "").strip(),
                notes=request.form.get("notes", "").strip(),
            )
            flash("Resident added.", "success")
            return redirect(url_for("app_resident_detail", resident_id=resident_id), code=303)
    return render_template("app/resident_form.html", resident=None)


@app.route("/app/residents/<int:resident_id>")
@app_auth.app_login_required
def app_resident_detail(resident_id):
    facility_id = session["app_facility_id"]
    resident = care.get_resident(resident_id, facility_id)
    if not resident:
        abort(404)
    today = care.today_str()
    mar_rows = care.get_mar_for_date(resident_id, facility_id, today)
    task_rows = care.get_tasks_for_date(resident_id, facility_id, today)
    return render_template(
        "app/resident_detail.html", resident=resident, mar_rows=mar_rows, task_rows=task_rows, today=today,
    )


@app.route("/app/residents/<int:resident_id>/edit", methods=["GET", "POST"])
@app_auth.owner_required
def app_resident_edit(resident_id):
    facility_id = session["app_facility_id"]
    resident = care.get_resident(resident_id, facility_id)
    if not resident:
        abort(404)
    if request.method == "POST":
        care.update_resident(
            resident_id, facility_id,
            name=request.form.get("name", "").strip() or resident["name"],
            room=request.form.get("room", "").strip(),
            date_of_birth=request.form.get("date_of_birth", "").strip(),
            allergies=request.form.get("allergies", "").strip(),
            diagnoses=request.form.get("diagnoses", "").strip(),
            emergency_contact=request.form.get("emergency_contact", "").strip(),
            notes=request.form.get("notes", "").strip(),
        )
        flash("Resident updated.", "success")
        return redirect(url_for("app_resident_detail", resident_id=resident_id), code=303)
    return render_template("app/resident_form.html", resident=resident)


@app.route("/app/residents/<int:resident_id>/archive", methods=["POST"])
@app_auth.owner_required
def app_resident_archive(resident_id):
    facility_id = session["app_facility_id"]
    resident = care.get_resident(resident_id, facility_id)
    if not resident:
        abort(404)
    care.set_resident_active(resident_id, facility_id, False)
    flash("Resident archived.", "success")
    return redirect(url_for("app_residents_list"), code=303)


@app.route("/app/residents/<int:resident_id>/mar/<int:mar_log_id>/mark", methods=["POST"])
@app_auth.app_login_required
def app_mar_mark(resident_id, mar_log_id):
    facility_id = session["app_facility_id"]
    status = request.form.get("status", "given")
    if status not in ("given", "missed", "refused", "held", "due"):
        abort(400)
    try:
        care.mark_mar(mar_log_id, facility_id, status, session["app_user_id"], request.form.get("note", ""))
    except ValueError:
        abort(404)
    if request.form.get("next") == "med-pass":
        return redirect(url_for("app_med_pass"), code=303)
    return redirect(url_for("app_resident_detail", resident_id=resident_id), code=303)


@app.route("/app/residents/<int:resident_id>/tasks/<int:task_log_id>/mark", methods=["POST"])
@app_auth.app_login_required
def app_task_mark(resident_id, task_log_id):
    facility_id = session["app_facility_id"]
    status = request.form.get("status", "done")
    if status not in ("done", "missed", "pending"):
        abort(400)
    try:
        care.mark_task(task_log_id, facility_id, status, session["app_user_id"], request.form.get("note", ""))
    except ValueError:
        abort(404)
    if request.form.get("next") == "task-manager":
        return redirect(url_for("app_task_manager"), code=303)
    return redirect(url_for("app_resident_detail", resident_id=resident_id), code=303)


@app.route("/app/residents/<int:resident_id>/medications", methods=["GET", "POST"])
@app_auth.owner_required
def app_medications(resident_id):
    facility_id = session["app_facility_id"]
    resident = care.get_resident(resident_id, facility_id)
    if not resident:
        abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Medication name is required.", "error")
        else:
            care.create_medication(
                resident_id, facility_id, name,
                dose=request.form.get("dose", "").strip(),
                route=request.form.get("route", "").strip(),
                instructions=request.form.get("instructions", "").strip(),
                times=request.form.get("times", "").strip(),
            )
            flash("Medication added.", "success")
        return redirect(url_for("app_medications", resident_id=resident_id), code=303)
    meds = care.list_medications(resident_id, facility_id, include_inactive=True)
    return render_template("app/medications.html", resident=resident, meds=meds)


@app.route("/app/residents/<int:resident_id>/medications/<int:med_id>/deactivate", methods=["POST"])
@app_auth.owner_required
def app_medication_deactivate(resident_id, med_id):
    facility_id = session["app_facility_id"]
    try:
        care.set_medication_active(med_id, facility_id, False)
    except ValueError:
        abort(404)
    flash("Medication deactivated.", "success")
    return redirect(url_for("app_medications", resident_id=resident_id), code=303)


@app.route("/app/residents/<int:resident_id>/tasks/manage", methods=["GET", "POST"])
@app_auth.owner_required
def app_tasks_manage(resident_id):
    facility_id = session["app_facility_id"]
    resident = care.get_resident(resident_id, facility_id)
    if not resident:
        abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Task title is required.", "error")
        else:
            care.create_task(resident_id, facility_id, title, shift=request.form.get("shift", "any"))
            flash("Task added.", "success")
        return redirect(url_for("app_tasks_manage", resident_id=resident_id), code=303)
    tasks = care.list_tasks(resident_id, facility_id, include_inactive=True)
    return render_template("app/tasks_manage.html", resident=resident, tasks=tasks)


@app.route("/app/residents/<int:resident_id>/tasks/<int:task_id>/deactivate", methods=["POST"])
@app_auth.owner_required
def app_task_deactivate(resident_id, task_id):
    facility_id = session["app_facility_id"]
    try:
        care.set_task_active(task_id, facility_id, False)
    except ValueError:
        abort(404)
    flash("Task deactivated.", "success")
    return redirect(url_for("app_tasks_manage", resident_id=resident_id), code=303)


@app.route("/app/residents/<int:resident_id>/billing")
@app_auth.owner_required
def app_billing(resident_id):
    facility_id = session["app_facility_id"]
    resident = care.get_resident(resident_id, facility_id)
    if not resident:
        abort(404)
    ledger, totals = care.get_billing_ledger(resident_id, facility_id)
    return render_template("app/billing.html", resident=resident, ledger=ledger, totals=totals, today=care.today_str())


@app.route("/app/residents/<int:resident_id>/billing/charge", methods=["POST"])
@app_auth.owner_required
def app_billing_add_charge(resident_id):
    facility_id = session["app_facility_id"]
    resident = care.get_resident(resident_id, facility_id)
    if not resident:
        abort(404)
    description = request.form.get("description", "").strip()
    try:
        amount_cents = care.dollars_to_cents(request.form.get("amount", ""))
    except ValueError:
        amount_cents = None
    if not description or not amount_cents or amount_cents <= 0:
        flash("Enter a description and a valid amount.", "error")
    else:
        care.create_charge(
            resident_id, facility_id, description, amount_cents,
            category=request.form.get("category", "rent"),
            charge_date=request.form.get("charge_date") or None,
            user_id=session["app_user_id"],
        )
        flash("Charge added.", "success")
    return redirect(url_for("app_billing", resident_id=resident_id), code=303)


@app.route("/app/residents/<int:resident_id>/billing/charge/<int:charge_id>/void", methods=["POST"])
@app_auth.owner_required
def app_billing_void_charge(resident_id, charge_id):
    facility_id = session["app_facility_id"]
    try:
        care.void_charge(charge_id, facility_id)
    except ValueError:
        abort(404)
    flash("Charge voided.", "success")
    return redirect(url_for("app_billing", resident_id=resident_id), code=303)


@app.route("/app/residents/<int:resident_id>/billing/payment", methods=["POST"])
@app_auth.owner_required
def app_billing_add_payment(resident_id):
    facility_id = session["app_facility_id"]
    resident = care.get_resident(resident_id, facility_id)
    if not resident:
        abort(404)
    try:
        amount_cents = care.dollars_to_cents(request.form.get("amount", ""))
    except ValueError:
        amount_cents = None
    if not amount_cents or amount_cents <= 0:
        flash("Enter a valid payment amount.", "error")
    else:
        care.create_payment(
            resident_id, facility_id, amount_cents,
            method=request.form.get("method", "check"),
            payer=request.form.get("payer", "").strip(),
            note=request.form.get("note", "").strip(),
            paid_on=request.form.get("paid_on") or None,
            user_id=session["app_user_id"],
        )
        flash("Payment recorded.", "success")
    return redirect(url_for("app_billing", resident_id=resident_id), code=303)


@app.route("/app/residents/<int:resident_id>/billing/payment/<int:payment_id>/void", methods=["POST"])
@app_auth.owner_required
def app_billing_void_payment(resident_id, payment_id):
    facility_id = session["app_facility_id"]
    try:
        care.void_payment(payment_id, facility_id)
    except ValueError:
        abort(404)
    flash("Payment voided.", "success")
    return redirect(url_for("app_billing", resident_id=resident_id), code=303)


if __name__ == "__main__":
    app.run(debug=True, port=5050, host="0.0.0.0")
