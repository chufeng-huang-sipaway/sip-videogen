"""Document management service."""
from __future__ import annotations
import base64
from pathlib import Path
from sip_videogen.brands.storage import get_active_brand,get_brand_dir
from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_TEXT_EXTS,BridgeResponse
from ..utils.path_utils import resolve_docs_path
class DocumentService:
    """Document (text file) operations."""
    def __init__(self,state:BridgeState):self._state=state
    def _get_docs_dir(self,slug:str|None=None)->tuple[Path|None,str|None]:
        """Get docs directory for target slug."""
        target_slug=slug or self._state.current_brand or get_active_brand()
        if not target_slug:return None,"No brand selected"
        return get_brand_dir(target_slug)/"docs",None
    def get_documents(self,slug:str|None=None)->dict:
        """List brand documents (text files) under docs/."""
        try:
            target_slug=slug or self._state.current_brand or get_active_brand()
            if not target_slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            docs_dir=get_brand_dir(target_slug)/"docs"
            if not docs_dir.exists():return BridgeResponse(success=True,data={"documents":[]}).to_dict()
            documents:list[dict]=[]
            for path in sorted(docs_dir.rglob("*")):
                if not path.is_file()or path.name.startswith(".")or path.suffix.lower()not in ALLOWED_TEXT_EXTS:continue
                rel=str(path.relative_to(docs_dir))
                documents.append({"name":path.name,"path":rel,"size":path.stat().st_size})
            return BridgeResponse(success=True,data={"documents":documents}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def read_document(self,relative_path:str)->dict:
        """Read a document's text content (read-only preview)."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_docs_path(brand_dir,relative_path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Document not found").to_dict()
            if resolved.suffix.lower()not in ALLOWED_TEXT_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            max_bytes=512*1024
            if resolved.stat().st_size>max_bytes:return BridgeResponse(success=False,error="Document too large to preview (limit: 512KB)").to_dict()
            content=resolved.read_text(encoding="utf-8",errors="replace")
            return BridgeResponse(success=True,data={"content":content}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def open_document_in_finder(self,relative_path:str)->dict:
        """Reveal a document in Finder."""
        import subprocess
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_docs_path(brand_dir,relative_path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Document not found").to_dict()
            subprocess.run(["open","-R",str(resolved)],check=True)
            return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def delete_document(self,relative_path:str)->dict:
        """Delete a document file."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_docs_path(brand_dir,relative_path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Document not found").to_dict()
            if resolved.is_dir():return BridgeResponse(success=False,error="Cannot delete folders").to_dict()
            resolved.unlink()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def rename_document(self,relative_path:str,new_name:str)->dict:
        """Rename a document file."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_docs_path(brand_dir,relative_path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Document not found").to_dict()
            if"/"in new_name or"\\"in new_name:return BridgeResponse(success=False,error="Invalid filename").to_dict()
            if Path(new_name).suffix.lower()not in ALLOWED_TEXT_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            new_path=resolved.parent/new_name
            if new_path.exists():return BridgeResponse(success=False,error=f"File already exists: {new_name}").to_dict()
            resolved.rename(new_path)
            rel=str(new_path.relative_to(brand_dir/"docs"))
            return BridgeResponse(success=True,data={"newPath":rel}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def upload_document(self,filename:str,data_base64:str)->dict:
        """Upload a document into docs/ (text-only)."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            if"/"in filename or"\\"in filename:return BridgeResponse(success=False,error="Invalid filename").to_dict()
            if Path(filename).suffix.lower()not in ALLOWED_TEXT_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            docs_dir=brand_dir/"docs";docs_dir.mkdir(parents=True,exist_ok=True)
            target_path=docs_dir/filename
            if target_path.exists():return BridgeResponse(success=False,error=f"File already exists: {filename}").to_dict()
            content=base64.b64decode(data_base64);target_path.write_bytes(content)
            return BridgeResponse(success=True,data={"path":filename}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
