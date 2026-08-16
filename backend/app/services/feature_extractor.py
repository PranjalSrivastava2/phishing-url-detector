<<<<<<< HEAD
import re
from urllib.parse import urlparse

class FeatureExtractor:
    """
    Extracts lexical, structural, and content-based features from a URL 
    to match the exact 50-feature input matrix required by the ML models.
    """
    
    def __init__(self):
        # The exact order of features expected by the trained XGBoost model
        # (excluding the dropped 'FILENAME', 'URL', 'Domain', 'TLD', 'Title', and 'label')
        self.feature_columns = [
            'URLLength', 'DomainLength', 'IsDomainIP', 'URLSimilarityIndex', 
            'CharContinuationRate', 'TLDLegitimateProb', 'URLCharProb', 'TLDLength', 
            'NoOfSubDomain', 'HasObfuscation', 'NoOfObfuscatedChar', 'ObfuscationRatio', 
            'NoOfLettersInURL', 'LetterRatioInURL', 'NoOfDegitsInURL', 'DegitRatioInURL', 
            'NoOfEqualsInURL', 'NoOfQMarkInURL', 'NoOfAmpersandInURL', 'NoOfOtherSpecialCharsInURL', 
            'SpacialCharRatioInURL', 'IsHTTPS', 'LineOfCode', 'LargestLineLength', 'HasTitle', 
            'DomainTitleMatchScore', 'URLTitleMatchScore', 'HasFavicon', 'Robots', 'IsResponsive', 
            'NoOfURLRedirect', 'NoOfSelfRedirect', 'HasDescription', 'NoOfPopup', 'NoOfiFrame', 
            'HasExternalFormSubmit', 'HasSocialNet', 'HasSubmitButton', 'HasHiddenFields', 
            'HasPasswordField', 'Bank', 'Pay', 'Crypto', 'HasCopyrightInfo', 'NoOfImage', 'NoOfCSS', 
            'NoOfJS', 'NoOfSelfRef', 'NoOfEmptyRef', 'NoOfExternalRef'
        ]

    def extract(self, url: str, scraped_data: dict = None) -> dict:
        """
        Takes a raw URL and an optional dictionary of scraped content features.
        Returns a dictionary of all computed features ready for the ML model.
        """
        if scraped_data is None:
            scraped_data = {}

        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path

        features = {}

        # 1. Length-based Features
        features['URLLength'] = len(url)
        features['DomainLength'] = len(domain)
        
        # 2. Domain & TLD Features
        features['IsDomainIP'] = 1 if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain) else 0
        tld = domain.split('.')[-1] if '.' in domain else ''
        features['TLDLength'] = len(tld)
        features['NoOfSubDomain'] = max(0, len(domain.split('.')) - 2) if not features['IsDomainIP'] else 0
        features['IsHTTPS'] = 1 if parsed_url.scheme == 'https' else 0

        # 3. Character Count Features
        letters = len(re.findall(r'[a-zA-Z]', url))
        digits = len(re.findall(r'[0-9]', url))
        special_chars = len(re.sub(r'[a-zA-Z0-9]', '', url))
        
        features['NoOfLettersInURL'] = letters
        features['LetterRatioInURL'] = letters / len(url) if len(url) > 0 else 0
        features['NoOfDegitsInURL'] = digits
        features['DegitRatioInURL'] = digits / len(url) if len(url) > 0 else 0
        features['NoOfEqualsInURL'] = url.count('=')
        features['NoOfQMarkInURL'] = url.count('?')
        features['NoOfAmpersandInURL'] = url.count('&')
        features['NoOfOtherSpecialCharsInURL'] = special_chars
        features['SpacialCharRatioInURL'] = special_chars / len(url) if len(url) > 0 else 0

        # 4. Advanced / Probabilistic Features (Baseline estimates for live extraction)
        # In a full production environment, these would be computed against a live dataset or frequency table
        features['URLSimilarityIndex'] = 100.0  
        features['CharContinuationRate'] = 1.0  
        features['TLDLegitimateProb'] = 0.5     
        features['URLCharProb'] = 0.05          
        features['HasObfuscation'] = 0
        features['NoOfObfuscatedChar'] = 0
        features['ObfuscationRatio'] = 0.0

        # 5. Content-Based Features (Requires scraper.py)
        # We initialize them safely to 0 and update them if `scraped_data` was successfully fetched
        content_feature_keys = [
            'LineOfCode', 'LargestLineLength', 'HasTitle', 'DomainTitleMatchScore', 
            'URLTitleMatchScore', 'HasFavicon', 'Robots', 'IsResponsive', 'NoOfURLRedirect', 
            'NoOfSelfRedirect', 'HasDescription', 'NoOfPopup', 'NoOfiFrame', 'HasExternalFormSubmit', 
            'HasSocialNet', 'HasSubmitButton', 'HasHiddenFields', 'HasPasswordField', 'Bank', 'Pay', 
            'Crypto', 'HasCopyrightInfo', 'NoOfImage', 'NoOfCSS', 'NoOfJS', 'NoOfSelfRef', 
            'NoOfEmptyRef', 'NoOfExternalRef'
        ]

        for cf in content_feature_keys:
            features[cf] = scraped_data.get(cf, 0)

        # 6. Ensure strict column ordering
        ordered_features = {col: features.get(col, 0) for col in self.feature_columns}
        return ordered_features

