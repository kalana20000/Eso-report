import base64
import re
import time
import urllib.parse
from typing import Dict, List, Optional, Tuple
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


# Country name to ISO-3166 2-letter country code mapping for Google 'gl' parameter
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
    """
    Generates a Google UULE parameter from a location string.
    Google uses UULE to emulate localized search results without a proxy.
    
    Format:
    w+CAIQICI + <secret_length_key> + base64(<canonical_location>)
    """
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
    """
    Attempts to detect the two-letter ISO country code (gl) from location string.
    Defaults to 'us' if unknown.
    """
    loc_lower = location_name.lower()
    for country, gl in COUNTRY_GL_MAP.items():
        if country in loc_lower:
            return gl
    # Check if last token is a 2-letter country code
    parts = [p.strip() for p in loc_lower.split(",")]
    if parts and len(parts[-1]) == 2:
        return parts[-1]
    return "us"


def normalize_domain(url_or_domain: str) -> str:
    """
    Normalizes domain/URL for comparison by stripping protocol, 'www.',
    port, path, query parameters, and trailing slashes.
    Example: 'https://www.example.com/blog/' -> 'example.com'
    """
    text = url_or_domain.strip().lower()
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"^www\.", "", text)
    text = text.split("/")[0].split("?")[0].split("#")[0]
    return text


def resolve_real_url(url: str) -> str:
    """
    Resolves Google redirect URLs (/goto?url=... or /url?q=...) to final destinations.
    """
    if not url:
        return ""
    
    # Check if it is a Google redirect
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
    """
    Checks if a search result matches the target website/domain.
    Supports root domains, subdomains, or exact URLs.
    """
    target_clean = normalize_domain(target)
    url_domain = normalize_domain(result_url)
    display_domain = normalize_domain(result_display)
    
    # 1. Exact domain or subdomain match
    if target_clean in url_domain or target_clean in display_domain:
        return True
    
    # 2. Check if target is a substring of the raw display text or URL
    if target.strip().lower() in result_url.lower() or target.strip().lower() in result_display.lower():
        return True
        
    return False


class GoogleRankTracker:
    """
    SEO Rank Tracker that queries Google Search with location emulation (UULE + gl)
    using a stealth headless browser to extract real organic placings.
    """
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
        
        # Anti-bot detection flags
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        driver = webdriver.Chrome(options=options)
        # Patch navigator.webdriver via Chrome DevTools Protocol
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
        max_results: int = 30,
        country_code: Optional[str] = None,
        language: str = "en"
    ) -> Dict:
        """
        Executes Google search for keyword localized to `location` and finds `target_website` placing.
        """
        start_time = time.time()
        
        # Resolve location parameters
        uule = generate_uule(location) if location else ""
        gl = country_code.lower() if country_code else detect_country_code(location)
        
        # Build search query URL
        params = {
            "q": keyword,
            "hl": language,
            "gl": gl,
            "num": min(max(max_results, 10), 100),
        }
        if uule:
            params["uule"] = uule

        search_url = f"https://www.google.com/search?{urllib.parse.urlencode(params)}"
        
        driver = None
        extracted_results: List[Dict] = []
        target_found = False
        target_rank = None
        matched_item = None
        
        try:
            driver = self._create_driver()
            driver.set_page_load_timeout(15)
            try:
                driver.get(search_url)
            except Exception:
                try:
                    driver.execute_script("window.stop();")
                except Exception:
                    pass
            time.sleep(1.5)
            
            # Dismiss cookie consent if shown
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

            # Scroll down to load extra organic items if continuous scroll is active
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

            # Locate organic search result cards
            # Modern Google uses containers like div.tF2Cxc, div.MjjYud, div.g
            containers = driver.find_elements(
                By.CSS_SELECTOR,
                "div.tF2Cxc, div.MjjYud div.yuRUbf, div.g, div[data-sokoban-container]"
            )
            
            seen_titles = set()
            rank_counter = 1
            
            for c in containers:
                if rank_counter > max_results:
                    break
                    
                try:
                    # Extract title
                    h3_elements = c.find_elements(By.TAG_NAME, "h3")
                    if not h3_elements:
                        continue
                    title = h3_elements[0].text.strip()
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    
                    # Extract display cite / snippet
                    cite_elements = c.find_elements(By.TAG_NAME, "cite")
                    display_url = cite_elements[0].text.strip() if cite_elements else ""
                    
                    # Extract link
                    a_elements = c.find_elements(By.TAG_NAME, "a")
                    raw_href = a_elements[0].get_attribute("href") if a_elements else ""
                    
                    # Extract snippet / description text
                    snippet = ""
                    snippet_elems = c.find_elements(
                        By.CSS_SELECTOR,
                        "div.VwiC3b, div[data-sncf], span.aCOpRe"
                    )
                    if snippet_elems:
                        snippet = snippet_elems[0].text.strip()
                        
                    # Check match against target_website
                    is_match = is_target_match(target_website, raw_href, display_url)
                    
                    real_url = raw_href
                    if is_match and raw_href.startswith("https://www.google.com/goto"):
                        # Only resolve redirect when we need the exact final destination of target
                        resolved = resolve_real_url(raw_href)
                        if resolved:
                            real_url = resolved
                    elif not raw_href.startswith("http") and display_url.startswith("http"):
                        real_url = display_url.split(" ")[0]

                    result_entry = {
                        "rank": rank_counter,
                        "page": ((rank_counter - 1) // 10) + 1,
                        "title": title,
                        "url": real_url,
                        "display_url": display_url,
                        "snippet": snippet,
                        "is_target": is_match
                    }
                    
                    extracted_results.append(result_entry)
                    
                    if is_match and not target_found:
                        target_found = True
                        target_rank = rank_counter
                        matched_item = result_entry
                        
                    rank_counter += 1
                except Exception:
                    continue

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
        
        return {
            "success": True,
            "keyword": keyword,
            "location": location,
            "country_code": gl,
            "target_website": target_website,
            "target_found": target_found,
            "rank": target_rank,
            "page": ((target_rank - 1) // 10) + 1 if target_rank else None,
            "matched_item": matched_item,
            "total_extracted": len(extracted_results),
            "max_checked": max_results,
            "duration_seconds": duration,
            "search_url": search_url,
            "results": extracted_results
        }
