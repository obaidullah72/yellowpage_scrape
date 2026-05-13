import logging
import random
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from .models import Business, Notifier, ScrapeLog
from .services import next_run_for_frequency

logger = logging.getLogger(__name__)

BASE_URL = "https://www.yellowpages.com"
USER_AGENTS = [
    settings.YELLOWPAGES_USER_AGENT,
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


@dataclass
class ScrapeResult:
    pages_scraped: int = 0
    businesses_found: int = 0
    new_businesses: int = 0


class YellowPagesScraper:
    """Fetch Yellow Pages HTML via a warmed requests session; fall back to Playwright on 403."""

    def __init__(self, notifier):
        self.notifier = notifier
        self.session = requests.Session()
        self._session_warmed = False
        self._pw = None
        self._pw_browser = None
        self._pw_context = None

    def close(self):
        if self._pw_context is not None:
            try:
                self._pw_context.close()
            except Exception:
                logger.debug("Playwright context close failed", exc_info=True)
            self._pw_context = None
        if self._pw_browser is not None:
            try:
                self._pw_browser.close()
            except Exception:
                logger.debug("Playwright browser close failed", exc_info=True)
            self._pw_browser = None
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                logger.debug("Playwright stop failed", exc_info=True)
            self._pw = None

    def scrape(self):
        result = ScrapeResult()
        try:
            for page in range(1, self.notifier.max_pages + 1):
                try:
                    html = self._fetch_search_page(page)
                except requests.HTTPError as exc:
                    if exc.response is not None and exc.response.status_code in (401, 403):
                        logger.error(
                            "Yellow Pages returned %s (blocked). "
                            "Set SCRAPER_USE_PLAYWRIGHT=true and run: playwright install chromium",
                            exc.response.status_code,
                        )
                        break
                    logger.exception("Failed to fetch YellowPages page %s", page)
                    break
                except requests.RequestException:
                    logger.exception("Failed to fetch YellowPages page %s", page)
                    break

                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select(".result")
                if not cards and self._looks_blocked(soup):
                    raise RuntimeError("YellowPages anti-bot protection or captcha detected")

                result.pages_scraped += 1
                for card in cards:
                    business_data = self._parse_card(card)
                    if not business_data.get("yellowpages_url"):
                        continue
                    detail_data = self._fetch_detail_data(business_data["yellowpages_url"])
                    business_data.update({key: value for key, value in detail_data.items() if value})
                    result.businesses_found += 1
                    _, created = self._store_business(business_data)
                    if created:
                        result.new_businesses += 1
                        logger.info(
                            "New business saved for user %s: %s",
                            self.notifier.user_id,
                            business_data.get("name"),
                        )
                time.sleep(settings.SCRAPER_DELAY_SECONDS + random.uniform(0.2, 1.5))
        finally:
            self.close()
        return result

    def _build_search_terms(self):
        """Avoid redundant `keyword + category` when they are the same phrase (e.g. car wash + Car Wash)."""
        kw = (self.notifier.keyword or "").strip()
        cat = (self.notifier.category or "").strip()
        if not cat:
            return kw
        kw_l, cat_l = kw.lower(), cat.lower()
        if cat_l in kw_l or kw_l in cat_l.replace(" ", ""):
            return kw
        return f"{kw} {cat}".strip()

    def _warm_session(self):
        if self._session_warmed:
            return
        try:
            resp = self.session.get(
                f"{BASE_URL}/",
                headers=self._browser_headers(referer=None, sec_fetch_site="none"),
                timeout=settings.SCRAPER_TIMEOUT_SECONDS,
                allow_redirects=True,
            )
            logger.debug("YellowPages session warm GET / status=%s", resp.status_code)
        except requests.RequestException:
            logger.warning("YellowPages homepage warm failed", exc_info=True)
        self._session_warmed = True

    def _browser_headers(self, *, referer: str | None, sec_fetch_site: str):
        ua = random.choice(USER_AGENTS)
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": sec_fetch_site,
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def _fetch_html(self, url: str, *, referer: str) -> str:
        self._warm_session()
        headers = self._browser_headers(referer=referer, sec_fetch_site="same-origin")
        response = self.session.get(
            url,
            headers=headers,
            timeout=settings.SCRAPER_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
        if response.status_code == 403 and settings.SCRAPER_USE_PLAYWRIGHT:
            logger.warning("YellowPages returned 403; retrying with Playwright (browser)")
            return self._playwright_get(url)
        response.raise_for_status()
        return response.text

    def _playwright_get(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Yellow Pages blocked the request (403). Install Playwright: "
                "pip install playwright && playwright install chromium"
            ) from exc

        if self._pw is None:
            self._pw = sync_playwright().start()
            self._pw_browser = self._pw.chromium.launch(headless=True)
            self._pw_context = self._pw_browser.new_context(
                user_agent=settings.YELLOWPAGES_USER_AGENT,
                viewport={"width": 1366, "height": 900},
                locale="en-US",
            )
        page = self._pw_context.new_page()
        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=max(30_000, settings.SCRAPER_TIMEOUT_SECONDS * 1000),
            )
            time.sleep(1.5 + random.uniform(0, 0.8))
            return page.content()
        finally:
            page.close()

    def _fetch_search_page(self, page_num: int) -> str:
        params = {
            "search_terms": self._build_search_terms(),
            "geo_location_terms": self.notifier.location,
            "page": page_num,
        }
        req = requests.Request("GET", f"{BASE_URL}/search", params=params)
        prep = self.session.prepare_request(req)
        return self._fetch_html(prep.url, referer=f"{BASE_URL}/")

    def _fetch_detail_data(self, yellowpages_url):
        try:
            time.sleep(random.uniform(0.5, 1.5))
            html = self._fetch_html(yellowpages_url, referer=f"{BASE_URL}/")
        except requests.RequestException:
            logger.warning("Could not fetch business detail page: %s", yellowpages_url, exc_info=True)
            return {}
        return self._parse_detail(BeautifulSoup(html, "html.parser"))

    def _parse_card(self, card):
        name_node = card.select_one(".business-name span") or card.select_one(".business-name")
        url_node = card.select_one(".business-name")
        phone_node = card.select_one(".phones.phone.primary") or card.select_one(".phone")
        street_node = card.select_one(".street-address")
        locality_node = card.select_one(".locality")
        categories = [node.get_text(" ", strip=True) for node in card.select(".categories a")]
        rating_node = card.select_one(".result-rating")
        reviews_node = card.select_one(".count")
        website_node = card.select_one(".track-visit-website")
        image_node = card.select_one("img")

        full_address = " ".join(
            value for value in [self._text(street_node), self._text(locality_node)] if value
        )
        city, state, zip_code = parse_location(self._text(locality_node))
        yp_url = urljoin(BASE_URL, url_node.get("href", "")) if url_node else ""

        return {
            "name": self._text(name_node),
            "category": categories[0] if categories else self.notifier.category,
            "sub_category": categories[1] if len(categories) > 1 else "",
            "phone_number": normalize_blank(self._text(phone_node)),
            "website": clean_external_url(website_node.get("href")) if website_node else "",
            "full_address": full_address,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": "USA",
            "rating": parse_decimal(rating_node.get("class", [""])[-1].replace("stars", "")) if rating_node else None,
            "review_count": parse_int(self._text(reviews_node)),
            "yellowpages_url": yp_url,
            "logo_image": urljoin(BASE_URL, image_node.get("src", "")) if image_node and image_node.get("src") else "",
            "source_keyword": self.notifier.keyword,
            "source_location": self.notifier.location,
        }

    def _parse_detail(self, soup):
        email_node = soup.select_one("a.email-business")
        website_node = soup.select_one("a.website-link")
        description_node = soup.select_one(".business-card-footer .general-info") or soup.select_one(".description")
        hours = {}
        for row in soup.select(".open-details tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td, th")]
            if len(cells) >= 2:
                hours[cells[0]] = cells[1]

        social_links = []
        for node in soup.select("a[href*='facebook.com'], a[href*='instagram.com'], a[href*='linkedin.com'], a[href*='twitter.com'], a[href*='x.com']"):
            href = node.get("href")
            if href:
                social_links.append(href)

        lat, lng = None, None
        map_node = soup.select_one("a.directions, a[href*='maps']")
        if map_node:
            lat, lng = extract_lat_lng(map_node.get("href", ""))

        return {
            "email": normalize_blank(extract_email(email_node.get("href", "")) if email_node else ""),
            "website": clean_external_url(website_node.get("href")) if website_node else "",
            "description": self._text(description_node),
            "working_hours": hours,
            "social_media_links": sorted(set(social_links)),
            "latitude": lat,
            "longitude": lng,
        }

    def _store_business(self, data):
        data = normalize_business_data(data)
        lookup = Q(yellowpages_url=data["yellowpages_url"])
        if data.get("phone_number"):
            lookup |= Q(phone_number=data["phone_number"])
        if data.get("email"):
            lookup |= Q(email=data["email"])

        defaults = data.copy()
        defaults["notifier"] = self.notifier
        try:
            with transaction.atomic():
                existing = Business.objects.filter(lookup).first()
                if existing:
                    for key, value in defaults.items():
                        if value not in (None, "", {}, []) or not getattr(existing, key):
                            setattr(existing, key, value)
                    existing.save()
                    return existing, False
                return Business.objects.create(**defaults), True
        except IntegrityError:
            logger.info("Duplicate business detected during save: %s", data.get("yellowpages_url"))
            return Business.objects.filter(lookup).first(), False

    @staticmethod
    def _text(node):
        return node.get_text(" ", strip=True) if node else ""

    @staticmethod
    def _looks_blocked(soup):
        text = soup.get_text(" ", strip=True).lower()
        return "captcha" in text or "unusual traffic" in text or "access denied" in text


