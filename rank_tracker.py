import base64
import math
import re
import time
import urllib.parse
from typing import Dict, List, Optional
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


COUNTRY_GL_MAP = {
    "united states": "us",
    "usa": "us",
    "united kingdom": "uk",
    "uk": "uk",
    "great britain": "uk",
    "sri lanka": "lk",
    "canada": "ca",
    "australia": "au",
    "germany": "de",
    "france": "fr",
    "india": "in",
    "singapore": "sg",
    "united arab emirates": "ae",
    "uae": "ae",
    "dubai": "ae",
    "new zealand": "nz",
    "ireland": "ie",
    "netherlands": "nl",
    "spain": "es",
    "italy": "it",
    "brazil": "br",
    "japan": "jp",
    "south africa": "za",
    "malaysia": "my",
    "philippines": "ph",
    "pakistan": "pk",
    "bangladesh": "bd",
    "indonesia": "id",
    "mexico": "mx",
}


def generate_uule(location_name: str) -> str:
    """Generates Google UULE location emulation parameter."""
    secret_key = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    location_clean = location_name.strip()
    if not location_clean:
        return ""
    
    length = len(location_clean)
    if length >= len(secret_key):
        location_clean = location_clean[: len(secret_key) - 1]
        length = len(location_clean)
        
    hashed_length = secret_key[length]
    encoded_loc = base64.b64encode(location_clean.encode("utf-8")).decode("utf-8")
    return f"w+CAIQICI{hashed_length}{encoded_loc}"


def detect_country_code(location_name: str) -> str:
    """Detects 2-letter ISO country code from location name."""
    loc_lower = location_name.lower()
    for country, gl in COUNTRY_GL_MAP.items():
        if country in loc_lower:
            return gl
    parts = [p.strip() for p in loc_lower.split(",")]
    if parts and len(parts[-1]) == 2:
        return parts[-1]
    return "us"


def normalize_domain(url_or_domain: str) -> str:
    """Strips protocol, www, port, and paths for clean domain matching."""
    text = url_or_domain.strip().lower()
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"^www\.", "", text)
    text = text.split("/")[0].split("?")[0].split("#")[0]
    return text


