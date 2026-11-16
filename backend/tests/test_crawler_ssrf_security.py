"""Web Crawler SSRF & Domain Boundary Security Unit Tests."""

import ipaddress
import pytest
from app.services.url_validator import (
    validate_url_security,
    is_url_in_college_domain,
    is_ip_blocked,
    SSRFProtectionError,
    DomainBoundaryError,
)


def test_ssrf_blocked_localhost_and_loopback():
    """Verifies that localhost, 127.0.0.1, and ::1 are strictly blocked as SSRF risks."""
    blocked_urls = [
        "http://localhost:8000/internal-admin",
        "http://127.0.0.1:8080/debug",
        "http://127.0.1.1/secret",
        "https://[::1]/admin",
    ]
    for url in blocked_urls:
        with pytest.raises(SSRFProtectionError):
            validate_url_security(url)


def test_ssrf_blocked_cloud_metadata():
    """Verifies that AWS/GCP/Azure link-local metadata IPs and hostnames are rejected."""
    metadata_targets = [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://169.254.169.254/metadata/v1.json",
    ]
    for url in metadata_targets:
        with pytest.raises(SSRFProtectionError):
            validate_url_security(url)


def test_ssrf_blocked_private_ip_networks():
    """Verifies that RFC 1918 private IPv4 subnets are rejected."""
    private_ips = [
        ipaddress.ip_address("10.0.0.1"),
        ipaddress.ip_address("10.254.0.5"),
        ipaddress.ip_address("172.16.0.1"),
        ipaddress.ip_address("172.31.255.255"),
        ipaddress.ip_address("192.168.1.1"),
        ipaddress.ip_address("192.168.0.254"),
    ]
    for ip in private_ips:
        assert is_ip_blocked(ip) is True, f"Private IP {ip} must be blocked by SSRF filter"


def test_domain_boundary_enforcement():
    """Verifies that crawler requests outside the registered college domain are rejected."""
    approved_domain = "ait.edu.in"

    # Within domain
    assert is_url_in_college_domain("https://ait.edu.in/about-us", approved_domain) is True
    assert is_url_in_college_domain("https://ait.edu.in/admissions/fees", approved_domain) is True

    # Allowed subdomains
    assert is_url_in_college_domain("https://admissions.ait.edu.in/portal", approved_domain, allowed_subdomains="admissions,exam") is True
    assert is_url_in_college_domain("https://exam.ait.edu.in/schedule", approved_domain, allowed_subdomains="admissions,exam") is True

    # Disallowed third-party domains
    assert is_url_in_college_domain("https://malicious-site.com/ait", approved_domain) is False
    assert is_url_in_college_domain("https://google.com", approved_domain) is False
    assert is_url_in_college_domain("https://fakeait.edu.in", approved_domain) is False


def test_disallowed_url_schemes():
    """Verifies that non-HTTP/HTTPS schemes (file://, gopher://, ftp://) are rejected."""
    dangerous_schemes = [
        "file:///etc/passwd",
        "file:///C:/Windows/System32/drivers/etc/hosts",
        "ftp://ftp.example.com/files",
        "gopher://gopher.example.com/",
    ]
    for url in dangerous_schemes:
        with pytest.raises(SSRFProtectionError):
            validate_url_security(url)
