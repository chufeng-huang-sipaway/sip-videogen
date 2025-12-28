"""Tests for ImageProductionManager skip_review functionality."""
from pathlib import Path
from unittest.mock import AsyncMock,MagicMock,patch
import pytest
from sip_videogen.agents.tools.image_production import ImageProductionManager
from sip_videogen.generators.image_generator import ImageGenerationError
from sip_videogen.models.assets import AssetType,GeneratedAsset
from sip_videogen.models.image_review import ImageGenerationResult
from sip_videogen.models.script import SharedElement
class TestSkipReview:
    """Tests for skip_review functionality in ImageProductionManager."""
    @pytest.fixture
    def mock_generator(self):
        """Create mock ImageGenerator."""
        mock_asset=GeneratedAsset(asset_type=AssetType.REFERENCE_IMAGE,element_id="test_element",local_path="/tmp/test.png")
        with patch("sip_videogen.agents.tools.image_production.ImageGenerator") as MockGen:
            instance=MockGen.return_value
            instance.generate_reference_image=AsyncMock(return_value=mock_asset)
            instance._get_aspect_ratio_for_element=MagicMock(return_value="1:1")
            yield instance
    @pytest.mark.asyncio
    async def test_skip_review_returns_unreviewed_status(self,sample_shared_element:SharedElement,tmp_path:Path,mock_generator):
        """Test that skip_review=True returns 'unreviewed' status."""
        manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
        manager.generator=mock_generator
        result=await manager.generate_with_review(sample_shared_element,skip_review=True)
        assert result.status=="unreviewed"
        assert result.element_id==sample_shared_element.id
        assert result.local_path=="/tmp/test.png"
        assert len(result.attempts)==1
        assert result.attempts[0].outcome=="success"
    @pytest.mark.asyncio
    async def test_skip_review_bypasses_reviewer(self,sample_shared_element:SharedElement,tmp_path:Path,mock_generator):
        """Test that skip_review=True does not call review_image."""
        manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
        manager.generator=mock_generator
        with patch("sip_videogen.agents.tools.image_production.review_image") as mock_review:
            await manager.generate_with_review(sample_shared_element,skip_review=True)
            mock_review.assert_not_called()
    @pytest.mark.asyncio
    async def test_skip_review_handles_generation_error(self,sample_shared_element:SharedElement,tmp_path:Path):
        """Test that skip_review mode handles generation errors gracefully."""
        with patch("sip_videogen.agents.tools.image_production.ImageGenerator") as MockGen:
            instance=MockGen.return_value
            instance.generate_reference_image=AsyncMock(side_effect=ImageGenerationError("API Error"))
            instance._get_aspect_ratio_for_element=MagicMock(return_value="1:1")
            manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
            manager.generator=instance
            result=await manager.generate_with_review(sample_shared_element,skip_review=True)
            assert result.status=="failed"
            assert result.element_id==sample_shared_element.id
            assert result.local_path==""
            assert len(result.attempts)==1
            assert result.attempts[0].outcome=="error"
            assert "API Error" in result.attempts[0].error_message
    @pytest.mark.asyncio
    async def test_parallel_skip_review(self,sample_shared_element:SharedElement,sample_environment_element:SharedElement,tmp_path:Path):
        """Test that parallel generation with skip_review works correctly."""
        with patch("sip_videogen.agents.tools.image_production.ImageGenerator") as MockGen:
            call_count=0
            async def mock_gen(element,output_dir,aspect_ratio=None):
                nonlocal call_count
                call_count+=1
                return GeneratedAsset(asset_type=AssetType.REFERENCE_IMAGE,element_id=element.id,local_path=f"/tmp/test_{call_count}.png")
            instance=MockGen.return_value
            instance.generate_reference_image=mock_gen
            instance._get_aspect_ratio_for_element=MagicMock(return_value="1:1")
            manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
            manager.generator=instance
            elements=[sample_shared_element,sample_environment_element]
            results=await manager.generate_all_with_review_parallel(elements,skip_review=True)
            assert len(results)==2
            assert all(r.status=="unreviewed" for r in results)
            assert results[0].element_id==sample_shared_element.id
            assert results[1].element_id==sample_environment_element.id
    @pytest.mark.asyncio
    async def test_default_skip_review_is_false(self,sample_shared_element:SharedElement,tmp_path:Path):
        """Test that skip_review defaults to False (normal review flow)."""
        #Create a real temp file for the test
        test_img=tmp_path/"test.png"
        test_img.write_bytes(b"fake png data")
        mock_asset=GeneratedAsset(asset_type=AssetType.REFERENCE_IMAGE,element_id="test_element",local_path=str(test_img))
        with patch("sip_videogen.agents.tools.image_production.ImageGenerator") as MockGen:
            instance=MockGen.return_value
            instance.generate_reference_image=AsyncMock(return_value=mock_asset)
            instance._get_aspect_ratio_for_element=MagicMock(return_value="1:1")
            with patch("sip_videogen.agents.tools.image_production.review_image") as mock_review:
                from sip_videogen.models.image_review import ImageReviewResult,ReviewDecision
                mock_review.return_value=ImageReviewResult(decision=ReviewDecision.ACCEPT,element_id="test",reasoning="Looks good")
                manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
                manager.generator=instance
                result=await manager.generate_with_review(sample_shared_element)
                #Default behavior should call the reviewer
                mock_review.assert_called_once()
                assert result.status=="success"
class TestUnreviewedStatusInModel:
    """Tests for 'unreviewed' status in ImageGenerationResult model."""
    def test_unreviewed_status_is_valid(self):
        """Test that 'unreviewed' is a valid status in ImageGenerationResult."""
        result=ImageGenerationResult(element_id="test",status="unreviewed",local_path="/tmp/test.png",attempts=[],final_prompt="test prompt")
        assert result.status=="unreviewed"
    def test_all_statuses_are_valid(self):
        """Test that all expected statuses are valid."""
        for status in ["success","fallback","failed","unreviewed"]:
            result=ImageGenerationResult(element_id="test",status=status,local_path="/tmp/test.png" if status!="failed" else "",attempts=[],final_prompt="test")
            assert result.status==status
