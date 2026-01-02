"""Product management service."""
from __future__ import annotations
import base64,io,re
from datetime import datetime
from pathlib import Path
from sip_videogen.brands.models import ProductAttribute,ProductFull
from sip_videogen.brands.product_description import extract_attributes_from_description,has_attributes_block,merge_attributes_into_description
from sip_videogen.brands.storage import(add_product_image,create_product,delete_product,delete_product_image,list_product_images,list_products,load_product,save_product,set_primary_product_image)
from sip_videogen.config.logging import get_logger
from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_IMAGE_EXTS,bridge_ok,bridge_error
from ..utils.path_utils import resolve_in_dir
logger=get_logger(__name__)
class ProductService:
    """Product CRUD and image operations."""
    def __init__(self,state:BridgeState):self._state=state
    def get_products(self,brand_slug:str|None=None)->dict:
        """Get list of products for a brand."""
        try:
            target_slug=brand_slug or self._state.get_active_slug()
            if not target_slug:return bridge_error("No brand selected")
            products=list_products(target_slug)
            return bridge_ok({"products":[{"slug":p.slug,"name":p.name,"description":p.description,"primary_image":p.primary_image,"attribute_count":p.attribute_count,"created_at":p.created_at.isoformat(),"updated_at":p.updated_at.isoformat()}for p in products]})
        except Exception as e:return bridge_error(str(e))
    def get_product(self,product_slug:str)->dict:
        """Get detailed product information."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            product=load_product(slug,product_slug)
            if not product:return bridge_error(f"Product '{product_slug}' not found")
            description=merge_attributes_into_description(product.description or"",product.attributes)
            return bridge_ok({"slug":product.slug,"name":product.name,"description":description,"images":product.images,"primary_image":product.primary_image,"attributes":[{"key":a.key,"value":a.value,"category":a.category}for a in product.attributes],"created_at":product.created_at.isoformat(),"updated_at":product.updated_at.isoformat()})
        except Exception as e:return bridge_error(str(e))
    def create_product(self,name:str,description:str,images:list[dict]|None=None,attributes:list[dict]|None=None)->dict:
        """Create a new product."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            if not name.strip():return bridge_error("Product name is required")
            product_slug=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
            if not product_slug:return bridge_error("Invalid product name")
            if load_product(slug,product_slug):return bridge_error(f"Product '{product_slug}' already exists")
            description_text=description.strip();parsed_attributes:list[ProductAttribute]=[]
            if attributes is not None:
                for attr in attributes:
                    if not isinstance(attr,dict):continue
                    key=attr.get("key","").strip();value=attr.get("value","").strip();category=attr.get("category","general").strip()
                    if key and value:parsed_attributes.append(ProductAttribute(key=key,value=value,category=category))
            else:description_text,parsed_attributes=extract_attributes_from_description(description_text)
            description_text=merge_attributes_into_description(description_text,parsed_attributes)
            now=datetime.utcnow()
            product=ProductFull(slug=product_slug,name=name.strip(),description=description_text,images=[],primary_image="",attributes=parsed_attributes,created_at=now,updated_at=now)
            create_product(slug,product)
            if images:
                for img in images:
                    filename=img.get("filename","");data_b64=img.get("data","")
                    if not filename or not data_b64:continue
                    ext=Path(filename).suffix.lower()
                    if ext not in ALLOWED_IMAGE_EXTS:continue
                    try:content=base64.b64decode(data_b64);add_product_image(slug,product_slug,filename,content)
                    except Exception as e:logger.warning("Failed to add product image %s: %s",filename,e)
            return bridge_ok({"slug":product_slug})
        except Exception as e:return bridge_error(str(e))
    def update_product(self,product_slug:str,name:str|None=None,description:str|None=None,attributes:list[dict]|None=None)->dict:
        """Update an existing product."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            product=load_product(slug,product_slug)
            if not product:return bridge_error(f"Product '{product_slug}' not found")
            if name is not None:product.name=name.strip()
            description_text=product.description or""
            if description is not None:description_text=description.strip()
            if attributes is not None:
                parsed_attributes:list[ProductAttribute]=[]
                for attr in attributes:
                    if not isinstance(attr,dict):continue
                    key=attr.get("key","").strip();value=attr.get("value","").strip();category=attr.get("category","general").strip()
                    if key and value:parsed_attributes.append(ProductAttribute(key=key,value=value,category=category))
                product.attributes=parsed_attributes
            elif description is not None and has_attributes_block(description_text):
                description_text,parsed_attributes=extract_attributes_from_description(description_text);product.attributes=parsed_attributes
            product.description=merge_attributes_into_description(description_text,product.attributes)
            product.updated_at=datetime.utcnow();save_product(slug,product)
            return bridge_ok({"slug":product.slug,"name":product.name,"description":product.description})
        except Exception as e:return bridge_error(str(e))
    def delete_product(self,product_slug:str)->dict:
        """Delete a product and all its files."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            deleted=delete_product(slug,product_slug)
            if not deleted:return bridge_error(f"Product '{product_slug}' not found")
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def get_product_images(self,product_slug:str)->dict:
        """Get list of images for a product."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            images=list_product_images(slug,product_slug)
            return bridge_ok({"images":images})
        except Exception as e:return bridge_error(str(e))
    def upload_product_image(self,product_slug:str,filename:str,data_base64:str)->dict:
        """Upload an image to a product."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            if"/"in filename or"\\"in filename:return bridge_error("Invalid filename")
            ext=Path(filename).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            content=base64.b64decode(data_base64);brand_relative_path=add_product_image(slug,product_slug,filename,content)
            return bridge_ok({"path":brand_relative_path})
        except Exception as e:return bridge_error(str(e))
    def delete_product_image(self,product_slug:str,filename:str)->dict:
        """Delete a product image."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            deleted=delete_product_image(slug,product_slug,filename)
            if not deleted:return bridge_error(f"Image '{filename}' not found")
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def set_primary_product_image(self,product_slug:str,filename:str)->dict:
        """Set the primary image for a product."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            product=load_product(slug,product_slug)
            if not product:return bridge_error(f"Product '{product_slug}' not found")
            brand_relative_path=f"products/{product_slug}/images/{filename}"
            if brand_relative_path not in product.images:return bridge_error(f"Image '{filename}' not found in product")
            success=set_primary_product_image(slug,product_slug,brand_relative_path)
            if not success:return bridge_error("Failed to set primary image")
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def get_product_image_thumbnail(self,path:str)->dict:
        """Get base64-encoded thumbnail for a product image."""
        try:
            if not path.startswith("products/"):return bridge_error("Path must start with 'products/'")
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_in_dir(brand_dir,path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Image not found")
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            if suffix==".svg":
                content=resolved.read_bytes();encoded=base64.b64encode(content).decode("utf-8")
                return bridge_ok({"dataUrl":f"data:image/svg+xml;base64,{encoded}"})
            from PIL import Image
            with Image.open(resolved)as img:
                img=img.convert("RGBA");img.thumbnail((256,256))
                buf=io.BytesIO();img.save(buf,format="PNG")
                encoded=base64.b64encode(buf.getvalue()).decode("utf-8")
            return bridge_ok({"dataUrl":f"data:image/png;base64,{encoded}"})
        except Exception as e:return bridge_error(str(e))
    def get_product_image_full(self,path:str)->dict:
        """Get base64-encoded full-resolution product image."""
        try:
            if not path.startswith("products/"):return bridge_error("Path must start with 'products/'")
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_in_dir(brand_dir,path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Image not found")
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            content=resolved.read_bytes();encoded=base64.b64encode(content).decode("utf-8")
            mime_types={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".gif":"image/gif",".webp":"image/webp",".svg":"image/svg+xml"}
            mime=mime_types.get(suffix,"image/png")
            return bridge_ok({"dataUrl":f"data:{mime};base64,{encoded}"})
        except Exception as e:return bridge_error(str(e))
    async def analyze_all_packaging_text(self,skip_existing:bool=True)->dict:
        """Bulk analyze packaging text for all products in active brand."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            from sip_videogen.advisor.tools import _impl_analyze_all_product_packaging
            result=await _impl_analyze_all_product_packaging(skip_existing=skip_existing,skip_human_edited=True,max_products=50)
            return bridge_ok({"result":result})
        except Exception as e:return bridge_error(str(e))
