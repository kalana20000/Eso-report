import csv
import io
import json
from flask import Flask, jsonify, render_template, request, Response

from database import (
    delete_check_by_id,
    get_check_by_id,
    get_recent_checks,
    init_db,
    save_check_result,
)
from rank_tracker import GoogleRankTracker, detect_country_code

app = Flask(__name__)
init_db()

# Singleton tracker instance (headless)
rank_tracker = GoogleRankTracker(headless=True)


@app.route("/")
def index():
    """Render the main SEO rank tracker web dashboard."""
    recent_checks = get_recent_checks(limit=15)
    return render_template("index.html", recent_checks=recent_checks)


@app.route("/api/check", methods=["POST"])
def api_check_rank():
    """
    Search Google with location emulation and find target website ranking.
    Expected JSON payload or Form data:
    {
        "keyword": "best coffee shop",
        "location": "Colombo, Sri Lanka",
        "target_website": "coffee.lk",
        "max_results": 30,
        "country_code": "lk" (optional)
    }
    """
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    keyword = data.get("keyword", "").strip()
    location = data.get("location", "").strip()
    target_website = data.get("target_website", "").strip()
    max_results = int(data.get("max_results", 30))
    country_code = data.get("country_code", "").strip() or None

    if not keyword:
        return jsonify({"success": False, "error": "Keyword is required"}), 400
    if not location:
        return jsonify({"success": False, "error": "Location is required"}), 400
    if not target_website:
        return jsonify({"success": False, "error": "Target website is required"}), 400

    # Auto-detect country code if not provided
    if not country_code:
        country_code = detect_country_code(location)

    # Perform Google localized search and rank extraction
    result = rank_tracker.check_rank(
        keyword=keyword,
        location=location,
        target_website=target_website,
        max_results=max_results,
        country_code=country_code,
    )

    if not result.get("success"):
        return jsonify(result), 500

    # Save to SQLite database
    record_id = save_check_result(result)
    result["id"] = record_id

    return jsonify(result)


@app.route("/api/history", methods=["GET"])
def api_history():
    """Returns past rank checks."""
    limit = int(request.args.get("limit", 50))
    checks = get_recent_checks(limit=limit)
    return jsonify({"success": True, "history": checks})


@app.route("/api/check/<int:record_id>", methods=["GET"])
def api_get_check(record_id):
    """Returns details and full SERP results of a previous check."""
    record = get_check_by_id(record_id)
    if not record:
        return jsonify({"success": False, "error": "Record not found"}), 404
    return jsonify({"success": True, "check": record})


@app.route("/api/check/<int:record_id>", methods=["DELETE"])
def api_delete_check(record_id):
    """Deletes a record from history."""
    deleted = delete_check_by_id(record_id)
    return jsonify({"success": deleted})


@app.route("/export/csv/<int:record_id>")
def export_csv(record_id):
    """Generates a downloadable CSV report of the SERP results for an audit."""
    record = get_check_by_id(record_id)
    if not record:
        return "Record not found", 404

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow([
        "Rank",
        "Page",
        "Title",
        "URL",
        "Display Domain",
        "Snippet",
        "Is Target",
    ])

    for r in record.get("results", []):
        writer.writerow([
            r.get("rank"),
            r.get("page"),
            r.get("title"),
            r.get("url"),
            r.get("display_url"),
            r.get("snippet"),
            "YES" if r.get("is_target") else "NO",
        ])

    output = io.BytesIO(si.getvalue().encode("utf-8-sig"))
    filename = f"seo_rank_{record['keyword'].replace(' ', '_')}_{record_id}.csv"
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"},
    )


@app.route("/export/json/<int:record_id>")
def export_json(record_id):
    """Returns full check details as downloadable JSON."""
    record = get_check_by_id(record_id)
    if not record:
        return "Record not found", 404

    filename = f"seo_rank_{record['keyword'].replace(' ', '_')}_{record_id}.json"
    return Response(
        json.dumps(record, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename={filename}"},
    )


if __name__ == "__main__":
    print("\n🚀 Starting SEO Rank Tracker Flask Server on http://127.0.0.1:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
