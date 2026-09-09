"""Registry describing every editable chunk of content.json for the admin CRUD engine.

Each section is one of:
  - "object":      a single object with flat text fields, optionally with named
                    sublists nested inside it (e.g. hero has a `stats` sublist).
  - "objectlist":  a top-level array of objects, each with the same fields
                    (e.g. products, team members, FAQ items).
  - "stringlist":  a top-level array of plain strings (e.g. trust-logo names).
"""

SECTION_GROUPS = [
    {
        "key": "home",
        "label": "Home Page",
        "sections": [
            "home-hero", "home-logos", "home-value-props", "home-products",
            "home-ai-banner", "home-compliance", "home-testimonials", "home-cta",
        ],
    },
    {
        "key": "about",
        "label": "About Page",
        "sections": [
            "about-hero", "about-story", "about-mission", "about-values",
            "about-timeline", "about-team", "about-cta",
        ],
    },
    {
        "key": "pricing",
        "label": "Pricing Page",
        "sections": [
            "pricing-hero", "pricing-plans", "pricing-addons", "pricing-faq", "pricing-cta",
        ],
    },
    {
        "key": "global",
        "label": "Site-wide",
        "sections": ["site-settings", "footer"],
    },
]

SECTIONS = {
    "site-settings": {
        "title": "Site Settings",
        "path": ["site"],
        "kind": "object",
        "fields": [
            {"key": "name", "label": "Site name"},
            {"key": "mark", "label": "Logo mark (short text, e.g. initials)"},
            {"key": "tagline", "label": "Tagline", "type": "textarea"},
        ],
    },
    "footer": {
        "title": "Footer",
        "path": ["footer"],
        "kind": "object",
        "fields": [
            {"key": "tagline", "label": "Footer blurb", "type": "textarea"},
            {"key": "copyright", "label": "Copyright line"},
        ],
    },

    # ---------------- Home page ----------------
    "home-hero": {
        "title": "Home · Hero",
        "path": ["home", "hero"],
        "kind": "object",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow badge text"},
            {"key": "heading", "label": "Heading (plain part)"},
            {"key": "heading_accent", "label": "Heading (colored accent part)"},
            {"key": "lead", "label": "Lead paragraph", "type": "textarea"},
            {"key": "cta_primary", "label": "Primary button label"},
            {"key": "cta_secondary", "label": "Secondary button label"},
        ],
        "sublists": [
            {
                "key": "stats", "label": "Hero stats", "kind": "objectlist",
                "fields": [{"key": "value", "label": "Value"}, {"key": "label", "label": "Label"}],
            },
        ],
    },
    "home-logos": {
        "title": "Home · Trust Logos",
        "path": ["home", "logos"],
        "kind": "stringlist",
        "item_label": "Community / customer name",
    },
    "home-value-props": {
        "title": "Home · Why CareAgent",
        "path": ["home", "value_props"],
        "kind": "objectlist",
        "fields": [
            {"key": "icon", "label": "Icon"},
            {"key": "title", "label": "Title"},
            {"key": "text", "label": "Description", "type": "textarea"},
        ],
    },
    "home-products": {
        "title": "Home · Product Modules",
        "path": ["home", "products"],
        "kind": "objectlist",
        "fields": [
            {"key": "icon", "label": "Icon"},
            {"key": "title", "label": "Title"},
            {"key": "text", "label": "Description", "type": "textarea"},
        ],
    },
    "home-ai-banner": {
        "title": "Home · CareAgent AI Banner",
        "path": ["home", "ai_banner"],
        "kind": "object",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow badge text"},
            {"key": "heading", "label": "Heading", "type": "textarea"},
            {"key": "text", "label": "Body text", "type": "textarea"},
            {"key": "cta", "label": "Button label"},
        ],
        "sublists": [
            {"key": "points", "label": "Bullet points", "kind": "stringlist", "item_label": "Point"},
            {
                "key": "chat", "label": "Chat demo lines", "kind": "objectlist",
                "fields": [
                    {"key": "from", "label": "Speaker (\"bot\" or \"me\")"},
                    {"key": "text", "label": "Message", "type": "textarea"},
                ],
            },
        ],
    },
    "home-compliance": {
        "title": "Home · Compliance & Trust",
        "path": ["home", "compliance"],
        "kind": "object",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow badge text"},
            {"key": "heading", "label": "Heading", "type": "textarea"},
        ],
        "sublists": [
            {"key": "checklist", "label": "Checklist bullets", "kind": "stringlist", "item_label": "Bullet"},
            {
                "key": "stats", "label": "Stat boxes", "kind": "objectlist",
                "fields": [{"key": "value", "label": "Value"}, {"key": "label", "label": "Label"}],
            },
            {
                "key": "audit_rows", "label": "Live audit trail rows", "kind": "objectlist",
                "fields": [{"key": "label", "label": "Row label"}, {"key": "status", "label": "Status"}],
            },
        ],
    },
    "home-testimonials": {
        "title": "Home · Testimonials",
        "path": ["home", "testimonials"],
        "kind": "object",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow badge text"},
            {"key": "heading", "label": "Heading"},
        ],
        "sublists": [
            {
                "key": "quotes", "label": "Testimonials", "kind": "objectlist",
                "fields": [
                    {"key": "quote", "label": "Quote", "type": "textarea"},
                    {"key": "name", "label": "Person name"},
                    {"key": "role", "label": "Role / community"},
                ],
            },
            {
                "key": "ratings", "label": "Rating strip", "kind": "objectlist",
                "fields": [{"key": "value", "label": "Value"}, {"key": "label", "label": "Label"}],
            },
        ],
    },
    "home-cta": {
        "title": "Home · Bottom CTA Banner",
        "path": ["home", "cta"],
        "kind": "object",
        "fields": [
            {"key": "heading", "label": "Heading"},
            {"key": "text", "label": "Subtext", "type": "textarea"},
        ],
    },

    # ---------------- About page ----------------
    "about-hero": {
        "title": "About · Page Header",
        "path": ["about", "hero"],
        "kind": "object",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow badge text"},
            {"key": "heading", "label": "Heading"},
            {"key": "text", "label": "Subtext", "type": "textarea"},
        ],
    },
    "about-story": {
        "title": "About · Our Story",
        "path": ["about", "story"],
        "kind": "object",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow badge text"},
            {"key": "heading", "label": "Heading", "type": "textarea"},
        ],
        "sublists": [
            {"key": "paragraphs", "label": "Story paragraphs", "kind": "stringlist", "item_label": "Paragraph", "textarea": True},
            {
                "key": "stats", "label": "Story stats", "kind": "objectlist",
                "fields": [{"key": "value", "label": "Value"}, {"key": "label", "label": "Label"}],
            },
        ],
    },
    "about-mission": {
        "title": "About · Mission",
        "path": ["about", "mission"],
        "kind": "object",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow badge text"},
            {"key": "heading", "label": "Heading"},
            {"key": "text", "label": "Subtext", "type": "textarea"},
        ],
    },
    "about-values": {
        "title": "About · Values",
        "path": ["about", "core_values"],
        "kind": "objectlist",
        "fields": [
            {"key": "icon", "label": "Icon"},
            {"key": "title", "label": "Title"},
            {"key": "text", "label": "Description", "type": "textarea"},
        ],
    },
    "about-timeline": {
        "title": "About · Timeline / Milestones",
        "path": ["about", "timeline"],
        "kind": "objectlist",
        "fields": [
            {"key": "year", "label": "Year"},
            {"key": "title", "label": "Title"},
            {"key": "text", "label": "Description", "type": "textarea"},
        ],
    },
    "about-team": {
        "title": "About · Team",
        "path": ["about", "team"],
        "kind": "objectlist",
        "fields": [
            {"key": "initials", "label": "Initials"},
            {"key": "name", "label": "Full name"},
            {"key": "role", "label": "Role / title"},
        ],
    },
    "about-cta": {
        "title": "About · Bottom CTA Banner",
        "path": ["about", "cta"],
        "kind": "object",
        "fields": [
            {"key": "heading", "label": "Heading"},
            {"key": "text", "label": "Subtext", "type": "textarea"},
        ],
    },

    # ---------------- Pricing page ----------------
    "pricing-hero": {
        "title": "Pricing · Page Header",
        "path": ["pricing", "hero"],
        "kind": "object",
        "fields": [
            {"key": "eyebrow", "label": "Eyebrow badge text"},
            {"key": "heading", "label": "Heading"},
            {"key": "text", "label": "Subtext", "type": "textarea"},
        ],
    },
    "pricing-plans": {
        "title": "Pricing · Plans",
        "path": ["pricing", "plans"],
        "kind": "objectlist",
        "fields": [
            {"key": "name", "label": "Plan name"},
            {"key": "desc", "label": "Short description", "type": "textarea"},
            {"key": "featured", "label": "Highlight as “Most Popular”", "type": "checkbox"},
            {"key": "badge", "label": "Badge text (shown if highlighted)"},
            {"key": "price_monthly", "label": "Monthly price (e.g. $11 or Custom)"},
            {"key": "price_annual", "label": "Annual price (e.g. $9 or Custom)"},
            {"key": "price_suffix", "label": "Price suffix (e.g. / resident / mo)"},
            {"key": "cta_label", "label": "Button label"},
            {"key": "features", "label": "Features (one per line)", "type": "lines"},
        ],
    },
    "pricing-addons": {
        "title": "Pricing · Add-ons",
        "path": ["pricing", "addons"],
        "kind": "objectlist",
        "fields": [
            {"key": "name", "label": "Add-on name"},
            {"key": "text", "label": "Description", "type": "textarea"},
            {"key": "price", "label": "Price label"},
        ],
    },
    "pricing-faq": {
        "title": "Pricing · FAQ",
        "path": ["pricing", "faq"],
        "kind": "objectlist",
        "fields": [
            {"key": "q", "label": "Question"},
            {"key": "a", "label": "Answer", "type": "textarea"},
        ],
    },
    "pricing-cta": {
        "title": "Pricing · Bottom CTA Banner",
        "path": ["pricing", "cta"],
        "kind": "object",
        "fields": [
            {"key": "heading", "label": "Heading"},
            {"key": "text", "label": "Subtext", "type": "textarea"},
        ],
    },
}
