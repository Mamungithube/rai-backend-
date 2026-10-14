from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from urllib.parse import parse_qs
import logging
import hashlib
from django.core.cache import cache

logger = logging.getLogger("authentication")

@database_sync_to_async
def get_user(token_key):
    try:
        if not token_key:
            return AnonymousUser()

        if token_key.startswith("Bearer ") or token_key.startswith("bearer "):
            token_key = token_key.split(" ", 1)[1].strip()

        cache_key = f"ws_auth_{hashlib.sha256(token_key.encode()).hexdigest()}"
        cached_user_id = cache.get(cache_key)
        
        if cached_user_id:
            try:
                user = get_user_model().objects.get(id=cached_user_id, is_active=True)
                return user
            except get_user_model().DoesNotExist:
                cache.delete(cache_key)
        
        access_token = AccessToken(token_key)
        user_id = access_token['user_id']
        
        user = get_user_model().objects.get(id=user_id, is_active=True)
        cache.set(cache_key, user_id, 300)
        logger.info(f"WebSocket auth successful for user: {user.username}")
        return user
        
    except (InvalidToken, TokenError) as e:
        logger.warning(f"Invalid WebSocket token: {e}")
        return AnonymousUser()
    except get_user_model().DoesNotExist:
        logger.warning(f"User not found for WebSocket token")
        return AnonymousUser()
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}", exc_info=True)
        return AnonymousUser()

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
            raw_token = None
            query_string = parse_qs(scope.get("query_string", b"").decode("utf8"))
            
            # 1. Query parameters: ?token=... or ?access_token=... or ?bearer=...
            tokens = (
                query_string.get("token") or 
                query_string.get("access_token") or 
                query_string.get("bearer")
            )
            if tokens and len(tokens) > 0 and tokens[0]:
                raw_token = tokens[0].strip()

            # 2. Authorization header / Sec-WebSocket-Protocol if not in query params
            if not raw_token:
                headers = dict(scope.get("headers", []))
                
                # Check Authorization header
                if b"authorization" in headers:
                    auth_header = headers[b"authorization"].decode("utf8").strip()
                    if auth_header.lower().startswith("bearer "):
                        raw_token = auth_header.split(" ", 1)[1].strip()
                    else:
                        raw_token = auth_header

                # Check Sec-WebSocket-Protocol (used by some mobile/web WebSocket clients)
                elif b"sec-websocket-protocol" in headers:
                    protocols = [p.strip() for p in headers[b"sec-websocket-protocol"].decode("utf8").split(",")]
                    for idx, p in enumerate(protocols):
                        if p.lower() in ("bearer", "token", "jwt") and idx + 1 < len(protocols):
                            raw_token = protocols[idx + 1]
                            break
                        elif len(p) > 30 and "." in p:  # Likely a JWT token
                            raw_token = p
                            break

                # 3. Cookies if present
                elif b"cookie" in headers:
                    from http.cookies import SimpleCookie
                    cookie_header = headers[b"cookie"].decode("utf8")
                    cookie = SimpleCookie()
                    cookie.load(cookie_header)
                    for key in ("access_token", "token", "jwt"):
                        if key in cookie:
                            raw_token = cookie[key].value
                            break

            if raw_token:
                scope["user"] = await get_user(raw_token)
            else:
                logger.debug("WebSocket connection attempt with no auth token provided")
                scope["user"] = AnonymousUser()
        except Exception as e:
            logger.error(f"Middleware error: {e}", exc_info=True)
            scope["user"] = AnonymousUser()
        
        return await self.app(scope, receive, send)