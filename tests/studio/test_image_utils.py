"""Tests for studio image utilities."""
import base64,pytest
from pathlib import Path
from unittest.mock import patch,MagicMock
from sip_videogen.studio.utils.image_utils import get_image_thumbnail,get_image_full
#=============================================================================
#Fixtures
#=============================================================================
@pytest.fixture
def tmp_brand_dir(tmp_path):
    """Create a temporary brand directory with test images."""
    brand_dir=tmp_path/"test-brand"
    products_dir=brand_dir/"products"/"test-product"/"images"
    products_dir.mkdir(parents=True)
    templates_dir=brand_dir/"templates"/"test-template"/"images"
    templates_dir.mkdir(parents=True)
    return brand_dir
@pytest.fixture
def png_image_data():
    """Minimal valid PNG image (1x1 red pixel)."""
    from PIL import Image
    import io
    img=Image.new("RGB",(1,1),color=(255,0,0))
    buf=io.BytesIO();img.save(buf,format="PNG")
    return buf.getvalue()
@pytest.fixture
def svg_image_data():
    """Minimal valid SVG image."""
    return b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>'
#=============================================================================
#get_image_thumbnail tests
#=============================================================================
class TestGetImageThumbnail:
    """Tests for get_image_thumbnail function."""
    def test_returns_error_for_invalid_prefix(self,tmp_brand_dir):
        """Should return error when path doesn't start with expected prefix."""
        result=get_image_thumbnail(tmp_brand_dir,"wrong/path.png","products")
        assert result["success"]==False
        assert "Path must start with 'products/'"in result["error"]
    def test_returns_error_for_nonexistent_file(self,tmp_brand_dir):
        """Should return error when file doesn't exist."""
        result=get_image_thumbnail(tmp_brand_dir,"products/test-product/images/missing.png","products")
        assert result["success"]==False
        assert "Image not found"in result["error"]
    def test_returns_error_for_directory(self,tmp_brand_dir):
        """Should return error when path is a directory."""
        result=get_image_thumbnail(tmp_brand_dir,"products/test-product/images","products")
        assert result["success"]==False
        assert "Path is not a file"in result["error"]
    def test_returns_error_for_unsupported_type(self,tmp_brand_dir):
        """Should return error for unsupported file types."""
        bad_file=tmp_brand_dir/"products"/"test-product"/"images"/"file.txt"
        bad_file.write_text("not an image")
        result=get_image_thumbnail(tmp_brand_dir,"products/test-product/images/file.txt","products")
        assert result["success"]==False
        assert "Unsupported file type"in result["error"]
    def test_returns_dataurl_for_valid_png(self,tmp_brand_dir,png_image_data):
        """Should return base64 dataUrl for valid PNG."""
        img_file=tmp_brand_dir/"products"/"test-product"/"images"/"test.png"
        img_file.write_bytes(png_image_data)
        result=get_image_thumbnail(tmp_brand_dir,"products/test-product/images/test.png","products")
        assert result["success"]==True
        assert "dataUrl"in result["data"]
        assert result["data"]["dataUrl"].startswith("data:image/png;base64,")
    def test_returns_svg_dataurl_for_svg(self,tmp_brand_dir,svg_image_data):
        """Should return SVG dataUrl without conversion."""
        svg_file=tmp_brand_dir/"products"/"test-product"/"images"/"icon.svg"
        svg_file.write_bytes(svg_image_data)
        result=get_image_thumbnail(tmp_brand_dir,"products/test-product/images/icon.svg","products")
        assert result["success"]==True
        assert result["data"]["dataUrl"].startswith("data:image/svg+xml;base64,")
        #Verify SVG content is preserved
        b64_part=result["data"]["dataUrl"].split(",")[1]
        decoded=base64.b64decode(b64_part)
        assert decoded==svg_image_data
    def test_returns_error_for_corrupt_image(self,tmp_brand_dir):
        """Should return error for corrupt image file."""
        corrupt_file=tmp_brand_dir/"products"/"test-product"/"images"/"corrupt.png"
        corrupt_file.write_bytes(b"not a valid image file")
        result=get_image_thumbnail(tmp_brand_dir,"products/test-product/images/corrupt.png","products")
        assert result["success"]==False
        assert "Cannot decode image file"in result["error"]
    def test_works_with_templates_prefix(self,tmp_brand_dir,png_image_data):
        """Should work with templates prefix."""
        img_file=tmp_brand_dir/"templates"/"test-template"/"images"/"test.png"
        img_file.write_bytes(png_image_data)
        result=get_image_thumbnail(tmp_brand_dir,"templates/test-template/images/test.png","templates")
        assert result["success"]==True
        assert result["data"]["dataUrl"].startswith("data:image/png;base64,")