#for testing:
if __name__ == "__main__":
    extractor = FeatureExtractor()
    sample_url = "https://www.paypal-secure-login-update.com/verify?id=12345"
    
    # Simulating failed scrape by passing an empty dictionary
    result = extractor.extract(sample_url, scraped_data={})
    print(f"Extracted {len(result)} features for prediction.")
=======
"""
feature_extractor.py

Given a raw URL string, computes the subset of model features that can be
derived instantly from the URL text alone (no network request needed).

This covers 22 of the 50 features the trained model expects:
    - 19 pure lexical/structural features (length, char counts, ratios, etc.)
    - 3 features that need small reference tables built from training data:
      TLDLegitimateProb, URLCharProb, URLSimilarityIndex

The remaining 28 features are content-based (page HTML, forms, images,
title, etc.) and require fetching the actual webpage. Those are computed
separately by scraper.py and merged with this output by predictor.py
before the final feature row is passed to the model.

Note on URLSimilarityIndex: PhiUSIIL's original metric is proprietary and
not fully documented, so this is an approximation — the best fuzzy-match
similarity score (0-100) between the URL's domain and a sample of ~5000
known-legitimate domains from the training set. It captures the same
intent (how closely a domain resembles a known-legitimate one) but is not
guaranteed to numerically match PhiUSIIL's original values.
"""

import re
import math
import os
from urllib.parse import urlparse

import joblib
from rapidfuzz import process, fuzz

# ---- Load reference artifacts built from training data ----
_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "saved_models")

_tld_legit_prob = joblib.load(os.path.join(_MODEL_DIR, "tld_legit_prob.pkl"))
_overall_legit_rate = joblib.load(os.path.join(_MODEL_DIR, "overall_legit_rate.pkl"))
_char_prob_table = joblib.load(os.path.join(_MODEL_DIR, "char_prob_table.pkl"))
_reference_domains = joblib.load(os.path.join(_MODEL_DIR, "reference_domains.pkl"))

_SHORTENERS = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd",
    "buff.ly", "adf.ly", "shorte.st", "rebrand.ly"
}

_SPECIAL_CHARS = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")


def _get_tld(hostname: str) -> str:
    """Extract the top-level domain from a hostname (simple suffix split)."""
    if not hostname:
        return ""
    parts = hostname.split(".")
    return parts[-1] if len(parts) > 1 else ""


def _char_continuation_rate(url: str) -> float:
    """
    Longest run of same-type characters (letters, digits, or special chars)
    divided by URL length — higher means more "blocky" repetition,
    which can indicate obfuscation.
    """
    if not url:
        return 0.0

    def char_type(c):
        if c.isalpha():
            return "letter"
        if c.isdigit():
            return "digit"
        return "special"

    max_run = 1
    current_run = 1
    for i in range(1, len(url)):
        if char_type(url[i]) == char_type(url[i - 1]):
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1

    return max_run / len(url)


