import feedparser
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return BeautifulSoup(text, "lxml").get_text(separator=" ", strip=True)


def _parse_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def fetch_feed(url: str, max_age_hours: int = 25, keywords: list[str] | None = None) -> list[dict]:
    """Fetch an RSS feed and return articles published within max_age_hours.

    If keywords are provided, only articles whose title or summary contain at
    least one keyword (case-insensitive) are returned.
    """
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "DailyNewsAgent/1.0"})
    except Exception as e:
        print(f"[rss] Error fetching {url}: {e}")
        return []

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=max_age_hours)
    articles = []

    for entry in feed.entries:
        published = _parse_date(entry)
        if published and published < cutoff:
            continue

        title = entry.get("title", "").strip()
        summary = _strip_html(entry.get("summary", entry.get("description", "")))
        link = entry.get("link", "")
        source = feed.feed.get("title", url)

        if keywords:
            haystack = (title + " " + summary).lower()
            if not any(kw.lower() in haystack for kw in keywords):
                continue

        articles.append({
            "title": title,
            "link": link,
            "summary": summary[:800],
            "published": published.isoformat() if published else None,
            "source": source,
        })

    return articles


def fetch_section(sources: list[dict], max_age_hours: int = 25) -> list[dict]:
    """Fetch multiple RSS sources for a section, merging and deduplicating by link."""
    seen_links: set[str] = set()
    all_articles: list[dict] = []

    for source in sources:
        url = source["url"]
        keywords = source.get("keywords")
        articles = fetch_feed(url, max_age_hours=max_age_hours, keywords=keywords)
        for article in articles:
            if article["link"] not in seen_links:
                seen_links.add(article["link"])
                all_articles.append(article)

    all_articles.sort(key=lambda a: a["published"] or "", reverse=True)
    return all_articles
