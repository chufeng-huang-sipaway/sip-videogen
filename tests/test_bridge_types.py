"""Tests for bridge response types and helpers."""
import pytest
from sip_videogen.studio.utils.bridge_types import BridgeResponse,bridge_ok,bridge_error
class TestBridgeResponse:
    """Tests for BridgeResponse dataclass."""
    def test_success_response_structure(self):
        """Success response should have correct shape."""
        resp=BridgeResponse(success=True,data={"foo":1})
        assert resp.to_dict()=={"success":True,"data":{"foo":1},"error":None}
    def test_error_response_structure(self):
        """Error response should have correct shape."""
        resp=BridgeResponse(success=False,error="Something failed")
        assert resp.to_dict()=={"success":False,"data":None,"error":"Something failed"}
    def test_empty_success_response(self):
        """Success with no data should have None data."""
        resp=BridgeResponse(success=True)
        assert resp.to_dict()=={"success":True,"data":None,"error":None}
class TestBridgeHelpers:
    """Tests for bridge_ok and bridge_error helpers."""
    def test_bridge_ok_with_data(self):
        """bridge_ok should return success response with data."""
        assert bridge_ok({"foo":1})=={"success":True,"data":{"foo":1},"error":None}
    def test_bridge_ok_with_list(self):
        """bridge_ok should handle list data."""
        assert bridge_ok([1,2,3])=={"success":True,"data":[1,2,3],"error":None}
    def test_bridge_ok_empty(self):
        """bridge_ok with no args should return None data."""
        assert bridge_ok()=={"success":True,"data":None,"error":None}
    def test_bridge_error_with_message(self):
        """bridge_error should return error response."""
        assert bridge_error("fail")=={"success":False,"data":None,"error":"fail"}
    def test_bridge_error_preserves_message(self):
        """bridge_error should preserve full error message."""
        msg="Product 'test-product' not found"
        assert bridge_error(msg)=={"success":False,"data":None,"error":msg}
    def test_response_keys_consistent(self):
        """Both response types should have same keys."""
        ok_keys=set(bridge_ok({"x":1}).keys())
        err_keys=set(bridge_error("err").keys())
        assert ok_keys==err_keys=={"success","data","error"}