def run_notifier_scrape(notifier):
    log = ScrapeLog.objects.create(notifier=notifier, status=ScrapeLog.STATUS_STARTED, message="Scrape started")
    try:
        result = YellowPagesScraper(notifier).scrape()
        log.status = ScrapeLog.STATUS_SUCCESS
        log.message = "Scrape completed"
        log.pages_scraped = result.pages_scraped
        log.businesses_found = result.businesses_found
        log.new_businesses = result.new_businesses
    except Exception as exc:
        logger.exception("Scrape failed for notifier %s", notifier.pk)
        log.status = ScrapeLog.STATUS_ERROR
        log.message = "Scrape failed"
        log.error_details = str(exc)
    finally:
        log.completed_at = timezone.now()
        log.save()
        notifier.last_run_at = timezone.now()
        notifier.next_run_at = next_run_for_frequency(notifier.frequency, notifier.last_run_at)
        notifier.save(update_fields=["last_run_at", "next_run_at"])
    return log


def run_due_notifiers():
    now = timezone.now()
    notifiers = Notifier.objects.filter(is_active=True).filter(Q(next_run_at__isnull=True) | Q(next_run_at__lte=now))
    for notifier in notifiers:
        run_notifier_scrape(notifier)


def parse_location(locality):
    if not locality:
        return "", "", ""
    match = re.match(r"(?P<city>.*?),\s*(?P<state>[A-Z]{2})\s*(?P<zip>\d{5}(?:-\d{4})?)?", locality)
    if not match:
        return locality, "", ""
    return match.group("city") or "", match.group("state") or "", match.group("zip") or ""


