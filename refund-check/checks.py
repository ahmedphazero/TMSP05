"""The middle layer. Each check returns a list of Problems; run_checks() collects them all."""
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import db
from rules import (ALLOWED_EXTENSIONS, CATEGORIES, DOCUMENTS, MAX_AMOUNT, REQUIRED_DOCUMENTS)


@dataclass
class Problem:
    field: str
    message: str


def parse_invoices(raw):
    """Split on commas/newlines, trim, drop empties, keep order, upper-case."""
    parts = re.split(r"[,\n;]+", raw or "")
    return [p.strip().upper() for p in parts if p.strip()]


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def check_taxpayer(data):
    extin = (data.get("extin") or "").strip()
    if not extin:
        return [Problem("extin", "Excise number (EXTIN) is required.")]
    if not re.fullmatch(r"[A-Za-z0-9]{5,20}", extin):
        return [Problem("extin", "Excise number must be 5-20 letters or digits.")]
    return []


def check_category(data):
    if (data.get("category") or "") not in CATEGORIES:
        return [Problem("category", "Choose a valid refund category.")]
    return []


def check_amount(data):
    raw = (data.get("amount") or "").strip()
    if not raw:
        return [Problem("amount", "Claim amount is required.")]
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        return [Problem("amount", "Claim amount must be a number.")]
    if amount <= 0:
        return [Problem("amount", "Claim amount must be greater than zero.")]
    if amount > MAX_AMOUNT:
        return [Problem("amount", f"Claim amount is above the allowed maximum ({MAX_AMOUNT:,}).")]
    if amount != amount.quantize(Decimal("0.001")):
        return [Problem("amount", "Claim amount can have at most 3 decimal places.")]
    return []


def check_period(data):
    start, end = _parse_date(data.get("period_from")), _parse_date(data.get("period_to"))
    problems = []
    if start is None:
        problems.append(Problem("period_from", "Period start must be a valid date."))
    if end is None:
        problems.append(Problem("period_to", "Period end must be a valid date."))
    if problems:
        return problems
    if start > end:
        problems.append(Problem("period_to", "Period end must be on or after the start."))
    if end > date.today():
        problems.append(Problem("period_to", "Period end cannot be in the future."))
    return problems


def check_invoices(data):
    invoices = parse_invoices(data.get("invoices"))
    if not invoices:
        return [Problem("invoices", "Enter at least one invoice reference.")]
    dupes = sorted({i for i in invoices if invoices.count(i) > 1})
    if dupes:
        return [Problem("invoices", f"Invoice listed more than once: {', '.join(dupes)}.")]
    return []


def check_documents(data, files):
    problems = []
    category = data.get("category")
    for key in REQUIRED_DOCUMENTS.get(category, []):
        f = files.get(key)
        if f is None or not getattr(f, "filename", ""):
            problems.append(Problem(key, f"Missing required document: {DOCUMENTS[key]}."))
    for key, label in DOCUMENTS.items():           # validate anything that was uploaded
        f = files.get(key)
        name = getattr(f, "filename", "") if f is not None else ""
        if name:
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext not in ALLOWED_EXTENSIONS:
                problems.append(Problem(key, f"{label}: file type '.{ext}' not allowed "
                                             f"(use {', '.join(sorted(ALLOWED_EXTENSIONS))})."))
    return problems


def check_duplicates(data, db_path):
    extin = (data.get("extin") or "").strip().upper()
    invoices = parse_invoices(data.get("invoices"))
    exact = db.find_exact_duplicate(
        db_path, extin, data.get("period_from"), data.get("period_to"),
        (data.get("amount") or "").strip(), invoices,
    )
    if exact:
        return [Problem("invoices", f"This looks like a duplicate of earlier claim #{exact}.")]
    reused = db.find_reused_invoices(db_path, extin, invoices)
    if reused:
        return [Problem("invoices", f"Invoice already used in an earlier claim: {', '.join(reused)}.")]
    return []


def run_checks(data, files, db_path):
    """Run every check and return all problems (empty list = success)."""
    problems = []
    problems += check_taxpayer(data)
    problems += check_category(data)
    problems += check_amount(data)
    problems += check_period(data)
    problems += check_invoices(data)
    problems += check_documents(data, files)
    # only look up duplicates when the basic fields are sound
    if not problems:
        problems += check_duplicates(data, db_path)
    return problems
