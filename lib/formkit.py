"""Generic helpers for turning admin edit-forms into JSON-shaped data, and back."""


def parse_flat(form, fields):
    result = {}
    for f in fields:
        key = "field-{}".format(f["key"])
        if f.get("type") == "checkbox":
            result[f["key"]] = form.get(key) == "on"
        else:
            result[f["key"]] = form.get(key, "")
    return result


def parse_objectlist(form, prefix, fields):
    items = []
    i = 0
    while True:
        guard = "{}-{}-{}".format(prefix, i, fields[0]["key"])
        if guard not in form:
            break
        item = {}
        for f in fields:
            key = "{}-{}-{}".format(prefix, i, f["key"])
            if f.get("type") == "lines":
                raw = form.get(key, "")
                item[f["key"]] = [line.strip() for line in raw.splitlines() if line.strip()]
            elif f.get("type") == "checkbox":
                item[f["key"]] = form.get(key) == "on"
            else:
                item[f["key"]] = form.get(key, "")
        items.append(item)
        i += 1
    return items


def parse_stringlist(form, prefix):
    items = []
    i = 0
    while True:
        key = "{}-{}".format(prefix, i)
        if key not in form:
            break
        val = form.get(key, "").strip()
        if val != "":
            items.append(val)
        i += 1
    return items


def parse_new_object(form, fields):
    item = {}
    for f in fields:
        key = "new-{}".format(f["key"])
        if f.get("type") == "lines":
            raw = form.get(key, "")
            item[f["key"]] = [line.strip() for line in raw.splitlines() if line.strip()]
        elif f.get("type") == "checkbox":
            item[f["key"]] = form.get(key) == "on"
        else:
            item[f["key"]] = form.get(key, "")
    return item


def blank_object(fields):
    obj = {}
    for f in fields:
        if f.get("type") == "lines":
            obj[f["key"]] = []
        elif f.get("type") == "checkbox":
            obj[f["key"]] = False
        else:
            obj[f["key"]] = ""
    return obj