def parse_int(value):
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return int(digits) if digits else None


def parse_decimal(value):
    if not value:
        return None
    normalized = str(value).replace("_", ".")
    match = re.search(r"\d+(?:\.\d+)?", normalized)
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return None


def extract_email(value):
    if value.startswith("mailto:"):
        return value.replace("mailto:", "").split("?")[0]
    return value


def extract_lat_lng(url):
    query = parse_qs(urlparse(url).query)
    for key in ("query", "q"):
        if key in query:
            match = re.search(r"(-?\d+\.\d+),\s*(-?\d+\.\d+)", query[key][0])
            if match:
                return Decimal(match.group(1)), Decimal(match.group(2))
    return None, None


def clean_external_url(url):
    if not url:
        return ""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "redirect" in query:
        return query["redirect"][0]
    if not parsed.scheme:
        return f"https://{url.lstrip('/')}"
    return url


def normalize_blank(value):
    value = (value or "").strip()
    return value or None


def normalize_business_data(data):
    normalized = data.copy()
    normalized["name"] = normalized.get("name") or "Unknown Business"
    normalized["yellowpages_url"] = normalized.get("yellowpages_url") or f"{BASE_URL}/search?search_terms={quote_plus(normalized['name'])}"
    for key in ("phone_number", "email"):
        normalized[key] = normalize_blank(normalized.get(key))
    return normalized
