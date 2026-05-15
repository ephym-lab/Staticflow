from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import time

class BaseAuditor(ABC):
    """
    Base class for all auditing strategies.
    Supports individual logging or unified transaction logging.
    """
    @abstractmethod
    async def log_request(self, payload: Dict[str, Any], context: Dict[str, Any]):
        pass

    @abstractmethod
    async def log_response(self, response: Any, context: Dict[str, Any]):
        pass

    @abstractmethod
    async def log_error(self, error: Exception, context: Dict[str, Any]):
        pass

    @abstractmethod
    async def log_transaction(self, request: Any, response: Any = None, error: Any = None, context: Dict[str, Any] = None):
        pass

    @abstractmethod
    async def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent audit logs.
        """
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

    async def log_error(self, error: Exception, context: Dict[str, Any]):
        self.logs.append({
            "timestamp": time.time(),
            "type": "error",
            "message": str(error),
            "context": context
        })

    async def log_transaction(self, request: Any, response: Any = None, error: Any = None, context: Dict[str, Any] = None):
        self.logs.append({
            "timestamp": time.time(),
            "request": request,
            "response": response,
            "error": error, # Keep the dict/summary if present
            "context": context
        })

    async def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        # Return most recent logs first
        return self.logs[-limit:][::-1]

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

    async def log_error(self, error: Exception, context: Dict[str, Any]):
        await self.collection.insert_one({
            "timestamp": time.time(),
            "type": "error",
            "message": str(error),
            "context": context
        })

    async def log_transaction(self, request: Any, response: Any = None, error: Any = None, context: Dict[str, Any] = None):
        await self.collection.insert_one({
            "timestamp": time.time(),
            "type": "transaction",
            "request": request,
            "response": response,
            "error": error, # Preserves structured summary/traceback
            "context": context
        })

    async def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        # Fetch latest logs sorted by timestamp descending
        cursor = self.collection.find().sort("timestamp", -1).limit(limit)
        results = await cursor.to_list(length=limit)
        # Remove MongoDB _id for easier JSON serialization
        for r in results:
            r["_id"] = str(r["_id"])
        return results
