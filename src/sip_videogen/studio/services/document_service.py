"""Document management service."""
from __future__ import annotations
import base64
from pathlib import Path
from sip_videogen.brands import storage
from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_TEXT_EXTS,bridge_ok,bridge_error
from ..utils.os_utils import reveal_in_file_manager
from ..utils.path_utils import resolve_docs_path
class DocumentService:
    """Document (text file) operations."""
    def __init__(self,state:BridgeState):self._state=state
    def get_documents(self,slug:str|None=None)->dict:
        """List brand documents (text files) under docs/."""
        try:
            target_slug=slug or storage.get_active_brand()
            if not target_slug:return bridge_error("No brand selected")
            documents=storage.list_documents(target_slug)
            return bridge_ok({"documents":documents})
        except Exception as e:return bridge_error(str(e))
    def read_document(self,relative_path:str)->dict:
        """Read a document's text content (read-only preview)."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_docs_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Document not found")
            if resolved.suffix.lower()not in ALLOWED_TEXT_EXTS:
                return bridge_error("Unsupported file type")
            max_bytes=512*1024
            if resolved.stat().st_size>max_bytes:
                return bridge_error("Document too large to preview (limit: 512KB)")
            content=resolved.read_text(encoding="utf-8",errors="replace")
            return bridge_ok({"content":content})
        except Exception as e:return bridge_error(str(e))
    def open_document_in_finder(self,relative_path:str)->dict:
        """Reveal a document in Finder."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_docs_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Document not found")
            reveal_in_file_manager(resolved)
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def delete_document(self,relative_path:str)->dict:
        """Delete a document file."""
        try:
            slug=storage.get_active_brand()
            if not slug:return bridge_error("No brand selected")
            success,err=storage.delete_document(slug,relative_path)
            if err:return bridge_error(err)
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def rename_document(self,relative_path:str,new_name:str)->dict:
        """Rename a document file."""
        try:
            slug=storage.get_active_brand()
            if not slug:return bridge_error("No brand selected")
            if Path(new_name).suffix.lower()not in ALLOWED_TEXT_EXTS:
                return bridge_error("Unsupported file type")
            new_rel,err=storage.rename_document(slug,relative_path,new_name)
            if err:return bridge_error(err)
            return bridge_ok({"newPath":new_rel})
        except Exception as e:return bridge_error(str(e))
    def upload_document(self,filename:str,data_base64:str)->dict:
        """Upload a document into docs/ (text-only)."""
        try:
            slug=storage.get_active_brand()
            if not slug:return bridge_error("No brand selected")
            if"/"in filename or"\\"in filename:return bridge_error("Invalid filename")
            if Path(filename).suffix.lower()not in ALLOWED_TEXT_EXTS:
                return bridge_error("Unsupported file type")
            #Check if file exists
            docs_dir=storage.get_docs_dir(slug)
            target_path=docs_dir/filename
            if target_path.exists():return bridge_error(f"File already exists: {filename}")
            content=base64.b64decode(data_base64)
            saved_path,err=storage.save_document(slug,filename,content)
            if err:return bridge_error(err)
            return bridge_ok({"path":saved_path})
        except Exception as e:return bridge_error(str(e))
