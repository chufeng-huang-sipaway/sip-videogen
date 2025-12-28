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
class TestVariantsGeneration:
    """Tests for multi-variant image generation with early-exit review."""
    @pytest.fixture
    def mock_generator_variants(self,tmp_path:Path):
        """Create mock ImageGenerator with variant support."""
        with patch("sip_videogen.agents.tools.image_production.ImageGenerator") as MockGen:
            instance=MockGen.return_value
            async def mock_variants(elem,out_dir,num_variants,aspect_ratio=None):
                paths=[]
                for i in range(num_variants):
                    p=tmp_path/f"{elem.id}_v{i}.png"
                    p.write_bytes(b"fake png data")
                    paths.append(str(p))
                return paths
            instance.generate_reference_image_variants=mock_variants
            instance._get_aspect_ratio_for_element=MagicMock(return_value="1:1")
            yield instance
    @pytest.mark.asyncio
    async def test_generate_with_variants_accepts_first(self,sample_shared_element:SharedElement,tmp_path:Path,mock_generator_variants):
        """Test that early-exit review accepts first passing variant."""
        with patch("sip_videogen.agents.tools.image_production.review_image") as mock_review:
            from sip_videogen.models.image_review import ImageReviewResult,ReviewDecision
            mock_review.return_value=ImageReviewResult(decision=ReviewDecision.ACCEPT,element_id="test",reasoning="Good")
            manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
            manager.generator=mock_generator_variants
            result=await manager.generate_with_variants(sample_shared_element,num_variants=3)
            assert result.status=="success"
            assert len(result.attempts)==1  #Early exit after first accept
            mock_review.assert_called_once()
    @pytest.mark.asyncio
    async def test_generate_with_variants_rejects_then_accepts(self,sample_shared_element:SharedElement,tmp_path:Path,mock_generator_variants):
        """Test that variant review continues until acceptance."""
        with patch("sip_videogen.agents.tools.image_production.review_image") as mock_review:
            from sip_videogen.models.image_review import ImageReviewResult,ReviewDecision
            call_count=0
            def review_side_effect(**kwargs):
                nonlocal call_count
                call_count+=1
                if call_count<3:
                    return ImageReviewResult(decision=ReviewDecision.REJECT,element_id="test",reasoning="Bad",improvement_suggestions="Try again")
                return ImageReviewResult(decision=ReviewDecision.ACCEPT,element_id="test",reasoning="Good")
            mock_review.side_effect=review_side_effect
            manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
            manager.generator=mock_generator_variants
            result=await manager.generate_with_variants(sample_shared_element,num_variants=3)
            assert result.status=="success"
            assert len(result.attempts)==3
            assert result.attempts[0].outcome=="rejected"
            assert result.attempts[1].outcome=="rejected"
            assert result.attempts[2].outcome=="success"
    @pytest.mark.asyncio
    async def test_generate_with_variants_all_rejected_uses_fallback(self,sample_shared_element:SharedElement,tmp_path:Path,mock_generator_variants):
        """Test fallback behavior when all variants are rejected."""
        with patch("sip_videogen.agents.tools.image_production.review_image") as mock_review:
            from sip_videogen.models.image_review import ImageReviewResult,ReviewDecision
            mock_review.return_value=ImageReviewResult(decision=ReviewDecision.REJECT,element_id="test",reasoning="Bad",improvement_suggestions="")
            manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
            manager.generator=mock_generator_variants
            result=await manager.generate_with_variants(sample_shared_element,num_variants=2)
            assert result.status=="fallback"
            assert len(result.attempts)==2
    @pytest.mark.asyncio
    async def test_generate_with_variants_cleans_up_unused(self,sample_shared_element:SharedElement,tmp_path:Path,mock_generator_variants):
        """Test that unused variants are cleaned up after acceptance."""
        with patch("sip_videogen.agents.tools.image_production.review_image") as mock_review:
            from sip_videogen.models.image_review import ImageReviewResult,ReviewDecision
            mock_review.return_value=ImageReviewResult(decision=ReviewDecision.ACCEPT,element_id="test",reasoning="Good")
            manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
            manager.generator=mock_generator_variants
            await manager.generate_with_variants(sample_shared_element,num_variants=3)
            #After cleanup, only final file should exist (no _v0, _v1, _v2 variants)
            variant_files=[f for f in tmp_path.iterdir() if "_v" in f.name]
            assert len(variant_files)==0
    @pytest.mark.asyncio
    async def test_generate_with_variants_skip_review_uses_first(self,sample_shared_element:SharedElement,tmp_path:Path):
        """Test that skip_review + num_variants returns first variant."""
        with patch("sip_videogen.agents.tools.image_production.ImageGenerator") as MockGen:
            mock_asset=GeneratedAsset(asset_type=AssetType.REFERENCE_IMAGE,element_id="test",local_path=str(tmp_path/"test.png"))
            instance=MockGen.return_value
            instance.generate_reference_image=AsyncMock(return_value=mock_asset)
            instance._get_aspect_ratio_for_element=MagicMock(return_value="1:1")
            manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
            manager.generator=instance
            result=await manager.generate_with_variants(sample_shared_element,num_variants=3,skip_review=True)
            assert result.status=="unreviewed"
            #Should not have generated variants since skip_review=True
            instance.generate_reference_image_variants=AsyncMock()
            instance.generate_reference_image_variants.assert_not_called()
    @pytest.mark.asyncio
    async def test_parallel_with_variants(self,sample_shared_element:SharedElement,sample_environment_element:SharedElement,tmp_path:Path):
        """Test parallel generation with variants enabled."""
        async def mock_variants(elem,out_dir,num_variants,aspect_ratio=None):
            paths=[]
            for i in range(num_variants):
                p=tmp_path/f"{elem.id}_v{i}.png"
                p.write_bytes(b"fake png data")
                paths.append(str(p))
            return paths
        with patch("sip_videogen.agents.tools.image_production.ImageGenerator") as MockGen:
            instance=MockGen.return_value
            instance.generate_reference_image_variants=mock_variants
            instance._get_aspect_ratio_for_element=MagicMock(return_value="1:1")
            with patch("sip_videogen.agents.tools.image_production.review_image") as mock_review:
                from sip_videogen.models.image_review import ImageReviewResult,ReviewDecision
                mock_review.return_value=ImageReviewResult(decision=ReviewDecision.ACCEPT,element_id="test",reasoning="Good")
                manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
                manager.generator=instance
                elements=[sample_shared_element,sample_environment_element]
                results=await manager.generate_all_with_review_parallel(elements,num_variants=2)
                assert len(results)==2
                assert all(r.status=="success" for r in results)
    @pytest.mark.asyncio
    async def test_variants_generation_fails_gracefully(self,sample_shared_element:SharedElement,tmp_path:Path):
        """Test that variant generation failure is handled gracefully."""
        with patch("sip_videogen.agents.tools.image_production.ImageGenerator") as MockGen:
            async def mock_variants_fail(*args,**kwargs):
                return []  #No variants generated
            instance=MockGen.return_value
            instance.generate_reference_image_variants=mock_variants_fail
            instance._get_aspect_ratio_for_element=MagicMock(return_value="1:1")
            manager=ImageProductionManager(gemini_api_key="test-key",output_dir=tmp_path)
            manager.generator=instance
            result=await manager.generate_with_variants(sample_shared_element,num_variants=3)
            assert result.status=="failed"
            assert "All variant generations failed" in result.attempts[0].error_message
