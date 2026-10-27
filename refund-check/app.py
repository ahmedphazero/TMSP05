"""Flask app: form -> checks layer -> success or problems."""
import os

from flask import Flask, render_template, request

import db
from checks import parse_invoices, run_checks
from rules import CATEGORIES, DOCUMENTS, REQUIRED_DOCUMENTS


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024        # 20 MB per request
    app.config["DB_PATH"] = db_path or os.environ.get("DB_PATH", "refunds.db")
    db.init_db(app.config["DB_PATH"])

    def form_context(**extra):
        ctx = dict(categories=CATEGORIES, documents=DOCUMENTS, required=REQUIRED_DOCUMENTS,
                   values={}, problems=[], errors={})
        ctx.update(extra)
        return ctx

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            return render_template("form.html", **form_context())

        data = {k: request.form.get(k, "") for k in
                ("extin", "category", "period_from", "period_to", "amount", "invoices")}
        files = {k: request.files.get(k) for k in DOCUMENTS}

        problems = run_checks(data, files, app.config["DB_PATH"])
        if problems:
            errors = {}
            for p in problems:
                errors.setdefault(p.field, []).append(p.message)
            return render_template("form.html", **form_context(
                values=data, problems=problems, errors=errors)), 422

        ref = db.save_submission(
            app.config["DB_PATH"], data["extin"].strip().upper(), data["category"],
            data["period_from"], data["period_to"], data["amount"].strip(),
            parse_invoices(data["invoices"]),
        )
        return render_template("success.html", reference=ref, values=data,
                               category_label=CATEGORIES[data["category"]])

    @app.route("/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(413)
    def too_large(_):
        return render_template("form.html", **form_context(
            problems=[type("P", (), {"field": "files", "message": "Upload is too large (max 20 MB)."})()]
        )), 413

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
