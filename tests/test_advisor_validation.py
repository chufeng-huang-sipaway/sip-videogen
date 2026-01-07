"""Tests for reference image validation in Brand Advisor."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sip_studio.advisor.validation import (
    ReferenceValidationResult,
    ValidationAttempt,
    _improve_prompt_for_identity,
    generate_with_validation,
    validate_reference_identity,
)


class TestReferenceValidationResult:
    """Tests for ReferenceValidationResult model."""

    def test_valid_result_accepts_score_in_range(self):
        """Test that valid similarity scores are accepted."""
        result = ReferenceValidationResult(
            is_identical=True,
            similarity_score=0.95,
            reasoning="Objects match perfectly",
            improvement_suggestions="",
        )
        assert result.similarity_score == 0.95
        assert result.is_identical is True

    def test_score_validation_rejects_out_of_range(self):
        """Test that scores outside 0-1 range are rejected."""
        with pytest.raises(ValueError):
            ReferenceValidationResult(
                is_identical=False,
                similarity_score=1.5,  # Invalid
                reasoning="Test",
            )

        with pytest.raises(ValueError):
            ReferenceValidationResult(
                is_identical=False,
                similarity_score=-0.1,  # Invalid
                reasoning="Test",
            )


class TestValidateReferenceIdentity:
    """Tests for validate_reference_identity function."""

    @pytest.mark.asyncio
    async def test_validation_accepts_identical_images(self):
        """Test that validator accepts when images are identical."""
        mock_result = ReferenceValidationResult(
            is_identical=True,
            similarity_score=0.95,
            reasoning="Objects are identical - same product with matching features",
            improvement_suggestions="",
        )

        with patch("agents.Runner") as mock_runner:
            mock_runner.run = AsyncMock(return_value=MagicMock(final_output=mock_result))

            result = await validate_reference_identity(
                reference_image_bytes=b"fake_ref_bytes",
                generated_image_bytes=b"fake_gen_bytes",
                original_prompt="Test prompt",
            )

        assert result.is_identical is True
        assert result.similarity_score >= 0.9

    @pytest.mark.asyncio
    async def test_validation_rejects_different_objects(self):
        """Test that validator rejects when objects differ."""
        mock_result = ReferenceValidationResult(
            is_identical=False,
            similarity_score=0.4,
            reasoning="Objects are different products - different brand logo",
            improvement_suggestions="Emphasize the exact brand logo placement and text",
        )

        with patch("agents.Runner") as mock_runner:
            mock_runner.run = AsyncMock(return_value=MagicMock(final_output=mock_result))

            result = await validate_reference_identity(
                reference_image_bytes=b"fake_ref_bytes",
                generated_image_bytes=b"fake_gen_bytes",
                original_prompt="Test prompt",
            )

        assert result.is_identical is False
        assert result.similarity_score < 0.8
        assert len(result.improvement_suggestions) > 0

    @pytest.mark.asyncio
    async def test_validation_creates_proper_agent(self):
        """Test that validator creates GPT-4o agent with correct config."""
        mock_result = ReferenceValidationResult(
            is_identical=True,
            similarity_score=0.9,
            reasoning="Match",
            improvement_suggestions="",
        )

        with patch("agents.Agent") as mock_agent_class, patch("agents.Runner") as mock_runner:
            mock_runner.run = AsyncMock(return_value=MagicMock(final_output=mock_result))

            await validate_reference_identity(
                reference_image_bytes=b"fake_ref_bytes",
                generated_image_bytes=b"fake_gen_bytes",
                original_prompt="Test prompt",
            )

            # Verify agent was created with GPT-4o
            mock_agent_class.assert_called_once()
            call_kwargs = mock_agent_class.call_args[1]
            assert call_kwargs["model"] == "gpt-4o"
            assert call_kwargs["output_type"] == ReferenceValidationResult


class TestGenerateWithValidation:
    """Tests for generate_with_validation function."""

    @pytest.fixture
    def mock_gemini_client(self):
        """Create a mock Gemini client that produces fake image bytes."""
        from PIL import Image as PILImage

        mock_client = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data = True

        # Create a real small PNG image for the mock
        mock_image = PILImage.new("RGB", (10, 10), color="red")

        mock_part.as_image.return_value = mock_image
        mock_client.models.generate_content.return_value = MagicMock(parts=[mock_part])
        return mock_client

    @pytest.fixture
    def fake_reference_image(self):
        """Create fake reference image bytes."""
        import io

        from PIL import Image as PILImage

        img = PILImage.new("RGB", (10, 10), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(
        self, tmp_path: Path, mock_gemini_client, fake_reference_image
    ):
        """Test successful generation on first attempt."""
        mock_validation = ReferenceValidationResult(
            is_identical=True,
            similarity_score=0.92,
            reasoning="Match",
            improvement_suggestions="",
        )

        with patch(
            "sip_studio.advisor.validation.generator.validate_reference_identity",
            return_value=mock_validation,
        ):
            result = await generate_with_validation(
                client=mock_gemini_client,
                prompt="Test prompt",
                reference_image_bytes=fake_reference_image,
                output_dir=tmp_path,
                filename="test_output",
                max_retries=3,
            )

        assert result.path.endswith("test_output.png")
        assert result.warning is None

    @pytest.mark.asyncio
    async def test_retries_on_validation_failure(
        self, tmp_path: Path, mock_gemini_client, fake_reference_image
    ):
        """Test retry logic when validation fails."""
        # First attempt fails, second succeeds
        validations = [
            ReferenceValidationResult(
                is_identical=False,
                similarity_score=0.5,
                reasoning="Different",
                improvement_suggestions="Add more detail about the logo",
            ),
            ReferenceValidationResult(
                is_identical=True,
                similarity_score=0.9,
                reasoning="Match",
                improvement_suggestions="",
            ),
        ]

        call_count = [0]

        async def mock_validate(*args, **kwargs):
            result = validations[min(call_count[0], len(validations) - 1)]
            call_count[0] += 1
            return result

        with patch(
            "sip_studio.advisor.validation.generator.validate_reference_identity",
            side_effect=mock_validate,
        ):
            result = await generate_with_validation(
                client=mock_gemini_client,
                prompt="Test prompt",
                reference_image_bytes=fake_reference_image,
                output_dir=tmp_path,
                filename="test_output",
                max_retries=3,
            )

        assert call_count[0] == 2  # Two validation calls
        assert result.path.endswith("test_output.png")
        assert result.warning is None

    @pytest.mark.asyncio
    async def test_returns_best_attempt_on_exhaustion(
        self, tmp_path: Path, mock_gemini_client, fake_reference_image
    ):
        """Test fallback to best attempt when all retries fail."""
        # All attempts fail with varying scores
        mock_validation = ReferenceValidationResult(
            is_identical=False,
            similarity_score=0.6,
            reasoning="Not quite matching",
            improvement_suggestions="Try emphasizing the shape",
        )

        with patch(
            "sip_studio.advisor.validation.generator.validate_reference_identity",
            return_value=mock_validation,
        ):
            result = await generate_with_validation(
                client=mock_gemini_client,
                prompt="Test prompt",
                reference_image_bytes=fake_reference_image,
                output_dir=tmp_path,
                filename="test_output",
                max_retries=3,
            )

        assert result.warning is not None
        assert "0.6" in result.warning  # Similarity score mentioned

    @pytest.mark.asyncio
    async def test_tracks_best_attempt_across_retries(
        self, tmp_path: Path, mock_gemini_client, fake_reference_image
    ):
        """Test that best attempt is tracked when scores vary."""
        # Scores: 0.5, 0.7, 0.6 - should keep attempt with 0.7
        validations = [
            ReferenceValidationResult(
                is_identical=False,
                similarity_score=0.5,
                reasoning="Poor match",
                improvement_suggestions="Fix colors",
            ),
            ReferenceValidationResult(
                is_identical=False,
                similarity_score=0.7,
                reasoning="Better but not identical",
                improvement_suggestions="Fix logo",
            ),
            ReferenceValidationResult(
                is_identical=False,
                similarity_score=0.6,
                reasoning="Worse than before",
                improvement_suggestions="Start over",
            ),
        ]

        call_count = [0]

        async def mock_validate(*args, **kwargs):
            result = validations[min(call_count[0], len(validations) - 1)]
            call_count[0] += 1
            return result

        with patch(
            "sip_studio.advisor.validation.generator.validate_reference_identity",
            side_effect=mock_validate,
        ):
            result = await generate_with_validation(
                client=mock_gemini_client,
                prompt="Test prompt",
                reference_image_bytes=fake_reference_image,
                output_dir=tmp_path,
                filename="test_output",
                max_retries=3,
            )

        # Should report the best score (0.7)
        assert result.warning is not None
        assert "0.7" in result.warning

    @pytest.mark.asyncio
    async def test_handles_generation_errors_gracefully(self, tmp_path: Path, fake_reference_image):
        """Test handling when image generation fails."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")

        result = await generate_with_validation(
            client=mock_client,
            prompt="Test prompt",
            reference_image_bytes=fake_reference_image,
            output_dir=tmp_path,
            filename="test_output",
            max_retries=2,
        )

        assert "Error" in result or "failed" in result.lower()


