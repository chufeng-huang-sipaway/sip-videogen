"""Document management service."""
from __future__ import annotations
import base64
from pathlib import Path
from sip_videogen.brands.storage import get_active_brand,get_brand_dir
from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_TEXT_EXTS,bridge_ok,bridge_error
from ..utils.os_utils import reveal_in_file_manager
from ..utils.path_utils import resolve_docs_path
class DocumentService:
    """Document (text file) operations."""
    def __init__(self,state:BridgeState):self._state=state
    def _get_docs_dir(self,slug:str|None=None)->tuple[Path|None,str|None]:
        """Get docs directory for target slug."""
        target_slug=slug or get_active_brand()
        if not target_slug:return None,"No brand selected"
        return get_brand_dir(target_slug)/"docs",None
    def get_documents(self,slug:str|None=None)->dict:
        """List brand documents (text files) under docs/."""
        try:
            target_slug=slug or get_active_brand()
            if not target_slug:return bridge_error("No brand selected")
            docs_dir=get_brand_dir(target_slug)/"docs"
            if not docs_dir.exists():return bridge_ok({"documents":[]})
            documents:list[dict]=[]
            for path in sorted(docs_dir.rglob("*")):
                if not path.is_file()or path.name.startswith(".")or path.suffix.lower()not in ALLOWED_TEXT_EXTS:continue
                rel=str(path.relative_to(docs_dir))
                documents.append({"name":path.name,"path":rel,"size":path.stat().st_size})
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
            if resolved.suffix.lower()not in ALLOWED_TEXT_EXTS:return bridge_error("Unsupported file type")
            max_bytes=512*1024
            if resolved.stat().st_size>max_bytes:return bridge_error("Document too large to preview (limit: 512KB)")
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
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_docs_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Document not found")
            if resolved.is_dir():return bridge_error("Cannot delete folders")
            resolved.unlink()
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def rename_document(self,relative_path:str,new_name:str)->dict:
        """Rename a document file."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_docs_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Document not found")
            if"/"in new_name or"\\"in new_name:return bridge_error("Invalid filename")
            if Path(new_name).suffix.lower()not in ALLOWED_TEXT_EXTS:return bridge_error("Unsupported file type")
            new_path=resolved.parent/new_name
            if new_path.exists():return bridge_error(f"File already exists: {new_name}")
            resolved.rename(new_path)
            rel=str(new_path.relative_to(brand_dir/"docs"))
            return bridge_ok({"newPath":rel})
        except Exception as e:return bridge_error(str(e))
    def upload_document(self,filename:str,data_base64:str)->dict:
        """Upload a document into docs/ (text-only)."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            if"/"in filename or"\\"in filename:return bridge_error("Invalid filename")
            if Path(filename).suffix.lower()not in ALLOWED_TEXT_EXTS:return bridge_error("Unsupported file type")
            docs_dir=brand_dir/"docs";docs_dir.mkdir(parents=True,exist_ok=True)
            target_path=docs_dir/filename
            if target_path.exists():return bridge_error(f"File already exists: {filename}")
            content=base64.b64decode(data_base64);target_path.write_bytes(content)
            return bridge_ok({"path":filename})
        except Exception as e:return bridge_error(str(e))