def resolve_real_url(url: str) -> str:
    """Resolves Google /goto or /url redirects to actual target URLs."""
    if not url:
        return ""
    
    if "google.com/goto?url=" in url or "/goto?url=" in url:
        try:
            full_url = url if url.startswith("http") else f"https://www.google.com{url}"
            resp = requests.get(full_url, allow_redirects=False, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
            loc = resp.headers.get("Location")
            if loc:
                return loc
        except Exception:
            pass

    if "/url?q=" in url:
        try:
            parsed = urllib.parse.urlparse(url)
            queries = urllib.parse.parse_qs(parsed.query)
            if "q" in queries and queries["q"]:
                return queries["q"][0]
        except Exception:
            pass
            
    return url


def is_target_match(target: str, result_url: str, result_display: str) -> bool:
    """Checks if a search result matches the target website/domain."""
    target_clean = normalize_domain(target)
    url_domain = normalize_domain(result_url)
    display_domain = normalize_domain(result_display)
    
    # 1. Root domain or subdomain match
    if target_clean in url_domain or target_clean in display_domain:
        return True
    
    # 2. Substring match for target name
    if target.strip().lower() in result_url.lower() or target.strip().lower() in result_display.lower():
        return True
        
    return False


class GoogleRankTracker:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def _create_driver(self) -> webdriver.Chrome:
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        # Anti-detection flags
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        driver = webdriver.Chrome(options=options)
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"}
            )
        except Exception:
            pass
            
        return driver

    def check_rank(
        self,
        keyword: str,
        location: str,
        target_website: str,
        max_results: int = 50,
        country_code: Optional[str] = None,
        language: str = "en"
    ) -> Dict:
        """
        Performs multi-page localized Google SERP scan.
        Scans across all pages (Page 1, 2, 3...) up to max_results,
        capturing ALL occurrences and count of target_website.
        """
        start_time = time.time()
        
        uule = generate_uule(location) if location else ""
        gl = country_code.lower() if country_code else detect_country_code(location)
        
        driver = None
        extracted_results: List[Dict] = []
        all_target_matches: List[Dict] = []
        seen_identifiers = set()
        
        # Compute how many Google pages to visit (each page usually has ~10 organic results)
        pages_to_crawl = max(1, math.ceil(max_results / 10))
        # Cap at 10 pages (top 100) to keep execution fast and prevent bot blocks
        pages_to_crawl = min(pages_to_crawl, 10)
        
        rank_counter = 1
        
        try:
            driver = self._create_driver()
            driver.set_page_load_timeout(15)
            
            for page_idx in range(pages_to_crawl):
                if rank_counter > max_results:
                    break
                    
                start_offset = page_idx * 10
                params = {
                    "q": keyword,
                    "hl": language,
                    "gl": gl,
                    "start": start_offset
                }
                if uule:
                    params["uule"] = uule

                search_url = f"https://www.google.com/search?{urllib.parse.urlencode(params)}"
                
                try:
                    driver.get(search_url)
                except Exception:
                    try:
                        driver.execute_script("window.stop();")
                    except Exception:
                        pass
                        
                time.sleep(1.5)
                
                # Dismiss cookie banner on first page if present
                if page_idx == 0:
                    consent_buttons = driver.find_elements(
                        By.XPATH,
                        "//button[contains(., 'Accept all') or contains(., 'I agree') or contains(., 'Accept')]"
                    )
                    if consent_buttons:
                        try:
                            consent_buttons[0].click()
                            time.sleep(1)
                        except Exception:
                            pass

                # Locate organic search result cards
                containers = driver.find_elements(
                    By.CSS_SELECTOR,
                    "div.tF2Cxc, div.MjjYud div.yuRUbf, div.g, div[data-sokoban-container]"
                )
                
                page_extracted_count = 0
                
                for c in containers:
                    if rank_counter > max_results:
                        break
                        
                    try:
                        h3_elements = c.find_elements(By.TAG_NAME, "h3")
                        if not h3_elements:
                            continue
                        title = h3_elements[0].text.strip()
                        if not title:
                            continue
                            
                        cite_elements = c.find_elements(By.TAG_NAME, "cite")
                        display_url = cite_elements[0].text.strip() if cite_elements else ""
                        
                        a_elements = c.find_elements(By.TAG_NAME, "a")
                        raw_href = a_elements[0].get_attribute("href") if a_elements else ""
                        
                        # Deduplicate by title + display_url
                        item_id = f"{title}_{display_url}"
                        if item_id in seen_identifiers:
                            continue
                        seen_identifiers.add(item_id)
                        
                        # Description snippet
                        snippet = ""
                        snippet_elems = c.find_elements(
                            By.CSS_SELECTOR,
                            "div.VwiC3b, div[data-sncf], span.aCOpRe"
                        )
                        if snippet_elems:
                            snippet = snippet_elems[0].text.strip()
                            
                        # Target match test
                        is_match = is_target_match(target_website, raw_href, display_url)
                        
                        real_url = raw_href
                        if is_match and raw_href.startswith("https://www.google.com/goto"):
                            resolved = resolve_real_url(raw_href)
                            if resolved:
                                real_url = resolved
                        elif not raw_href.startswith("http") and display_url.startswith("http"):
                            real_url = display_url.split(" ")[0]

                        result_entry = {
                            "rank": rank_counter,
                            "page": page_idx + 1,
                            "title": title,
                            "url": real_url,
                            "display_url": display_url,
                            "snippet": snippet,
                            "is_target": is_match
                        }
                        
                        extracted_results.append(result_entry)
                        
                        if is_match:
                            all_target_matches.append(result_entry)
                            
                        rank_counter += 1
                        page_extracted_count += 1
                    except Exception:
                        continue
                        
                # If a page returned 0 new results, we reached the end of Google SERP
                if page_extracted_count == 0:
                    break

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "keyword": keyword,
                "location": location,
                "target_website": target_website,
                "duration_seconds": round(time.time() - start_time, 2)
            }
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        duration = round(time.time() - start_time, 2)
        target_found = len(all_target_matches) > 0
        best_match = all_target_matches[0] if target_found else None
        
        return {
            "success": True,
            "keyword": keyword,
            "location": location,
            "country_code": gl,
            "target_website": target_website,
            "target_found": target_found,
            "rank": best_match["rank"] if best_match else None,
            "page": best_match["page"] if best_match else None,
            "appearances_count": len(all_target_matches),
            "all_appearances": all_target_matches,
            "matched_item": best_match,
            "total_extracted": len(extracted_results),
            "max_checked": max_results,
            "pages_scanned": page_idx + 1 if 'page_idx' in locals() else 1,
            "duration_seconds": duration,
            "results": extracted_results
        }
