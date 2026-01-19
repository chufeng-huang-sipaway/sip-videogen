"""Tests for brand creation from website models."""

from __future__ import annotations

import json
from datetime import timezone

import pytest

from sip_studio.brands.research.models import (
    VALID_STATES,
    BrandCreationJob,
    BrandResearchBundle,
    ResearchCompleteness,
    WebsiteAssets,
)


class TestWebsiteAssets:
    def test_defaults(self):
        a = WebsiteAssets()
        assert a.colors == []
        assert a.meta_description == ""
        assert a.headlines == []
        assert a.logo_candidates == []

    def test_with_values(self):
        a = WebsiteAssets(
            colors=["#FF0000", "#00FF00"],
            meta_description="A great brand",
            og_title="Brand Name",
            headlines=["Welcome", "About Us"],
            logo_candidates=["https://example.com/logo.png"],
        )
        assert len(a.colors) == 2
        assert a.og_title == "Brand Name"
        assert len(a.headlines) == 2

    def test_json_roundtrip(self):
        a = WebsiteAssets(colors=["#123456"], meta_description="Test", theme_color="#FFFFFF")
        d = a.model_dump()
        a2 = WebsiteAssets.model_validate(d)
        assert a2.colors == a.colors
        assert a2.meta_description == a.meta_description


class TestResearchCompleteness:
    def test_valid_confidence(self):
        c = ResearchCompleteness(confidence=0.8, is_complete=True)
        assert c.confidence == 0.8
        assert c.is_complete

    def test_confidence_bounds(self):
        with pytest.raises(ValueError):
            ResearchCompleteness(confidence=1.5, is_complete=True)
        with pytest.raises(ValueError):
            ResearchCompleteness(confidence=-0.1, is_complete=False)

    def test_with_gaps(self):
        c = ResearchCompleteness(
            confidence=0.5,
            is_complete=False,
            missing_aspects=["color palette", "typography"],
            suggested_queries=["brand colors", "font usage"],
        )
        assert len(c.missing_aspects) == 2
        assert len(c.suggested_queries) == 2


class TestBrandResearchBundle:
    def test_minimal(self):
        b = BrandResearchBundle(brand_name="TestBrand", website_url="https://test.com")
        assert b.brand_name == "TestBrand"
        assert b.deep_research_summary == ""
        assert b.website_assets is None

    def test_with_assets(self):
        assets = WebsiteAssets(colors=["#000"])
        comp = ResearchCompleteness(confidence=0.9, is_complete=True)
        b = BrandResearchBundle(
            brand_name="Test", website_url="https://x.com", website_assets=assets, completeness=comp
        )
        assert b.website_assets is not None
        assert b.completeness is not None
        assert b.completeness.confidence == 0.9


class TestBrandCreationJob:
    def test_defaults(self):
        j = BrandCreationJob(
            job_id="job-1", brand_name="Test", website_url="https://test.com", slug="test"
        )
        assert j.status == "pending"
        assert j.phase == "starting"
        assert j.percent_complete == 0
        assert j.error is None
        assert j.cancel_requested is False
        assert j.schema_version == 1

    def test_validate_state_valid(self):
        j = BrandCreationJob(
            job_id="j1",
            brand_name="T",
            website_url="https://t.com",
            slug="t",
            status="running",
            phase="researching",
        )
        assert j.validate_state()

    def test_validate_state_invalid(self):
        j = BrandCreationJob(
            job_id="j1",
            brand_name="T",
            website_url="https://t.com",
            slug="t",
            status="pending",
            phase="creating",
        )
        assert not j.validate_state()

    def test_all_valid_states(self):
        for status, phase in VALID_STATES:
            j = BrandCreationJob(
                job_id="j",
                brand_name="T",
                website_url="https://t.com",
                slug="t",
                status=status,
                phase=phase,
            )
            assert j.validate_state(), f"({status},{phase}) should be valid"

    def test_percent_bounds(self):
        with pytest.raises(ValueError):
            BrandCreationJob(
                job_id="j",
                brand_name="T",
                website_url="https://t.com",
                slug="t",
                percent_complete=101,
            )
        with pytest.raises(ValueError):
            BrandCreationJob(
                job_id="j",
                brand_name="T",
                website_url="https://t.com",
                slug="t",
                percent_complete=-1,
            )

    def test_json_roundtrip(self):
        j = BrandCreationJob(
            job_id="job-123",
            brand_name="Acme",
            website_url="https://acme.com",
            slug="acme",
            status="running",
            phase="researching",
            percent_complete=50,
            phase_detail="Analyzing website",
        )
        d = j.to_json_dict()
        # Verify datetime serialized as string
        assert isinstance(d["created_at"], str)
        assert isinstance(d["updated_at"], str)
        # Roundtrip
        j2 = BrandCreationJob.from_json_dict(d)
        assert j2.job_id == j.job_id
        assert j2.brand_name == j.brand_name
        assert j2.status == j.status
        assert j2.phase == j.phase

    def test_json_file_roundtrip(self, tmp_path):
        """Test writing to file and reading back (schema migration placeholder)."""
        j = BrandCreationJob(
            job_id="job-file",
            brand_name="FileTest",
            website_url="https://file.test",
            slug="file-test",
        )
        p = tmp_path / "job.json"
        p.write_text(json.dumps(j.to_json_dict()))
        d = json.loads(p.read_text())
        j2 = BrandCreationJob.from_json_dict(d)
        assert j2.job_id == j.job_id
        assert j2.schema_version == 1

    def test_with_error(self):
        j = BrandCreationJob(
            job_id="j",
            brand_name="T",
            website_url="https://t.com",
            slug="t",
            status="failed",
            phase="failed",
            error="Connection timeout",
            error_code="TIMEOUT",
        )
        assert j.error == "Connection timeout"
        assert j.error_code == "TIMEOUT"

    def test_timezone_aware_datetime(self):
        j = BrandCreationJob(job_id="j", brand_name="T", website_url="https://t.com", slug="t")
        assert j.created_at.tzinfo is not None
        assert j.updated_at.tzinfo == timezone.utc
