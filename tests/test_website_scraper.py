"""Tests for website scraper with SSRF protection."""

from __future__ import annotations

import ipaddress

import pytest

from sip_studio.brands.research.website_scraper import (
    SSRFError,
    _HTMLAssetParser,
    _is_global_ip,
    _validate_url,
    validate_url_for_scraping,
)


class TestSSRFValidation:
    def test_valid_https_url(self):
        scheme, host, port = _validate_url("https://example.com")
        assert scheme == "https"
        assert host == "example.com"
        assert port is None

    def test_valid_http_url(self):
        scheme, host, port = _validate_url("http://example.com:80/path")
        assert scheme == "http"
        assert host == "example.com"
        assert port == 80

    def test_rejects_file_scheme(self):
        with pytest.raises(SSRFError, match="Scheme.*not allowed"):
            _validate_url("file:///etc/passwd")

    def test_rejects_ftp_scheme(self):
        with pytest.raises(SSRFError, match="Scheme.*not allowed"):
            _validate_url("ftp://example.com")

    def test_rejects_data_scheme(self):
        with pytest.raises(SSRFError, match="Scheme.*not allowed"):
            _validate_url("data:text/html,<h1>test</h1>")

    def test_rejects_userinfo(self):
        with pytest.raises(SSRFError, match="userinfo not allowed"):
            _validate_url("https://user:pass@example.com")

    def test_rejects_username_only(self):
        with pytest.raises(SSRFError, match="userinfo not allowed"):
            _validate_url("https://user@example.com")

    def test_rejects_non_standard_port(self):
        with pytest.raises(SSRFError, match="Port.*not allowed"):
            _validate_url("https://example.com:8080")

    def test_rejects_no_hostname(self):
        with pytest.raises(SSRFError, match="No hostname"):
            _validate_url("https:///path")

    def test_allows_port_443(self):
        _, _, port = _validate_url("https://example.com:443")
        assert port == 443


class TestIPValidation:
    def test_global_ipv4(self):
        assert _is_global_ip(ipaddress.ip_address("8.8.8.8"))
        assert _is_global_ip(ipaddress.ip_address("93.184.216.34"))

    def test_private_ipv4_10(self):
        assert not _is_global_ip(ipaddress.ip_address("10.0.0.1"))
        assert not _is_global_ip(ipaddress.ip_address("10.255.255.255"))

    def test_private_ipv4_172(self):
        assert not _is_global_ip(ipaddress.ip_address("172.16.0.1"))
        assert not _is_global_ip(ipaddress.ip_address("172.31.255.255"))
        assert _is_global_ip(ipaddress.ip_address("172.32.0.1"))

    def test_private_ipv4_192(self):
        assert not _is_global_ip(ipaddress.ip_address("192.168.0.1"))
        assert not _is_global_ip(ipaddress.ip_address("192.168.255.255"))

    def test_localhost_ipv4(self):
        assert not _is_global_ip(ipaddress.ip_address("127.0.0.1"))
        assert not _is_global_ip(ipaddress.ip_address("127.255.255.255"))

    def test_link_local_ipv4(self):
        assert not _is_global_ip(ipaddress.ip_address("169.254.1.1"))

    def test_cgnat_ipv4(self):
        assert not _is_global_ip(ipaddress.ip_address("100.64.0.1"))

    def test_documentation_ipv4(self):
        assert not _is_global_ip(ipaddress.ip_address("192.0.2.1"))
        assert not _is_global_ip(ipaddress.ip_address("198.51.100.1"))
        assert not _is_global_ip(ipaddress.ip_address("203.0.113.1"))

    def test_global_ipv6(self):
        assert _is_global_ip(ipaddress.ip_address("2001:4860:4860::8888"))

    def test_localhost_ipv6(self):
        assert not _is_global_ip(ipaddress.ip_address("::1"))

    def test_unspecified_ipv6(self):
        assert not _is_global_ip(ipaddress.ip_address("::"))

    def test_link_local_ipv6(self):
        assert not _is_global_ip(ipaddress.ip_address("fe80::1"))

    def test_unique_local_ipv6(self):
        assert not _is_global_ip(ipaddress.ip_address("fc00::1"))
        assert not _is_global_ip(ipaddress.ip_address("fd00::1"))

    def test_multicast_ipv6(self):
        assert not _is_global_ip(ipaddress.ip_address("ff02::1"))


