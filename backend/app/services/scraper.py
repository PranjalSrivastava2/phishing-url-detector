"""
scraper.py

Given a raw URL, fetches the live webpage and computes the 28 content-based
features the model expects (page structure, forms, links, keywords, etc.).
These complement the 22 URL-only features from feature_extractor.py.

Safety notes:
    - A short timeout and a capped response size are used, since some
      target URLs (especially phishing ones) may be slow, unreachable,
      or intentionally malformed.
    - If the page cannot be fetched at all (timeout, DNS failure, blocked,
      SSL error, etc.), all content-based features default to 0/safe
      values rather than raising an error — the model can still make a
      prediction from the lexical features alone, and a failed fetch is
      itself a mild signal worth logging.
    - Only HTML text is parsed; no scripts are executed, so JS-only
      behaviour (e.g. popups triggered dynamically) is approximated by
      scanning script text for common popup-related function calls.
"""

import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 6            # seconds
MAX_CONTENT_BYTES = 2_000_000  # 2 MB cap, avoid huge pages slowing the scan
USER_AGENT = "Mozilla/5.0 (compatible; PhishingURLDetector/1.0)"

_SOCIAL_DOMAINS = {
    "facebook.com", "twitter.com", "x.com", "instagram.com",
    "linkedin.com", "youtube.com", "pinterest.com", "tiktok.com"
}

_BANK_KEYWORDS = {"bank", "banking", "account", "iban", "swift"}
_PAY_KEYWORDS = {"pay", "payment", "checkout", "invoice", "billing"}
_CRYPTO_KEYWORDS = {"crypto", "bitcoin", "wallet", "blockchain", "ethereum", "btc"}


def _default_content_features() -> dict:
    """Fallback feature values when the page can't be fetched or parsed."""
    return {
        "LineOfCode": 0,
        "LargestLineLength": 0,
        "HasTitle": 0,
        "DomainTitleMatchScore": 0.0,
        "URLTitleMatchScore": 0.0,
        "HasFavicon": 0,
        "Robots": 0,
        "IsResponsive": 0,
        "NoOfURLRedirect": 0,
        "NoOfSelfRedirect": 0,
        "HasDescription": 0,
        "NoOfPopup": 0,
        "NoOfiFrame": 0,
        "HasExternalFormSubmit": 0,
        "HasSocialNet": 0,
        "HasSubmitButton": 0,
        "HasHiddenFields": 0,
        "HasPasswordField": 0,
        "Bank": 0,
        "Pay": 0,
        "Crypto": 0,
        "HasCopyrightInfo": 0,
        "NoOfImage": 0,
        "NoOfCSS": 0,
        "NoOfJS": 0,
        "NoOfSelfRef": 0,
        "NoOfEmptyRef": 0,
        "NoOfExternalRef": 0,
    }


def _text_match_score(a: str, b: str) -> float:
    """Simple word-overlap similarity between two strings, 0-100 scale."""
    a_words = set(re.findall(r"[a-z0-9]+", a.lower()))
    b_words = set(re.findall(r"[a-z0-9]+", b.lower()))
    if not a_words or not b_words:
        return 0.0
    overlap = a_words & b_words
    return 100.0 * len(overlap) / max(len(a_words), len(b_words))


def _classify_link(href: str, base_domain: str) -> str:
    """Classify a link as self, external, or empty relative to base_domain."""
    if not href or href.strip() in ("#", ""):
        return "empty"
    parsed = urlparse(href)
    if not parsed.netloc:
        return "self"  # relative link, stays on same domain
    return "self" if parsed.netloc.lower().lstrip("www.") == base_domain else "external"


