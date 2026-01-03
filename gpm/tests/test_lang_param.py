"""
Test script để kiểm tra _with_lang_param function
"""
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def _with_lang_param(url: str, lang: str = "en") -> str:
    """Add/replace ?lang=en (or keep existing params)."""
    try:
        p = urlparse(url)
        q = parse_qs(p.query)
        q["lang"] = [lang]
        new_query = urlencode(q, doseq=True)
        return urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))
    except Exception:
        return url

if __name__ == "__main__":
    # Test cases
    test_urls = [
        "https://www.tiktok.com/foryou",
        "https://www.tiktok.com/@username",
        "https://www.tiktok.com/foryou?sort=trending",
        "https://www.tiktok.com/@user/video/123456?lang=vi",
        "https://www.tiktok.com/search?q=test&from=explore",
    ]

    print("🧪 Testing _with_lang_param function:\n")
    for url in test_urls:
        result = _with_lang_param(url)
        print(f"Original:  {url}")
        print(f"With lang: {result}")
        print()

    print("✅ All tests completed!")
