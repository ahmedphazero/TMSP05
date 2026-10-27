"""Business rules in one place. DRAFT values: confirm with the Authority before real use."""

CATEGORIES = {
    "export":    "Excise goods exported",
    "destroyed": "Excise goods destroyed",
    "returned":  "Excise goods returned to warehouse",
}

DOCUMENTS = {
    "customs_declaration": "Customs declaration",
    "commercial_invoice":  "Commercial invoice",
    "payment_receipt":     "Excise payment receipt",
    "destruction_cert":    "Destruction certificate",
}

# Which documents each refund category must include.
REQUIRED_DOCUMENTS = {
    "export":    ["customs_declaration", "commercial_invoice", "payment_receipt"],
    "destroyed": ["destruction_cert", "payment_receipt"],
    "returned":  ["commercial_invoice", "payment_receipt"],
}

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_AMOUNT = 10_000_000          # sanity cap