def _url_char_prob(url: str) -> float:
    """
    Average probability of this URL's characters occurring in known
    legitimate URLs (from the training-derived char_prob_table).
    Lower values mean more "unusual" character composition.
    """
    if not url:
        return 0.0
    probs = [_char_prob_table.get(c, 1e-6) for c in url.lower()]
    return sum(probs) / len(probs)


def _url_similarity_index(hostname: str) -> float:
    """
    Approximation of URLSimilarityIndex: best fuzzy-match score (0-100)
    between this hostname and a sample of known-legitimate domains.
    See module docstring for the caveat on this being an approximation.
    """
    if not hostname or not _reference_domains:
        return 0.0
    match = process.extractOne(hostname, _reference_domains, scorer=fuzz.ratio)
    return float(match[1]) if match else 0.0


def extract_lexical_features(url: str) -> dict:
    """
    Compute the 22 URL-derived features for a single raw URL string.
    Returns a dict keyed by the exact feature names the model expects.
    """
    url = url.strip()
    parsed = urlparse(url if "://" in url else f"http://{url}")
    hostname = parsed.netloc.split(":")[0].lower()
    tld = _get_tld(hostname)

    is_domain_ip = bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname))

    letters = sum(c.isalpha() for c in url)
    digits = sum(c.isdigit() for c in url)
    equals = url.count("=")
    qmarks = url.count("?")
    ampersands = url.count("&")
    special_chars = sum(1 for c in url if c in _SPECIAL_CHARS)
    other_special = special_chars - equals - qmarks - ampersands

    subdomain_count = max(hostname.count(".") - 1, 0) if hostname else 0

    url_len = len(url) if url else 1  # avoid div-by-zero

    features = {
        "URLLength": len(url),
        "DomainLength": len(hostname),
        "IsDomainIP": int(is_domain_ip),
        "URLSimilarityIndex": _url_similarity_index(hostname),
        "CharContinuationRate": _char_continuation_rate(url),
        "TLDLegitimateProb": _tld_legit_prob.get(tld, _overall_legit_rate),
        "URLCharProb": _url_char_prob(url),
        "TLDLength": len(tld),
        "NoOfSubDomain": subdomain_count,
        "HasObfuscation": int(bool(re.search(r"%[0-9a-fA-F]{2}", url))),
        "NoOfObfuscatedChar": len(re.findall(r"%[0-9a-fA-F]{2}", url)),
        "ObfuscationRatio": len(re.findall(r"%[0-9a-fA-F]{2}", url)) / url_len,
        "NoOfLettersInURL": letters,
        "LetterRatioInURL": letters / url_len,
        "NoOfDegitsInURL": digits,
        "DegitRatioInURL": digits / url_len,
        "NoOfEqualsInURL": equals,
        "NoOfQMarkInURL": qmarks,
        "NoOfAmpersandInURL": ampersands,
        "NoOfOtherSpecialCharsInURL": max(other_special, 0),
        "SpacialCharRatioInURL": special_chars / url_len,
        "IsHTTPS": int(parsed.scheme == "https"),
    }

    return features


def is_shortened_url(hostname: str) -> bool:
    """Helper (not a model feature) — flags known URL-shortener domains."""
    return hostname.lower() in _SHORTENERS


if __name__ == "__main__":
    test_urls = [
        "https://www.google.com",
        "http://paypal-secure-login.verify-account.tk/update?user=123&id=456",
        "https://bit.ly/3xample",
        "http://192.168.1.1/admin/login.php",
    ]
    for u in test_urls:
        print(f"\nURL: {u}")
        feats = extract_lexical_features(u)
        for k, v in feats.items():
            print(f"  {k}: {v}")
>>>>>>> 0c7780d4cf59b81c6ec4b7b2846c4af79c85dc34
