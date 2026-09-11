"""Path safety: slug sanitization, export containment, report glob injection."""

from pathlib import Path

import pytest

from trendscope.core.paths import safe_data_path, safe_slug


class TestSafeSlug:
    def test_traversal_blocked(self):
        s = safe_slug("../../etc/passwd")
        assert ".." not in s
        assert "/" not in s
        assert "\\" not in s

    def test_glob_metacharacters_stripped(self):
        assert "*" not in safe_slug("*")
        assert "[" not in safe_slug("[a-z]")
        assert "?" not in safe_slug("a?b")

    def test_spaces_and_normalization(self):
        assert safe_slug("crypto Colombia") == "crypto_Colombia"

    def test_empty_returns_general(self):
        assert safe_slug("") == "general"
        assert safe_slug(None) == "general"

    def test_max_len(self):
        assert len(safe_slug("a" * 100)) == 30

    def test_only_illegal_chars_returns_general(self):
        assert safe_slug("../..") == "general"


class TestSafeDataPath:
    def test_normal_filename(self, tmp_path: Path):
        p = safe_data_path(tmp_path, "export_ok.json")
        assert p == (tmp_path / "export_ok.json").resolve()

    def test_rejects_parent_in_filename(self, tmp_path: Path):
        # Path(filename).name strips directories, so ../../x becomes x
        p = safe_data_path(tmp_path, "../../etc/passwd")
        assert p.parent == tmp_path.resolve()

    def test_rejects_empty_name(self, tmp_path: Path):
        with pytest.raises(ValueError):
            safe_data_path(tmp_path, "..")


class TestExportContainment:
    def test_export_json_with_malicious_topic_stays_in_data_dir(self, tmp_path: Path):
        from trendscope.output.exporter import export_json

        payload = {
            "meta": {"query": {"topic": "../../tmp/pwned", "geo": "CO"}},
            "top_trends": [],
        }
        path = export_json(payload, output_dir=tmp_path)
        assert path.resolve().is_relative_to(tmp_path.resolve())
        assert ".." not in path.name

    def test_export_csv_with_malicious_topic(self, tmp_path: Path):
        from trendscope.output.exporter import export_csv

        payload = {
            "meta": {"query": {"topic": "..\\..\\evil", "geo": "CO"}},
            "top_trends": [{"title": "t", "source": "s"}],
        }
        path = export_csv(payload, output_dir=tmp_path)
        assert path.resolve().is_relative_to(tmp_path.resolve())


class TestTopicSlugProperty:
    def test_query_topic_slug_is_safe(self):
        from trendscope.core.query import TrendQuery

        q = TrendQuery(mode="free", free_topic="../../etc/passwd")
        slug = q.topic_slug
        assert ".." not in slug
        assert "/" not in slug
