import pytest
from staticfloww import StaticPayload, Section
from pydantic import BaseModel
from typing import Optional

class UserDetails(Section):
    name: str

class PaymentDetails(Section):
    amount: float

class MyGodSchema(StaticPayload):
    user_data: Optional[UserDetails] = None
    payment_data: Optional[PaymentDetails] = None

def test_payload_plucking():
    payload = MyGodSchema(
        details={"type": "TEST"},
        user_data={"name": "John Doe"},
        payment_data={"amount": 99.99}
    )
    
    user_section = payload.pluck("user_data")
    assert user_section.name == "John Doe"
    
    payment_section = payload.pluck("payment_data")
    assert payment_section.amount == 99.99
    
    missing = payload.pluck("Other")
    assert missing is None

def test_extra_fields():
    payload = MyGodSchema(
        details={"type": "TEST", "action": "TEST"},
        ExtraField="CustomData"
    )
    assert payload.ExtraField == "CustomData"
