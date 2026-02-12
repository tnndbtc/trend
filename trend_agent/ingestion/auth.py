"""
Authentication Handler for API-based Sources.

This module provides authentication mechanisms for:
1. API key injection (Bearer tokens, custom headers)
2. OAuth 2.0 flows (authorization code, client credentials)
3. Token refresh and management
4. Rate limiting and retry logic
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import httpx
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class TokenExpiredError(Exception):
    """Raised when OAuth token has expired."""
    pass


class AuthHandler:
    """
    Handles authentication for API-based collectors.

    Supports multiple authentication methods:
    - API keys (Bearer tokens, custom headers)
    - OAuth 2.0 (authorization code, client credentials)
    - Basic auth
    """

    def __init__(self, source_config: Dict[str, Any]):
        """
        Initialize auth handler.

        Args:
            source_config: Source configuration with auth details
        """
        self.source_config = source_config
        self.source_type = source_config.get('source_type')
        self.api_key = source_config.get('api_key')
        self.oauth_config = source_config.get('oauth_config', {})
        self.custom_headers = source_config.get('custom_headers', {})

        # Token cache
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._refresh_token: Optional[str] = None

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for requests.

        Returns:
            Dictionary of headers to include in requests
        """
        headers = {}

        # Add custom headers
        headers.update(self.custom_headers)

        # Add API key if configured
        if self.api_key:
            # Determine header format based on source type
            if self.source_type in ['reddit', 'twitter']:
                headers['Authorization'] = f'Bearer {self.api_key}'
            elif self.source_type == 'youtube':
                # YouTube uses API key as query parameter, not header
                pass
            else:
                # Default: Bearer token
                headers['Authorization'] = f'Bearer {self.api_key}'

        # Add OAuth token if available
        if self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'

        return headers

    async def authenticate(self) -> bool:
        """
        Perform authentication based on configuration.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        # Check if OAuth is configured
        if self.oauth_config and self.oauth_config.get('client_id'):
            return await self._oauth_authenticate()

        # Check if API key is configured
        if self.api_key:
            # API key authentication doesn't require explicit auth step
            return True

        # No authentication configured
        logger.warning(f"No authentication configured for {self.source_config.get('name')}")
        return True

    async def _oauth_authenticate(self) -> bool:
        """
        Perform OAuth 2.0 authentication.

        Returns:
            True if authentication successful
        """
        grant_type = self.oauth_config.get('grant_type', 'client_credentials')

        if grant_type == 'client_credentials':
            return await self._oauth_client_credentials()
        elif grant_type == 'authorization_code':
            return await self._oauth_authorization_code()
        else:
            raise AuthenticationError(f"Unsupported OAuth grant type: {grant_type}")

    async def _oauth_client_credentials(self) -> bool:
        """
        Perform OAuth 2.0 client credentials flow.

        Returns:
            True if successful
        """
        try:
            token_url = self.oauth_config.get('token_url')
            client_id = self.oauth_config.get('client_id')
            client_secret = self.oauth_config.get('client_secret')
            scope = self.oauth_config.get('scope', '')

            if not all([token_url, client_id, client_secret]):
                raise AuthenticationError("Missing OAuth credentials")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        'grant_type': 'client_credentials',
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'scope': scope,
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                )

                response.raise_for_status()
                token_data = response.json()

                # Store tokens
                self._access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                self._refresh_token = token_data.get('refresh_token')

                logger.info(f"OAuth authentication successful for {self.source_config.get('name')}")
                return True

        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}", exc_info=True)
            raise AuthenticationError(f"OAuth authentication failed: {str(e)}")

    async def _oauth_authorization_code(self) -> bool:
        """
        Perform OAuth 2.0 authorization code flow.

        Note: This requires user interaction, so we check if tokens are already stored.

        Returns:
            True if tokens available
        """
        # Check if tokens are stored in config
        stored_access_token = self.oauth_config.get('access_token')
        stored_refresh_token = self.oauth_config.get('refresh_token')
        token_expires_at = self.oauth_config.get('token_expires_at')

        if stored_access_token:
            self._access_token = stored_access_token
            self._refresh_token = stored_refresh_token

            if token_expires_at:
                self._token_expires_at = datetime.fromisoformat(token_expires_at)

            # Check if token is expired
            if self._token_expires_at and datetime.utcnow() >= self._token_expires_at:
                # Try to refresh
                if self._refresh_token:
                    return await self._oauth_refresh_token()
                else:
                    raise TokenExpiredError("Access token expired and no refresh token available")

            return True

        # No stored tokens - require manual authorization
        raise AuthenticationError(
            "OAuth authorization code flow requires manual authorization. "
            "Please complete OAuth flow and store tokens in source configuration."
        )

    async def _oauth_refresh_token(self) -> bool:
        """
        Refresh OAuth access token using refresh token.

        Returns:
            True if refresh successful
        """
        try:
            token_url = self.oauth_config.get('token_url')
            client_id = self.oauth_config.get('client_id')
            client_secret = self.oauth_config.get('client_secret')

            if not all([token_url, client_id, client_secret, self._refresh_token]):
                raise AuthenticationError("Missing credentials for token refresh")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        'grant_type': 'refresh_token',
                        'refresh_token': self._refresh_token,
                        'client_id': client_id,
                        'client_secret': client_secret,
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                )

                response.raise_for_status()
                token_data = response.json()

                # Update tokens
                self._access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                # Update refresh token if provided
                if 'refresh_token' in token_data:
                    self._refresh_token = token_data['refresh_token']

                logger.info(f"OAuth token refreshed for {self.source_config.get('name')}")
                return True

        except Exception as e:
            logger.error(f"Token refresh failed: {e}", exc_info=True)
            raise AuthenticationError(f"Token refresh failed: {str(e)}")

    def is_token_expired(self) -> bool:
        """
        Check if OAuth token is expired or about to expire.

        Returns:
            True if token is expired or will expire in next 5 minutes
        """
        if not self._token_expires_at:
            return False

        # Consider token expired if it expires in next 5 minutes
        buffer = timedelta(minutes=5)
        return datetime.utcnow() >= (self._token_expires_at - buffer)

    async def ensure_authenticated(self) -> None:
        """
        Ensure authentication is valid, refreshing if necessary.

        Raises:
            AuthenticationError: If authentication cannot be established
        """
        # Check if we need to authenticate
        if self._access_token and not self.is_token_expired():
            # Already authenticated and token is valid
            return

        # Need to authenticate or refresh
        if self._refresh_token and self.is_token_expired():
            # Try to refresh
            try:
                await self._oauth_refresh_token()
                return
            except Exception as e:
                logger.warning(f"Token refresh failed, re-authenticating: {e}")

        # Perform full authentication
        await self.authenticate()

    def get_auth_params(self) -> Dict[str, str]:
        """
        Get authentication parameters for URL query string.

        Some APIs (like YouTube) use API keys as query parameters.

        Returns:
            Dictionary of query parameters
        """
        params = {}

        if self.source_type == 'youtube' and self.api_key:
            params['key'] = self.api_key

        return params


class RateLimiter:
    """
    Rate limiter for API requests.

    Implements token bucket algorithm with per-source limits.
    """

    def __init__(self, requests_per_hour: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_hour: Maximum requests allowed per hour
        """
        self.requests_per_hour = requests_per_hour
        self.tokens = requests_per_hour
        self.last_refill = datetime.utcnow()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire a token for making a request.

        Blocks if no tokens available until refill.
        """
        async with self.lock:
            # Refill tokens based on elapsed time
            now = datetime.utcnow()
            elapsed_hours = (now - self.last_refill).total_seconds() / 3600

            if elapsed_hours > 0:
                # Refill tokens proportionally
                tokens_to_add = int(self.requests_per_hour * elapsed_hours)
                self.tokens = min(self.tokens + tokens_to_add, self.requests_per_hour)
                self.last_refill = now

            # Wait if no tokens available
            while self.tokens <= 0:
                # Calculate wait time until next token
                seconds_per_token = 3600 / self.requests_per_hour
                await asyncio.sleep(seconds_per_token)

                # Refill one token
                self.tokens = 1
                self.last_refill = datetime.utcnow()

            # Consume a token
            self.tokens -= 1

    def get_available_tokens(self) -> int:
        """Get current number of available tokens."""
        return self.tokens


class AuthenticatedHttpClient:
    """
    HTTP client with authentication and rate limiting.

    Combines auth handler and rate limiter for making authenticated requests.
    """

    def __init__(
        self,
        auth_handler: AuthHandler,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: int = 30,
    ):
        """
        Initialize authenticated HTTP client.

        Args:
            auth_handler: Authentication handler
            rate_limiter: Rate limiter (optional)
            timeout: Request timeout in seconds
        """
        self.auth_handler = auth_handler
        self.rate_limiter = rate_limiter
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make an authenticated HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        # Ensure authenticated
        await self.auth_handler.ensure_authenticated()

        # Apply rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Get auth headers and params
        headers = kwargs.pop('headers', {})
        headers.update(self.auth_handler.get_auth_headers())

        params = kwargs.pop('params', {})
        params.update(self.auth_handler.get_auth_params())

        # Make request
        client = await self._get_client()
        response = await client.request(
            method,
            url,
            headers=headers,
            params=params,
            **kwargs
        )

        response.raise_for_status()
        return response

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make GET request."""
        return await self.request('GET', url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make POST request."""
        return await self.request('POST', url, **kwargs)

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
