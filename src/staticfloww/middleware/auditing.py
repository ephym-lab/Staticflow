from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import time

class BaseAuditor(ABC):
    @abstractmethod
    async def log_request(self, payload: Dict[str, Any], context: Dict[str, Any]):
        pass

    @abstractmethod
    async def log_response(self, response: Any, context: Dict[str, Any]):
        pass

class MemoryAuditor(BaseAuditor):
    def __init__(self):
        self.logs = []

    async def log_request(self, payload: Dict[str, Any], context: Dict[str, Any]):
        self.logs.append({
            "timestamp": time.time(),
            "type": "request",
            "payload": payload,
            "context": context
        })

    async def log_response(self, response: Any, context: Dict[str, Any]):
        self.logs.append({
            "timestamp": time.time(),
            "type": "response",
            "data": response,
            "context": context
        })

class MongoAuditor(BaseAuditor):
    def __init__(self, uri: str, db_name: str = "staticflow", collection_name: str = "audit_logs"):
        from motor.motor_asyncio import AsyncIOMotorClient
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    async def log_request(self, payload: Dict[str, Any], context: Dict[str, Any]):
        await self.collection.insert_one({
            "timestamp": time.time(),
            "type": "request",
            "payload": payload,
            "context": context
        })

    async def log_response(self, response: Any, context: Dict[str, Any]):
        await self.collection.insert_one({
            "timestamp": time.time(),
            "type": "response",
            "data": response,
            "context": context
        })
