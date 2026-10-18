import pytest

from app.database import Store
from app.skills.compare import compare
from app.skills.source_reader import canonical_url, normalize, publication_date


def observation(**kw):
    return dict(metric="vacancy_rate", geography="City", period="2026Q1", value=7.2,
                unit="percent", definition="overall vacancy", publisher="Fixture",
                review_status="APPROVED", **kw)


def test_percent_points_and_relative_change():
    old = observation()
    new = old | {"period": "2026Q2", "value": 7.0}
    result = compare(old, new)
    assert result["status"] == "COMPARABLE"
    assert result["delta"] == pytest.approx(-0.2)
    assert result["delta_unit"] == "percentage points"
    assert result["relative_percent"] == pytest.approx(-2.7777777)


@pytest.mark.parametrize("field,value", [("period", "2026H1"), ("period", "2026Q1"),
    ("unit", "sq ft"), ("geography", "West End"), ("definition", "Grade A vacancy"),
    ("publisher", "Other"), ("review_status", "PENDING_REVIEW")])
def test_incompatible_or_unapproved_is_refused(field, value):
    old = observation()
    new = old | {"period": "2026Q2", "value": 7.0, field: value}
    assert compare(old, new)["status"] == "NOT_COMPARABLE"


def test_store_persists_settings(tmp_path):
    path = tmp_path / "test.sqlite3"
    Store(path).set_setting("focus", ["City"])
    assert Store(path).setting("focus") == ["City"]


def test_canonical_and_normalized_content():
    assert canonical_url("https://example.org/a?utm_source=x#z") == "https://example.org/a"
    assert normalize("  Hello\n  World ") == "Hello World"


def test_publication_date_uses_article_header_not_related_story_date():
    html = '<time class="sv-content-header__date" datetime="2026-08-06">06 August 2026</time><aside>01 October 2026</aside>'
    assert publication_date(html, "2026-10-01") == "2026-08-06"
