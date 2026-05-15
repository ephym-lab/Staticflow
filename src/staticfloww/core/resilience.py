import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type
from ..exceptions import StaticflowwError

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(
        self, 
        failure_threshold: int = 5, 
        recovery_timeout: float = 30.0,
        name: str = "default"
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None

    def record_success(self):
        self.failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            print(f"--- [Circuit Breaker: {self.name}] State changed to OPEN ---")

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                print(f"--- [Circuit Breaker: {self.name}] State changed to HALF_OPEN ---")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
            
        return False

class ResilienceStrategy:
    def __init__(
        self, 
        max_retries: int = 3, 
        backoff_factor: float = 0.5,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.circuit_breaker = circuit_breaker

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            raise StaticflowwError(f"Circuit breaker '{self.circuit_breaker.name}' is OPEN", status_code=503)

        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = self.backoff_factor * (2 ** (attempt - 1))
                    print(f"--- [Resilience] Retry {attempt}/{self.max_retries} after {wait_time}s ---")
                    await asyncio.sleep(wait_time)
                
                result = await func(*args, **kwargs)
                
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()
                return result
            
            except Exception as e:
                last_exception = e
                # We only retry on certain errors (timeouts, connection issues)
                # But for this implementation, let's keep it simple
                print(f"--- [Resilience] Attempt {attempt} failed: {str(e)} ---")
                
        if self.circuit_breaker:
            self.circuit_breaker.record_failure()
            
        raise last_exception