#=============================================================================
#get_image_full tests
#=============================================================================
class TestGetImageFull:
    """Tests for get_image_full function."""
    def test_returns_error_for_invalid_prefix(self,tmp_brand_dir):
        """Should return error when path doesn't start with expected prefix."""
        result=get_image_full(tmp_brand_dir,"wrong/path.png","products")
        assert result["success"]==False
        assert "Path must start with 'products/'"in result["error"]
    def test_returns_error_for_nonexistent_file(self,tmp_brand_dir):
        """Should return error when file doesn't exist."""
        result=get_image_full(tmp_brand_dir,"products/test-product/images/missing.png","products")
        assert result["success"]==False
        assert "Image not found"in result["error"]
    def test_returns_error_for_directory(self,tmp_brand_dir):
        """Should return error when path is a directory."""
        result=get_image_full(tmp_brand_dir,"products/test-product/images","products")
        assert result["success"]==False
        assert "Path is not a file"in result["error"]
    def test_returns_original_png(self,tmp_brand_dir,png_image_data):
        """Should return original PNG without conversion."""
        img_file=tmp_brand_dir/"products"/"test-product"/"images"/"test.png"
        img_file.write_bytes(png_image_data)
        result=get_image_full(tmp_brand_dir,"products/test-product/images/test.png","products")
        assert result["success"]==True
        assert result["data"]["dataUrl"].startswith("data:image/png;base64,")
        #Verify original content is preserved
        b64_part=result["data"]["dataUrl"].split(",")[1]
        decoded=base64.b64decode(b64_part)
        assert decoded==png_image_data
    def test_returns_svg_with_correct_mime(self,tmp_brand_dir,svg_image_data):
        """Should return SVG with correct MIME type."""
        svg_file=tmp_brand_dir/"templates"/"test-template"/"images"/"icon.svg"
        svg_file.write_bytes(svg_image_data)
        result=get_image_full(tmp_brand_dir,"templates/test-template/images/icon.svg","templates")
        assert result["success"]==True
        assert result["data"]["dataUrl"].startswith("data:image/svg+xml;base64,")
    def test_returns_jpeg_with_correct_mime(self,tmp_brand_dir):
        """Should return JPEG with correct MIME type."""
        #Minimal JPEG header
        jpeg_data=bytes([0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01])
        jpg_file=tmp_brand_dir/"products"/"test-product"/"images"/"photo.jpg"
        jpg_file.write_bytes(jpeg_data)
        result=get_image_full(tmp_brand_dir,"products/test-product/images/photo.jpg","products")
        assert result["success"]==True
        assert result["data"]["dataUrl"].startswith("data:image/jpeg;base64,")
#=============================================================================
#Path traversal tests
#=============================================================================
class TestPathTraversal:
    """Tests for path traversal prevention."""
    def test_thumbnail_blocks_path_traversal(self,tmp_brand_dir,png_image_data):
        """Should block path traversal attempts in thumbnail."""
        result=get_image_thumbnail(tmp_brand_dir,"products/../../../etc/passwd","products")
        assert result["success"]==False
        assert "Invalid path"in result["error"]or "Image not found"in result["error"]
    def test_full_blocks_path_traversal(self,tmp_brand_dir):
        """Should block path traversal attempts in full image."""
        result=get_image_full(tmp_brand_dir,"products/../../../etc/passwd","products")
        assert result["success"]==False
        assert "Invalid path"in result["error"]or "Image not found"in result["error"]