class TestHTMLParsing:
    def test_extract_meta_description(self):
        html = (
            '<html><head><meta name="description" content="Test brand description"></head></html>'
        )
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert a.meta_description == "Test brand description"

    def test_extract_og_tags(self):
        html = """<html><head>
        <meta property="og:title" content="Brand Name">
        <meta property="og:description" content="OG desc">
        <meta property="og:image" content="https://example.com/img.jpg">
        </head></html>"""
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert a.og_title == "Brand Name"
        assert a.og_description == "OG desc"
        assert a.og_image == "https://example.com/img.jpg"

    def test_extract_theme_color(self):
        html = '<html><head><meta name="theme-color" content="#FF5500"></head></html>'
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert a.theme_color == "#FF5500"

    def test_extract_headlines(self):
        html = (
            "<html><body><h1>Welcome to Brand</h1><h2>About Us</h2><h2>Products</h2></body></html>"
        )
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert "Welcome to Brand" in a.headlines
        assert "About Us" in a.headlines
        assert "Products" in a.headlines

    def test_extract_hex_colors_from_style(self):
        html = "<html><head><style>body{color:#FF0000;background:#00ff00;}</style></head></html>"
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert "#FF0000" in a.colors
        assert "#00FF00" in a.colors

    def test_extract_rgb_colors_from_inline_style(self):
        html = '<html><body><div style="color:rgb(255,128,0)">test</div></body></html>'
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert "#FF8000" in a.colors

    def test_extract_favicon(self):
        html = '<html><head><link rel="icon" href="/favicon.ico"></head></html>'
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert a.favicon_url == "/favicon.ico"

    def test_extract_logo_from_img_alt(self):
        html = '<html><body><img src="/images/logo.png" alt="Company Logo"></body></html>'
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert "/images/logo.png" in a.logo_candidates

    def test_extract_logo_from_img_src(self):
        html = '<html><body><img src="/assets/brand-logo.svg"></body></html>'
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert "/assets/brand-logo.svg" in a.logo_candidates

    def test_limits_colors(self):
        colors = "".join([f".c{i}{{color:#{i:06x};}}" for i in range(30)])
        html = f"<html><head><style>{colors}</style></head></html>"
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert len(a.colors) <= 20

    def test_limits_headlines(self):
        headlines = "".join([f"<h2>Headline {i}</h2>" for i in range(15)])
        html = f"<html><body>{headlines}</body></html>"
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert len(a.headlines) <= 10

    def test_handles_malformed_html(self):
        html = '<html><head><meta name="description" content="test"<body><h1>Title</h1>'
        p = _HTMLAssetParser()
        p.feed(html)
        a = p.get_assets()
        assert isinstance(a.colors, list)


class TestURLValidation:
    def test_validate_url_for_scraping_valid(self):
        err = validate_url_for_scraping("https://example.com")
        assert err is None

    def test_validate_url_for_scraping_invalid_scheme(self):
        err = validate_url_for_scraping("file:///etc/passwd")
        assert err is not None
        assert "Scheme" in err

    def test_validate_url_for_scraping_invalid_port(self):
        err = validate_url_for_scraping("https://example.com:8080")
        assert err is not None
        assert "Port" in err

    def test_validate_url_for_scraping_userinfo(self):
        err = validate_url_for_scraping("https://user:pass@example.com")
        assert err is not None
        assert "userinfo" in err
