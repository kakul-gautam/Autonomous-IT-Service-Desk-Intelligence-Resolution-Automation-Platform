import logging
import os
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache


logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """Prevent too many requests from same IP. Stops brute force attacks."""
    
    RATE_LIMIT = 100  # 100 requests per minute
    SENSITIVE_RATE_LIMIT = 50  # 50 for login page
    
    SENSITIVE_ENDPOINTS = ['/login/', '/password-reset/']
    
    def process_request(self, request):
        """Check if user is making too many requests."""
        ip = self.get_client_ip(request)
        
        # Use stricter limit for login
        rate_limit = self.RATE_LIMIT
        if any(request.path.startswith(p) for p in self.SENSITIVE_ENDPOINTS):
            rate_limit = self.SENSITIVE_RATE_LIMIT
        
        cache_key = f"rate_limit:{ip}"
        
        # Use atomic increment with 60-second TTL
        # Try to increment, if key doesn't exist, initialize and set
        try:
            current = cache.incr(cache_key)
        except ValueError:
            # Key doesn't exist or isn't an integer, initialize it
            cache.set(cache_key, 1, 60)
            current = 1
        
        if current > rate_limit:
            logger.warning(f"Rate limit exceeded for IP {ip}")
            return HttpResponse("Too many requests. Try again later.", status=429)
        
        return None
    
    def get_client_ip(self, request):
        """Get IP address from request.
        
        Only trusts X-Forwarded-For if request comes from a known trusted proxy.
        Otherwise returns REMOTE_ADDR directly.
        """
        # For now, trust X-Forwarded-For only from localhost (development)
        # In production, configure TRUSTED_PROXIES via environment
        remote_addr = request.META.get('REMOTE_ADDR', 'unknown')
        trusted_proxies = os.getenv('TRUSTED_PROXIES', 'localhost,127.0.0.1').split(',')
        trusted_proxies = [p.strip() for p in trusted_proxies if p.strip()]
        
        if remote_addr not in trusted_proxies:
            # Don't trust X-Forwarded-For from untrusted source
            return remote_addr
        
        # Only parse X-Forwarded-For from trusted proxies
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            # Get the first IP (original client)
            return x_forwarded.split(',')[0].strip()
        
        return remote_addr


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to prevent attacks."""
    
    def process_response(self, request, response):
        """Add security headers."""
        # Prevent clickjacking
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Prevent MIME sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent XSS
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Control browser features
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response


class InputValidationMiddleware(MiddlewareMixin):
    """Check request size to prevent buffer overflow attacks."""
    
    MAX_QUERY_STRING = 4096  # 4KB
    MAX_POST_SIZE = 10485760  # 10MB
    
    def process_request(self, request):
        """Check if request is too large."""
        # Check query string
        query = request.META.get('QUERY_STRING', '')
        if len(query) > self.MAX_QUERY_STRING:
            logger.warning(f"Query string too large: {len(query)} bytes")
            return HttpResponse("Query too large", status=413)
        
        # Check POST size
        content_length = request.META.get('CONTENT_LENGTH', 0)
        try:
            content_length = int(content_length)
        except ValueError:
            content_length = 0
        
        if content_length > self.MAX_POST_SIZE:
            logger.warning(f"POST too large: {content_length} bytes")
            return HttpResponse("Request too large", status=413)
        
        # Check for null bytes only on reasonably-sized requests
        # For large requests, skip in-memory check to avoid memory exhaustion
        if request.method == 'POST' and content_length < 1048576:  # Skip for >1MB
            try:
                if b'\x00' in request.body:
                    logger.warning("Null byte detected in request")
                    return HttpResponse("Invalid request", status=400)
            except Exception as e:
                # If we can't read the body safely, reject the request
                logger.warning(f"Error checking request body: {str(e)}")
                return HttpResponse("Invalid request", status=400)
        
        return None
