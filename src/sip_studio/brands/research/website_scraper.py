"""Website scraper with SSRF protection for brand asset extraction."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from sip_studio.brands.research.models import WebsiteAssets

logger = logging.getLogger(__name__)
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
GLOBAL_TIMEOUT_SECS = 30
MAX_RETRIES = 3
MAX_REDIRECTS = 5
ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({80, 443, None})
# Non-global IPv4 ranges per IANA
PRIVATE_IPV4_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
]
# Non-global IPv6 ranges
PRIVATE_IPV6_NETWORKS = [
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
]


class SSRFError(Exception):
    """Raised when SSRF protection blocks a request."""


class RetryableError(Exception):
    """Transient error that can be retried."""


class MaxRetriesError(Exception):
    """All retries exhausted."""


class ContentTooLargeError(Exception):
    """Response exceeds size limit."""


class InvalidContentTypeError(Exception):
    """Response is not HTML."""


def _is_global_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if IP is globally routable (not private/reserved)."""
    if isinstance(ip, ipaddress.IPv4Address):
        for net in PRIVATE_IPV4_NETWORKS:
            if ip in net:
                return False
    else:
        for net in PRIVATE_IPV6_NETWORKS:
            if ip in net:
                return False
        if ip.ipv4_mapped:
            return _is_global_ip(ip.ipv4_mapped)
    return True


def _validate_url(url: str) -> tuple[str, str, int | None]:
    """Validate URL and return (scheme, host, port). Raises SSRFError if invalid."""
    try:
        p = urlparse(url)
    except Exception as e:
        raise SSRFError(f"Invalid URL: {e}")
    if p.scheme not in ALLOWED_SCHEMES:
        raise SSRFError(f"Scheme {p.scheme!r} not allowed")
    if p.username or p.password:
        raise SSRFError("URLs with userinfo not allowed")
    if not p.hostname:
        raise SSRFError("No hostname in URL")
    port = p.port
    if port not in ALLOWED_PORTS:
        raise SSRFError(f"Port {port} not allowed")
    return p.scheme, p.hostname, port


async def _resolve_and_validate_host(hostname: str) -> list[str]:
    """Resolve hostname and validate all IPs are global. Returns validated IPs."""
    loop = asyncio.get_event_loop()
    try:
        infos = await loop.run_in_executor(
            None, lambda: socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        )
    except socket.gaierror as e:
        raise SSRFError(f"DNS resolution failed: {e}")
    if not infos:
        raise SSRFError("DNS returned no addresses")
    valid_ips: list[str] = []
    for _, _, _, _, sockaddr in infos:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if not _is_global_ip(ip):
            raise SSRFError(f"Resolved to non-global IP: {ip}")
        valid_ips.append(ip_str)
    if not valid_ips:
        raise SSRFError("No valid global IPs resolved")
    return valid_ips


class _HTMLAssetParser(HTMLParser):
    """Extract brand-relevant assets from HTML."""

    def __init__(self):
        super().__init__()
        self.colors: list[str] = []
        self.meta: dict[str, str] = {}
        self.headlines: list[str] = []
        self.logo_candidates: list[str] = []
        self.favicon_url: str = ""
        self._in_style = False
        self._style_content = ""
        self._in_h1 = False
        self._in_h2 = False
        self._current_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        a = dict(attrs)
        if tag == "meta":
            name = (a.get("name") or "").lower()
            prop = (a.get("property") or "").lower()
            content = a.get("content") or ""
            if name == "description":
                self.meta["description"] = content
            elif name == "theme-color":
                self.meta["theme-color"] = content
            elif prop == "og:title":
                self.meta["og:title"] = content
            elif prop == "og:description":
                self.meta["og:description"] = content
            elif prop == "og:image":
                self.meta["og:image"] = content
        elif tag == "link":
            rel = (a.get("rel", "") or "").lower()
            href = a.get("href", "") or ""
            if "icon" in rel and href:
                if "apple" not in rel:
                    self.favicon_url = href
            elif "logo" in rel and href:
                self.logo_candidates.append(href)
        elif tag == "img":
            src = a.get("src", "") or ""
            alt = (a.get("alt", "") or "").lower()
            if src and any(k in alt for k in ("logo", "brand")):
                self.logo_candidates.append(src)
            elif src and any(k in src.lower() for k in ("logo", "brand")):
                self.logo_candidates.append(src)
        elif tag == "style":
            self._in_style = True
        elif tag == "h1":
            self._in_h1 = True
            self._current_text = ""
        elif tag == "h2":
            self._in_h2 = True
            self._current_text = ""
        # Extract colors from inline style
        style = a.get("style", "") or ""
        if style:
            self._extract_colors_from_css(style)

    def handle_endtag(self, tag: str):
        if tag == "style":
            self._in_style = False
            self._extract_colors_from_css(self._style_content)
            self._style_content = ""
        elif tag == "h1":
            if self._current_text.strip():
                self.headlines.append(self._current_text.strip())
            self._in_h1 = False
        elif tag == "h2":
            if self._current_text.strip():
                self.headlines.append(self._current_text.strip())
            self._in_h2 = False

    def handle_data(self, data: str):
        if self._in_style:
            self._style_content += data
        elif self._in_h1 or self._in_h2:
            self._current_text += data

    def _extract_colors_from_css(self, css: str):
        # Hex colors: #RGB, #RRGGBB, #RRGGBBAA
        hex_pattern = r"#(?:[0-9a-fA-F]{3}){1,2}(?:[0-9a-fA-F]{2})?"
        for m in re.findall(hex_pattern, css):
            c = m.upper()
            if c not in self.colors:
                self.colors.append(c)
        # RGB/RGBA colors
        rgb_pattern = r"rgba?\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})"
        for m in re.findall(rgb_pattern, css):
            r, g, b = int(m[0]), int(m[1]), int(m[2])
            if all(0 <= x <= 255 for x in (r, g, b)):
                hx = f"#{r:02X}{g:02X}{b:02X}"
                if hx not in self.colors:
                    self.colors.append(hx)

    def get_assets(self) -> WebsiteAssets:
        return WebsiteAssets(
            colors=self.colors[:20],
            meta_description=self.meta.get("description", ""),
            og_title=self.meta.get("og:title", ""),
            og_description=self.meta.get("og:description", ""),
            og_image=self.meta.get("og:image", ""),
            theme_color=self.meta.get("theme-color", ""),
            headlines=self.headlines[:10],
            logo_candidates=self.logo_candidates[:5],
            favicon_url=self.favicon_url,
        )


