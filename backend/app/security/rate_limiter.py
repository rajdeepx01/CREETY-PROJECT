import time
from collections import defaultdict
from fastapi import Request, HTTPException, status

class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter per client IP / key."""
    def __init__(self):
        # key -> list of timestamps
        self.requests = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        
        # Filter out expired timestamps
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]
        
        if len(self.requests[key]) >= max_requests:
            return False
        
        self.requests[key].append(now)
        return True

limiter = InMemoryRateLimiter()

def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Dependency that enforces rate limiting per client IP."""
    async def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        # Combine endpoint path with IP for endpoint-specific limits
        endpoint_key = f"{request.url.path}:{client_ip}"
        
        if not limiter.is_allowed(endpoint_key, max_requests=max_requests, window_seconds=window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s allowed."
            )
    return dependency
