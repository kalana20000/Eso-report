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
        description="SEO Google Rank Tracker: Search a keyword on Google across all pages and find all placings of a website."
    )
    parser.add_argument("-k", "--keyword", required=True, help="Keyword to search on Google")
    parser.add_argument("-l", "--location", required=True, help="Geographical location (e.g. 'Colombo, Sri Lanka' or 'Austin, Texas, United States')")
    parser.add_argument("-t", "--target", required=True, help="Target website or domain to rank (e.g. 'coffee.lk' or 'example.com')")
    parser.add_argument("-n", "--max-results", type=int, default=50, help="Maximum number of organic results to inspect across pages (default: 50)")
    parser.add_argument("-c", "--country", default=None, help="2-letter country code override (gl), e.g. 'lk', 'us', 'uk'")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    init_db()
    tracker = GoogleRankTracker(headless=True)

    if not args.json:
        print("\n" + "=" * 70)
        print("🔍 Google Deep SEO Rank Tracker (Multi-Page)")
        print("=" * 70)
        print(f"Keyword:        {args.keyword}")
        print(f"Location:       {args.location}")
        print(f"Target Website: {args.target}")
        print(f"Scan Depth:     Top {args.max_results} results")
        print("-" * 70)
        print("Scanning Google SERP across multiple pages via stealth browser...")

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

    record_id = save_check_result(result)

    if args.json:
        result["db_record_id"] = record_id
        print(json.dumps(result, indent=2))
        return

    print("\n" + "=" * 70)
    print("📊 RANK CHECK & APPEARANCES AUDIT")
    print("=" * 70)
    
    if result["target_found"]:
        count = result["appearances_count"]
        best = result["matched_item"]
        print(f"🎉 FOUND! Target appears {count} time{'s' if count != 1 else ''} across {result['total_extracted']} scanned results.")
        print(f"🏆 Best Ranking:  Rank #{best['rank']} (Page {best['page']})")
        print(f"🔗 URL:           {best.get('url') or best.get('display_url')}")
        print(f"📝 Title:         {best.get('title')}")
        
        if count > 1:
            print("\n📋 All Matched Appearances:")
            for idx, item in enumerate(result["all_appearances"], 1):
                print(f"   [{idx}] Rank #{item['rank']} (Page {item['page']}): {item['title'][:40]} -> {item['url']}")
    else:
        print(f"⚠️  NOT FOUND in Top {result['total_extracted']} organic results across {result.get('pages_scanned', 1)} pages.")
        print(f"💡 Target '{args.target}' did not appear in any of the scanned pages.")

    print(f"\n⏱️  Duration: {result['duration_seconds']}s | Pages Scanned: {result.get('pages_scanned', 1)} | Total Results: {result['total_extracted']}")
    print("-" * 70)
    print("Sample Top SERP Placings:")
    for item in result["results"][:15]:
        marker = "👉 [TARGET]" if item["is_target"] else f"#{item['rank']} (P{item['page']})"
        title_disp = item['title'][:40]
        print(f"  {marker:<14} {title_disp:<42} | {item['display_url']}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
