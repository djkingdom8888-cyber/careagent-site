# CareAgent

A marketing site (Home / About / Pricing) backed by a small Flask app, plus an
admin panel at `/admin` where every section of the site can be edited without
touching code.

## Running it

```bash
./run.sh
```

This creates a virtualenv on first run, installs Flask, and starts the server
at **http://127.0.0.1:5050**.

(Node.js is broken on this machine — `dyld: Symbol not found ... __libcpp_verbose_abort`
— so the backend is Python/Flask instead of an Express app. If Node gets fixed
later this can be ported, but there's no need to.)

## Admin panel

Go to **http://127.0.0.1:5050/admin/login**.

First-run credentials are auto-generated and written to
`ADMIN_CREDENTIALS.txt` (gitignored, local only). Log in, then change the
password from **Settings** in the sidebar — after that you can delete the
file.

Every section of Home / About / Pricing has its own edit page, grouped in the
sidebar by page. Saving a section updates `data/content.json` immediately and
the public pages reflect it on next load — no restart needed. List-based
sections (products, team, testimonials, FAQ, pricing plans, etc.) support
adding and deleting rows, not just editing existing text.

## How it's put together

- `app.py` — routes: public pages (`/`, `/about`, `/pricing`) and the admin CRUD.
- `data/content.json` — every piece of editable copy on the site. This is the
  database; there's no separate DB engine.
- `lib/sections.py` — a schema describing each editable chunk of that JSON
  (which fields it has, whether it's a single object or a repeatable list).
  Both the edit forms and the save/add/delete routes are generated from this,
  so adding a new editable section is a matter of describing it here rather
  than writing a new route + template.
- `lib/formkit.py` — turns submitted form fields back into the JSON shape.
- `lib/auth.py` — single-admin session login, password hashing, CSRF tokens.
- `templates/` — Jinja templates. Public pages loop over `content.json` data;
  `templates/admin/edit_object.html` and `edit_list.html` are the two generic
  form renderers used by every admin section.
- `static/css/styles.css` — the public site's design system (unchanged from
  the original static build). `static/css/admin.css` is the separate admin
  dashboard theme.

## Notes / limitations

- Single admin account, no roles — fine for one operator, not for a team.
- No image uploads yet — everything editable today is text. The hero/product
  visuals are CSS mockups, not real images.
- Footer navigation links (Product/Company/Resources/Legal columns) are
  static except for the tagline/copyright — only the *labels* shown in
  Product come from the products list.
