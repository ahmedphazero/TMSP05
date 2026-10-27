# Excise Refund Check (Flask)

Form -> checks layer -> success, or a list of everything that is wrong.

## Run
    python -m venv .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python app.py                      # http://127.0.0.1:5000

## Test
    pytest

## Files
- app.py        web routes (form page, result)
- checks.py     the checks layer: one function per check, run_checks() runs them all
- rules.py      categories, required documents per category, allowed file types (DRAFT, edit here)
- db.py         SQLite store used for duplicate detection (refunds.db is created on first run)
- templates/    form.html, success.html, base.html
- static/       style.css

## Add a new check
1. Write `def check_something(data, ...) -> list[Problem]` in checks.py.
2. Call it inside run_checks().
3. Add a test in tests/test_app.py.