def fetch_content_features(url: str) -> dict:
    """
    Fetch the given URL and compute the 28 content-based model features.
    Returns default/zeroed values if the page can't be reached or parsed.
    """
    parsed_url = urlparse(url if "://" in url else f"http://{url}")
    base_domain = parsed_url.netloc.split(":")[0].lower().lstrip("www.")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            stream=True,
        )
        content = response.raw.read(MAX_CONTENT_BYTES, decode_content=True)
        html = content.decode(response.encoding or "utf-8", errors="ignore")
    except requests.RequestException:
        return _default_content_features()

    redirect_count = len(response.history)
    self_redirects = sum(
        1 for r in response.history
        if urlparse(r.url).netloc.lower().lstrip("www.") == base_domain
    )

    soup = BeautifulSoup(html, "html.parser")

    lines = html.splitlines()
    line_of_code = len(lines)
    largest_line_length = max((len(l) for l in lines), default=0)

    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    has_title = int(bool(title_text))

    domain_title_match = _text_match_score(base_domain, title_text)
    url_title_match = _text_match_score(url, title_text)

    has_favicon = int(bool(soup.find("link", rel=lambda r: r and "icon" in r.lower())))
    has_robots_tag = int(bool(soup.find("meta", attrs={"name": "robots"})))
    is_responsive = int(bool(soup.find("meta", attrs={"name": "viewport"})))
    has_description = int(bool(soup.find("meta", attrs={"name": "description"})))

    iframes = soup.find_all("iframe")
    no_of_iframe = len(iframes)

    forms = soup.find_all("form")
    has_external_form_submit = int(any(
        _classify_link(f.get("action", ""), base_domain) == "external" for f in forms
    ))
    has_submit_button = int(bool(
        soup.find("button", attrs={"type": "submit"}) or
        soup.find("input", attrs={"type": "submit"})
    ))
    has_hidden_fields = int(bool(soup.find("input", attrs={"type": "hidden"})))
    has_password_field = int(bool(soup.find("input", attrs={"type": "password"})))

    all_links = soup.find_all("a", href=True)
    social_link_found = any(
        any(sd in link["href"].lower() for sd in _SOCIAL_DOMAINS) for link in all_links
    )

    link_types = [_classify_link(link["href"], base_domain) for link in all_links]
    no_of_self_ref = link_types.count("self")
    no_of_empty_ref = link_types.count("empty")
    no_of_external_ref = link_types.count("external")

    page_text = soup.get_text(" ", strip=True).lower()
    has_bank = int(any(kw in page_text for kw in _BANK_KEYWORDS))
    has_pay = int(any(kw in page_text for kw in _PAY_KEYWORDS))
    has_crypto = int(any(kw in page_text for kw in _CRYPTO_KEYWORDS))
    has_copyright = int("©" in html or "copyright" in page_text)

    no_of_image = len(soup.find_all("img"))
    no_of_css = len(soup.find_all("link", rel="stylesheet")) + len(soup.find_all("style"))
    script_tags = soup.find_all("script")
    no_of_js = len(script_tags)

    script_text = " ".join(s.get_text() for s in script_tags)
    no_of_popup = len(re.findall(r"window\.open\s*\(|alert\s*\(|confirm\s*\(", script_text))

    return {
        "LineOfCode": line_of_code,
        "LargestLineLength": largest_line_length,
        "HasTitle": has_title,
        "DomainTitleMatchScore": domain_title_match,
        "URLTitleMatchScore": url_title_match,
        "HasFavicon": has_favicon,
        "Robots": has_robots_tag,
        "IsResponsive": is_responsive,
        "NoOfURLRedirect": redirect_count,
        "NoOfSelfRedirect": self_redirects,
        "HasDescription": has_description,
        "NoOfPopup": no_of_popup,
        "NoOfiFrame": no_of_iframe,
        "HasExternalFormSubmit": has_external_form_submit,
        "HasSocialNet": int(social_link_found),
        "HasSubmitButton": has_submit_button,
        "HasHiddenFields": has_hidden_fields,
        "HasPasswordField": has_password_field,
        "Bank": has_bank,
        "Pay": has_pay,
        "Crypto": has_crypto,
        "HasCopyrightInfo": has_copyright,
        "NoOfImage": no_of_image,
        "NoOfCSS": no_of_css,
        "NoOfJS": no_of_js,
        "NoOfSelfRef": no_of_self_ref,
        "NoOfEmptyRef": no_of_empty_ref,
        "NoOfExternalRef": no_of_external_ref,
    }


if __name__ == "__main__":
    test_urls = [
        "https://github.com",
        "https://this-domain-should-not-exist-abc123xyz.com",
    ]
    for u in test_urls:
        print(f"\nURL: {u}")
        feats = fetch_content_features(u)
        for k, v in feats.items():
            print(f"  {k}: {v}")
