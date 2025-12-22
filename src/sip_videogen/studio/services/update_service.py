"""App update management service."""
from __future__ import annotations
import asyncio,sys,threading
from sip_videogen.studio import __version__
from sip_videogen.studio.updater import(DownloadProgress,UpdateInfo,check_for_updates as do_check,download_update,get_current_version,get_update_settings,install_update,is_bundled_app,mark_update_checked,save_update_settings)
from ..state import BridgeState
from ..utils.bridge_types import BridgeResponse
class UpdateService:
    """App update checking and installation."""
    def __init__(self,state:BridgeState):self._state=state
    def get_app_version(self)->dict:
        """Get the current app version."""
        return BridgeResponse(success=True,data={"version":__version__,"is_bundled":is_bundled_app()}).to_dict()
    def check_for_updates(self)->dict:
        """Check if a newer version is available on GitHub Releases."""
        try:
            update_info=asyncio.run(do_check());mark_update_checked()
            if update_info is None:return BridgeResponse(success=True,data={"has_update":False,"current_version":get_current_version()}).to_dict()
            return BridgeResponse(success=True,data={"has_update":True,"current_version":get_current_version(),"new_version":update_info.version,"changelog":update_info.changelog,"release_url":update_info.release_url,"download_url":update_info.download_url,"file_size":update_info.file_size}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def download_and_install_update(self,download_url:str,version:str)->dict:
        """Download and install an update."""
        try:
            if not is_bundled_app():return BridgeResponse(success=False,error="Updates only work when running as a bundled .app. For development, use git pull instead.").to_dict()
            self._state.update_progress={"status":"downloading","percent":0}
            def on_progress(progress:DownloadProgress):self._state.update_progress={"status":"downloading","percent":progress.percent,"downloaded":progress.downloaded_bytes,"total":progress.total_bytes}
            update_info=UpdateInfo(version=version,download_url=download_url,changelog="",release_url="",file_size=0)
            dmg_path=asyncio.run(download_update(update_info,on_progress))
            if not dmg_path or not dmg_path.exists():self._state.update_progress={"status":"error","error":"Download failed"};return BridgeResponse(success=False,error="Failed to download update").to_dict()
            self._state.update_progress={"status":"installing","percent":100}
            if not install_update(dmg_path):self._state.update_progress={"status":"error","error":"Install failed"};return BridgeResponse(success=False,error="Failed to start update installation").to_dict()
            self._state.update_progress={"status":"restarting","percent":100}
            def quit_app():
                import time;time.sleep(1)
                if self._state.window:self._state.window.destroy()
                sys.exit(0)
            threading.Thread(target=quit_app,daemon=True).start()
            return BridgeResponse(success=True,data={"message":"Update downloaded. Restarting to install..."}).to_dict()
        except Exception as e:self._state.update_progress={"status":"error","error":str(e)};return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_update_progress(self)->dict:
        """Get the current update download/install progress."""
        p=self._state.update_progress
        if p is None:return BridgeResponse(success=True,data={"status":"idle","percent":0}).to_dict()
        return BridgeResponse(success=True,data=p).to_dict()
    def skip_update_version(self,version:str)->dict:
        """Skip a specific version (don't prompt for this version again)."""
        try:save_update_settings(skipped_version=version);return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_update_settings(self)->dict:
        """Get update-related settings."""
        try:return BridgeResponse(success=True,data=get_update_settings()).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def set_update_check_on_startup(self,enabled:bool)->dict:
        """Enable or disable automatic update checks on startup."""
        try:save_update_settings(check_on_startup=enabled);return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