async def _fetch_with_ssrf_protection(
    client: httpx.AsyncClient, url: str, visited: set[str]
) -> tuple[bytes, str]:
    """Fetch URL with SSRF protection, handling redirects manually. Returns (content, final_url)."""
    if url in visited:
        raise SSRFError("Redirect loop detected")
    if len(visited) >= MAX_REDIRECTS:
        raise SSRFError(f"Exceeded max redirects ({MAX_REDIRECTS})")
    visited.add(url)
    scheme, hostname, port = _validate_url(url)
    await _resolve_and_validate_host(hostname)
    resp = await client.get(url, follow_redirects=False)
    if resp.is_redirect:
        loc = resp.headers.get("location", "")
        if not loc:
            raise SSRFError("Redirect without Location header")
        # Resolve relative redirects
        if loc.startswith("/"):
            loc = f"{scheme}://{hostname}{':'+str(port) if port else ''}{loc}"
        elif not loc.startswith(("http://", "https://")):
            loc = f"{scheme}://{hostname}/{loc}"
        return await _fetch_with_ssrf_protection(client, loc, visited)
    content_type = resp.headers.get("content-type", "").lower()
    if "text/html" not in content_type:
        raise InvalidContentTypeError(f"Content-Type {content_type!r} is not HTML")
    # Stream response with size limit
    chunks: list[bytes] = []
    total = 0
    async for chunk in resp.aiter_bytes(8192):
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise ContentTooLargeError(f"Response exceeds {MAX_RESPONSE_BYTES} bytes")
        chunks.append(chunk)
    return b"".join(chunks), str(resp.url)


async def _scrape_attempt(url: str) -> WebsiteAssets:
    """Single scrape attempt."""
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(GLOBAL_TIMEOUT_SECS), trust_env=False
    ) as client:
        content, _ = await _fetch_with_ssrf_protection(client, url, set())
    try:
        html = content.decode("utf-8", errors="replace")
    except Exception:
        html = content.decode("latin-1", errors="replace")
    parser = _HTMLAssetParser()
    try:
        parser.feed(html)
    except Exception as e:
        logger.warning("HTML parsing error: %s", e)
    return parser.get_assets()


async def scrape_website(url: str) -> WebsiteAssets:
    """Scrape brand assets from URL with SSRF protection and retries.
    Args:
        url: Website URL to scrape
    Returns:
        WebsiteAssets with extracted brand information
    Raises:
        SSRFError: If URL is blocked for security reasons
        MaxRetriesError: If all retries fail
        asyncio.TimeoutError: If global deadline exceeded
    """
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            async with asyncio.timeout(GLOBAL_TIMEOUT_SECS):
                return await _scrape_attempt(url)
        except (SSRFError, InvalidContentTypeError):
            raise
        except (
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            ContentTooLargeError,
        ) as e:
            last_err = e
            logger.warning("Scrape attempt %d failed: %s", attempt + 1, e)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(min(2**attempt, 8))
        except Exception as e:
            last_err = e
            logger.error("Unexpected scrape error: %s", e)
            break
    raise MaxRetriesError(f"Failed after {MAX_RETRIES} attempts: {last_err}")


def validate_url_for_scraping(url: str) -> str | None:
    """Validate URL before starting a job. Returns error message or None if valid."""
    try:
        _validate_url(url)
        return None
    except SSRFError as e:
        return str(e)