class TestImprovePromptForIdentity:
    """Tests for _improve_prompt_for_identity function."""

    def test_adds_identity_requirements(self):
        """Test that identity requirements are added to prompt."""
        improved = _improve_prompt_for_identity(
            original_prompt="A coffee bag on a table",
            suggestions="",
            attempt_number=1,
        )

        assert "CRITICAL" in improved
        assert "EXACT SAME object" in improved
        assert "IDENTITY REQUIREMENT" in improved
        assert "Attempt 2" in improved

    def test_incorporates_suggestions(self):
        """Test that validator suggestions are incorporated."""
        improved = _improve_prompt_for_identity(
            original_prompt="A coffee bag",
            suggestions="The logo text is wrong - should say 'SUMMIT'",
            attempt_number=2,
        )

        assert "SUMMIT" in improved
        assert "Specific feedback" in improved

    def test_preserves_original_prompt(self):
        """Test that original prompt is preserved."""
        original = "A premium coffee bag with artisan branding"
        improved = _improve_prompt_for_identity(
            original_prompt=original,
            suggestions="Add more detail",
            attempt_number=1,
        )

        assert original in improved


class TestValidationAttempt:
    """Tests for ValidationAttempt dataclass."""

    def test_creates_valid_attempt(self):
        """Test creating a validation attempt record."""
        attempt = ValidationAttempt(
            attempt_number=1,
            prompt_used="Test prompt",
            image_path="/path/to/image.png",
            similarity_score=0.85,
            is_identical=True,
            improvement_suggestions="",
        )

        assert attempt.attempt_number == 1
        assert attempt.similarity_score == 0.85
        assert attempt.is_identical is True
