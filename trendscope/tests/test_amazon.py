"""Amazon: búsqueda por tema, estrellas, reseñas y captcha."""

from unittest.mock import MagicMock, patch

from scrapling.parser import Selector

from trendscope.analyzer.scorer import _score_by_source
from trendscope.core.query import TrendQuery
from trendscope.scrapers import amazon

SEARCH_HTML = """
<html><body>
<div data-asin="B01" data-component-type="s-search-result">
  <h2><a href="/dp/B01"><span>Apple AirPods Pro (2nd Gen)</span></a></h2>
  <span class="a-icon-alt">4.7 out of 5 stars</span>
  <a href="/dp/B01#customerReviews"><span>12,345</span></a>
  <span class="a-price"><span class="a-offscreen">$199.00</span></span>
</div>
<div data-asin="B02" data-component-type="s-search-result">
  <span class="puis-sponsored-label-text">Sponsored</span>
  <h2><span>Anuncio patrocinado</span></h2>
</div>
<div data-asin="B03" data-component-type="s-search-result">
  <h2><span>Audífonos genéricos</span></h2>
  <span class="a-icon-alt">3,2 de 5 estrellas</span>
  <span class="s-underline-text">(1.2K)</span>
</div>
</body></html>
"""


def test_build_url_uses_country_store_and_topic():
    url, mode = amazon.build_url(TrendQuery(mode="free", free_topic="audífonos bluetooth", geo="MX"))
    assert mode == "search" and url.startswith("https://www.amazon.com.mx/s?k=aud")
    url, _ = amazon.build_url(TrendQuery(mode="free", free_topic="x", geo="CO"))
    assert url.startswith("https://www.amazon.com/")  # sin tienda propia → .com
    url, mode = amazon.build_url(TrendQuery(mode="category", category="tecnologia", geo="ES"))
    assert mode == "bestsellers" and url == "https://www.amazon.es/gp/bestsellers/electronics/"


def test_parse_search_ratings_reviews_and_skips_ads():
    items = amazon.parse_search(Selector(SEARCH_HTML), "https://www.amazon.com/s?k=airpods")
    assert [i["asin"] for i in items] == ["B01", "B03"]
    first = items[0]
    assert first["rating"] == 4.7 and first["reviews"] == 12345
    assert first["price"] == "$199.00" and first["url"] == "https://www.amazon.com/dp/B01"
    assert items[1]["rating"] == 3.2 and items[1]["reviews"] == 1200


def test_parse_rating_locales():
    assert amazon.parse_rating("4,5 von 5 Sternen") == 4.5
    assert amazon.parse_rating("5つ星のうち4.3") == 4.3
    assert amazon.parse_rating("") is None


def test_captcha_falls_back_to_browser():
    blocked = MagicMock(status=503, html_content="Type the characters... captcha")
    ok = Selector(SEARCH_HTML)
    fetcher, stealthy = MagicMock(), MagicMock()
    fetcher.get.return_value = blocked
    stealthy.fetch.return_value = ok
    with patch.dict("sys.modules", {"scrapling.fetchers": MagicMock(Fetcher=fetcher, StealthyFetcher=stealthy)}):
        page = amazon._fetch_page("https://www.amazon.com/s?k=x", "en-US")
    stealthy.fetch.assert_called_once()
    assert "auto_match" not in stealthy.fetch.call_args.kwargs  # removido en Scrapling 0.3+
    assert page is ok


def test_amazon_score_rewards_reviews_and_stars():
    good = _score_by_source({"source": "amazon", "reviews": 20000, "rating": 4.8})
    bad = _score_by_source({"source": "amazon", "reviews": 20000, "rating": 2.0})
    few = _score_by_source({"source": "amazon", "reviews": 3, "rating": 4.8})
    assert good > bad and good > few
