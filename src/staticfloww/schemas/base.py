from typing import Any, Dict, Optional, Type, Union
from pydantic import BaseModel, Field, ConfigDict

class Section(BaseModel):
    """
    Base class for all data sections in the God Schema.
    Users should inherit from this to define their specific data structures.
    """
    model_config = ConfigDict(extra="allow")

class RequestDetails(BaseModel):
    """
    Meta details about the specific request action.
    """
    type: str
    country: Optional[str] = None
    version: Optional[str] = "v1"

class StaticPayload(BaseModel):
    """
    The base "God Schema" payload.
    All incoming requests to the gateway must adhere to this structure.
    """
    details: RequestDetails
    SessionID: Optional[str] = None
    IMEI: Optional[str] = ""
    Country: Optional[str] = None
    FormID: Optional[str] = None
    
    # This allows users to add their custom sections as fields in their subclass
    model_config = ConfigDict(extra="allow")

    def pluck(self, section_name: str) -> Optional[Section]:
        """
        Extracts a specific section from the payload.
        """
        return getattr(self, section_name, None)
