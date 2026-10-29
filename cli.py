import argparse
import json
import sys

# Configure UTF-8 stdout for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rank_tracker import GoogleRankTracker
from database import init_db, save_check_result

def main():
    parser = argparse.ArgumentParser(
        description="SEO Google Rank Tracker: Search a keyword on Google in a specific location and find the rank of a website."
    )
    parser.add_argument("-k", "--keyword", required=True, help="Keyword to search on Google")
    parser.add_argument("-l", "--location", required=True, help="Geographical location (e.g. 'Colombo, Sri Lanka' or 'Austin, Texas, United States')")
    parser.add_argument("-t", "--target", required=True, help="Target website or domain to rank (e.g. 'coffee.lk' or 'example.com')")
    parser.add_argument("-n", "--max-results", type=int, default=30, help="Maximum number of organic results to inspect (default: 30)")
    parser.add_argument("-c", "--country", default=None, help="2-letter country code override (gl), e.g. 'lk', 'us', 'uk'")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    init_db()
    tracker = GoogleRankTracker(headless=True)

    if not args.json:
        print("\n" + "=" * 65)
        print("[SEO Rank Tracker] Google Local Search")
        print("=" * 65)
        print(f"Keyword:        {args.keyword}")
        print(f"Location:       {args.location}")
        print(f"Target Website: {args.target}")
        print(f"Max Results:    {args.max_results}")
        print("-" * 65)
        print("Fetching localized Google SERP results via stealth browser...")

    result = tracker.check_rank(
        keyword=args.keyword,
        location=args.location,
        target_website=args.target,
        max_results=args.max_results,
        country_code=args.country
    )

    if not result.get("success"):
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n[Error] Search failed: {result.get('error')}")
        sys.exit(1)

    # Save to SQLite database
    record_id = save_check_result(result)

    if args.json:
        result["db_record_id"] = record_id
        print(json.dumps(result, indent=2))
        return

    print("\n" + "=" * 65)
    print("RANK CHECK RESULT")
    print("=" * 65)
    if result["target_found"]:
        print(f"SUCCESS: Target Found at Rank #{result['rank']} (Page {result['page']})")
        matched = result.get("matched_item") or {}
        print(f"URL:   {matched.get('url') or matched.get('display_url')}")
        print(f"Title: {matched.get('title')}")
    else:
        print(f"NOT FOUND in Top {result['total_extracted']} organic results.")
        print("Tip: Try increasing --max-results or check keyword optimization.")

    print(f"Duration: {result['duration_seconds']}s | Total results parsed: {result['total_extracted']}")
    print("-" * 65)
    print("Top 10 SERP Competitors:")
    for item in result["results"][:10]:
        marker = ">> [TARGET]" if item["is_target"] else f"#{item['rank']}"
        title_disp = item['title'][:45]
        print(f"  {marker:<12} {title_disp:<45} | {item['display_url']}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
