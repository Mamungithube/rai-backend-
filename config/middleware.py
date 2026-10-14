import time
import structlog

logger = structlog.get_logger(__name__)

class LatencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        response["X-Response-Time"] = f"{duration:.4f}s"
        
        # Log slow requests (> 500ms)
        if duration > 0.5:
            logger.warning("slow_request_detected", path=request.path, duration=f"{duration:.4f}s")
            
        return response
