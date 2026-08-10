"""Tests for the manually maintained source catalog."""

from pathlib import Path

import pytest

from jobagent.core.exceptions import ConfigurationError
from jobagent.crawlers.catalog import load_source_catalog

CATALOG_PATH = Path(__file__).parents[2] / "config" / "source_catalog.toml"


def test_repository_catalog_is_valid_and_has_required_coverage() -> None:
    catalog = load_source_catalog(CATALOG_PATH)

    assert {entry.category for entry in catalog.entries} == {
        "campus",
        "public_exam",
        "state_owned",
    }
    public_exam_regions = {
        region
        for entry in catalog.entries
        if entry.category == "public_exam"
        for region in entry.regions
    }
    assert {"jiangsu", "zhejiang", "shanghai"} <= public_exam_regions
    assert [entry.key for entry in catalog.runnable_entries()] == [
        "sasac-recruitment",
        "jiangsu-personnel-exam",
    ]
    assert catalog.get("sasac-recruitment").include_keywords


def test_catalog_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "sources.toml"
    path.write_text(
        """
[[sources]]
key = "same"
name = "One"
official_owner = "Owner"
category = "campus"
regions = ["national"]
base_url = "https://example.invalid/"
list_url = "https://example.invalid/list"
adapter = "one"
implementation_status = "active"
enabled = true
crawl_interval_minutes = 60

[[sources]]
key = "same"
name = "Two"
official_owner = "Owner"
category = "campus"
regions = ["national"]
base_url = "https://example.invalid/"
list_url = "https://example.invalid/list2"
adapter = "two"
implementation_status = "planned"
enabled = false
crawl_interval_minutes = 60
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="duplicate key") as raised:
        load_source_catalog(path)

    assert raised.value.code == "crawler.catalog_duplicate"


def test_catalog_rejects_enabled_planned_source(tmp_path: Path) -> None:
    path = tmp_path / "sources.toml"
    path.write_text(
        """
[[sources]]
key = "planned"
name = "Planned"
official_owner = "Owner"
category = "state_owned"
regions = ["national"]
base_url = "https://example.invalid/"
list_url = "https://example.invalid/list"
adapter = "planned"
implementation_status = "planned"
enabled = true
crawl_interval_minutes = 60
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="cannot be enabled") as raised:
        load_source_catalog(path)

    assert raised.value.code == "crawler.catalog_entry_invalid"
