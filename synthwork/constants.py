"""Shared names and the synthetic-data notice shown throughout the project."""

NOTICE = (
    "SYNTHETICWORKPLACE: all data is fictional and generated locally. "
    "No real companies, people, or emails exist in these files. "
    "Names are invented; any resemblance to real entities is coincidental."
)

HONESTY_HELP = (
    "HONESTY BOUNDARY: all generated data is synthetic and fictional. "
    "No real companies, people, or emails exist in the data. Names are invented; "
    "any resemblance to real entities is coincidental. Never treat this output "
    "as real company data or anonymised real data."
)

COLLECTION_FILES = {
    "company": "company.json",
    "employees": "employees.json",
    "emails": "emails.json",
    "accounts": "accounts.json",
    "contacts": "contacts.json",
    "invoices": "invoices.json",
    "tickets": "tickets.json",
    "documents": "documents.json",
}

QUERY_TYPES = tuple(COLLECTION_FILES) + ("spreadsheets", "all")

PROFILES = {
    "fixture": {
        "employees": 6,
        "accounts": 5,
        "contacts": 10,
        "email_threads": 8,
        "invoices": 6,
        "tickets": 4,
        "documents": 3,
    },
    "demo": {
        "employees": 12,
        "accounts": 10,
        "contacts": 22,
        "email_threads": 24,
        "invoices": 16,
        "tickets": 10,
        "documents": 5,
    },
    "scale": {
        "employees": 80,
        "accounts": 70,
        "contacts": 220,
        "email_threads": 400,
        "invoices": 250,
        "tickets": 140,
        "documents": 30,
    },
}

COMPANY_WORDS = (
    "Amber", "Brindle", "Cobalt", "Dapple", "Elm", "Fable", "Garnet",
    "Harbor", "Ivory", "Juniper", "Kestrel", "Linden", "Morrow", "Nimble",
    "Olive", "Pebble", "Quartz", "River", "Saffron", "Thistle", "Umber",
    "Velvet", "Willow", "Yonder", "Zephyr",
)

COMPANY_NOUNS = (
    "Arc", "Beacon", "Cairn", "Delta", "Ember", "Field", "Grove", "Haven",
    "Inlet", "Junction", "Keystone", "Lantern", "Meadow", "Northstar", "Orchard",
    "Pioneer", "Quarry", "Ridgeline", "Summit", "Tandem", "Union", "Vale",
    "Waypoint", "Yard", "Zenith",
)

INDUSTRIES = (
    "office supplies", "field services", "specialty foods", "learning materials",
    "workshop equipment", "garden goods", "design services", "freight planning",
)

FIRST_NAMES = (
    "Ari", "Bryn", "Cleo", "Dev", "Eli", "Fern", "Gray", "Hollis", "Indra",
    "Jules", "Kit", "Lior", "Mica", "Noor", "Orin", "Perry", "Quinn", "Remy",
    "Sage", "Tavi", "Uma", "Vale", "Wren", "Yael", "Zuri",
)

LAST_NAMES = (
    "Alder", "Bexley", "Calder", "Dorian", "Ellery", "Fenn", "Grove", "Hale",
    "Ives", "Jory", "Kellan", "Linden", "Marlowe", "Neri", "Oakes", "Pryor",
    "Quill", "Rowan", "Sayer", "Tolland", "Upton", "Voss", "Wilder", "Yarrow",
)

DEPARTMENTS = (
    "Operations", "Customer Care", "Finance", "Sales", "People", "Research",
)

ROLES = (
    "Coordinator", "Analyst", "Specialist", "Manager", "Associate", "Lead",
)

PRODUCTS = (
    "assembly kit", "archive box", "cable set", "desk lamp", "field notebook",
    "label roll", "measuring tool", "packing sleeve", "sample binder", "safety vest",
    "storage tray", "work mat",
)

PROJECTS = (
    "Autumn replenishment", "Beacon rollout", "Cedar refresh", "Dispatch review",
    "Equipment survey", "Field guide update", "Greenhouse setup", "Harbor transition",
    "Inventory reset", "Juniper renewal", "Knowledge base review", "Lantern launch",
)

COLLECTION_ORDER = (
    "company", "employees", "emails", "accounts", "contacts", "invoices",
    "spreadsheets", "tickets", "documents",
)
