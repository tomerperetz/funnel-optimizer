"""Meta OAuth flow for long-lived page tokens."""

import http.server
import json
import secrets
import socketserver
import urllib.parse
import webbrowser
from dataclasses import dataclass
from typing import Optional

import requests

from funnel_optimizer.config import get_settings

# OAuth configuration
REDIRECT_PORT = 9473  # Unusual port to avoid conflicts with Jupyter (8888), etc.
DEFAULT_REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"

# Can be overridden for ngrok/production
_redirect_uri_override: str | None = None


def set_redirect_uri(uri: str) -> None:
    """Set custom redirect URI (e.g., ngrok URL)."""
    global _redirect_uri_override
    _redirect_uri_override = uri


def get_redirect_uri() -> str:
    """Get current redirect URI."""
    return _redirect_uri_override or DEFAULT_REDIRECT_URI

# Permissions needed for lead gen campaigns
SCOPES = [
    "pages_manage_ads",
    "pages_read_engagement",
    "pages_show_list",
    "leads_retrieval",
    "ads_management",
    "ads_read",
    "business_management",
]


@dataclass
class TokenInfo:
    """Information about an access token."""
    access_token: str
    token_type: str = "user"  # "user" or "page"
    expires_in: Optional[int] = None  # seconds, None = never expires
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    scopes: list[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []


@dataclass
class PageInfo:
    """Information about a Facebook Page."""
    id: str
    name: str
    access_token: str  # Long-lived page token


def generate_auth_url() -> tuple[str, str]:
    """Generate Meta OAuth URL and state token.

    Returns:
        Tuple of (auth_url, state_token)
    """
    settings = get_settings()

    if not settings.meta_app_id:
        raise ValueError("FO_META_APP_ID not set in .env")

    state = secrets.token_urlsafe(16)

    params = {
        "client_id": settings.meta_app_id,
        "redirect_uri": get_redirect_uri(),
        "state": state,
        "scope": ",".join(SCOPES),
        "response_type": "code",
    }

    url = f"https://www.facebook.com/{settings.meta_api_version}/dialog/oauth?" + urllib.parse.urlencode(params)

    return url, state


def exchange_code_for_token(code: str) -> TokenInfo:
    """Exchange authorization code for short-lived access token.

    Args:
        code: Authorization code from OAuth callback

    Returns:
        TokenInfo with short-lived user access token
    """
    settings = get_settings()

    if not settings.meta_app_id or not settings.meta_app_secret:
        raise ValueError("FO_META_APP_ID and FO_META_APP_SECRET must be set in .env")

    url = f"https://graph.facebook.com/{settings.meta_api_version}/oauth/access_token"
    params = {
        "client_id": settings.meta_app_id,
        "client_secret": settings.meta_app_secret,
        "redirect_uri": get_redirect_uri(),
        "code": code,
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    return TokenInfo(
        access_token=data["access_token"],
        token_type="user",
        expires_in=data.get("expires_in"),
    )


def exchange_for_long_lived_token(short_lived_token: str) -> TokenInfo:
    """Exchange short-lived token for long-lived user token (60 days).

    Args:
        short_lived_token: Short-lived user access token

    Returns:
        TokenInfo with long-lived user access token
    """
    settings = get_settings()

    url = f"https://graph.facebook.com/{settings.meta_api_version}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": settings.meta_app_id,
        "client_secret": settings.meta_app_secret,
        "fb_exchange_token": short_lived_token,
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    return TokenInfo(
        access_token=data["access_token"],
        token_type="user",
        expires_in=data.get("expires_in"),  # ~60 days in seconds
    )


def get_user_pages(user_token: str) -> list[PageInfo]:
    """Get list of pages the user manages with long-lived page tokens.

    Args:
        user_token: Long-lived user access token

    Returns:
        List of PageInfo with never-expiring page tokens
    """
    settings = get_settings()

    url = f"https://graph.facebook.com/{settings.meta_api_version}/me/accounts"
    params = {
        "access_token": user_token,
        "fields": "id,name,access_token",
    }

    pages = []
    while url:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        for page in data.get("data", []):
            pages.append(PageInfo(
                id=page["id"],
                name=page["name"],
                access_token=page["access_token"],  # This is already long-lived
            ))

        # Handle pagination
        url = data.get("paging", {}).get("next")
        params = {}  # Next URL includes params

    return pages


def debug_token(token: str) -> dict:
    """Get debug info about a token (expiry, scopes, etc).

    Args:
        token: Access token to debug

    Returns:
        Dict with token debug info
    """
    settings = get_settings()

    url = f"https://graph.facebook.com/{settings.meta_api_version}/debug_token"
    params = {
        "input_token": token,
        "access_token": f"{settings.meta_app_id}|{settings.meta_app_secret}",
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get("data", {})


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    # Class variables to store result
    auth_code: Optional[str] = None
    auth_error: Optional[str] = None
    expected_state: Optional[str] = None

    def do_GET(self):
        """Handle GET request from OAuth redirect."""
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)

        # Check for error
        if "error" in params:
            OAuthCallbackHandler.auth_error = params.get("error_description", ["Unknown error"])[0]
            self._send_response("Authentication failed. You can close this window.")
            return

        # Verify state
        state = params.get("state", [None])[0]
        if state != OAuthCallbackHandler.expected_state:
            OAuthCallbackHandler.auth_error = "State mismatch - possible CSRF attack"
            self._send_response("Authentication failed (state mismatch). You can close this window.")
            return

        # Get code
        code = params.get("code", [None])[0]
        if not code:
            OAuthCallbackHandler.auth_error = "No authorization code received"
            self._send_response("Authentication failed. You can close this window.")
            return

        OAuthCallbackHandler.auth_code = code
        self._send_response("Authentication successful! You can close this window.")

    def _send_response(self, message: str):
        """Send HTML response."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Funnel Optimizer Auth</title></head>
        <body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
            <div style="text-align: center;">
                <h1>{message}</h1>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def run_oauth_flow(open_browser: bool = True) -> tuple[TokenInfo, list[PageInfo]]:
    """Run the complete OAuth flow.

    1. Generate auth URL
    2. Start local server for callback (before opening browser!)
    3. Open browser / print URL
    4. Wait for callback
    5. Exchange code for short-lived token
    6. Exchange for long-lived token
    7. Get page tokens

    Args:
        open_browser: Whether to automatically open the browser

    Returns:
        Tuple of (long_lived_user_token, list_of_pages_with_tokens)
    """
    # Generate auth URL
    auth_url, state = generate_auth_url()
    OAuthCallbackHandler.expected_state = state
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.auth_error = None

    # Use SO_REUSEADDR to avoid "address already in use" errors
    socketserver.TCPServer.allow_reuse_address = True

    # Start server FIRST
    try:
        httpd = socketserver.TCPServer(("127.0.0.1", REDIRECT_PORT), OAuthCallbackHandler)
    except OSError as e:
        raise RuntimeError(f"Cannot start callback server on port {REDIRECT_PORT}: {e}")

    print(f"\n{'='*60}")
    print(f"Callback server READY on http://localhost:{REDIRECT_PORT}/callback")
    print(f"{'='*60}\n")

    print(f"Open this URL to authenticate:\n")
    print(f"  {auth_url}\n")

    if open_browser:
        print("Opening browser...")
        webbrowser.open(auth_url)
    else:
        print("(Copy and paste the URL above into your browser)")

    print(f"\nWaiting for Facebook to redirect back...")
    print(f"(Keep this terminal open until you complete login)\n")

    try:
        httpd.handle_request()  # Handle single request (blocks until callback)
    finally:
        httpd.server_close()

    # Check for errors
    if OAuthCallbackHandler.auth_error:
        raise ValueError(f"OAuth failed: {OAuthCallbackHandler.auth_error}")

    if not OAuthCallbackHandler.auth_code:
        raise ValueError("No authorization code received")

    print("Received authorization code, exchanging for tokens...")

    # Exchange for tokens
    short_token = exchange_code_for_token(OAuthCallbackHandler.auth_code)
    print("Got short-lived token, exchanging for long-lived token...")

    long_token = exchange_for_long_lived_token(short_token.access_token)
    print(f"Got long-lived user token (expires in {long_token.expires_in // 86400} days)")

    # Get page tokens
    print("Fetching page tokens...")
    pages = get_user_pages(long_token.access_token)
    print(f"Found {len(pages)} page(s)")

    return long_token, pages


