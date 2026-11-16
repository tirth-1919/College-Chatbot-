"""URL Validation & SSRF Protection Engine.

Provides rigorous pre-connection DNS validation, private IP blocking,
tenant domain boundary enforcement, and URL canonicalization.
"""

import ipaddress
import re
import socket
from typing import List, Optional, Set
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse


class SSRFProtectionError(ValueError):
    """Raised when a URL targets a private, internal, or restricted network destination."""
    pass


class DomainBoundaryError(ValueError):
    """Raised when a URL falls outside the college tenant's authorized domain scope."""
    pass


# Private, Link-Local, Loopback, Carrier-Grade NAT, and Cloud Metadata CIDR Blocks
BLOCKED_IPV4_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (only valid as source)
    ipaddress.ip_network("10.0.0.0/8"),         # Private-Use (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (CGNAT)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local & AWS/GCP/Azure Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # Private-Use (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1 (Documentation)
    ipaddress.ip_network("192.168.0.0/16"),     # Private-Use (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2 (Documentation)
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3 (Documentation)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved for Future Use
    ipaddress.ip_network("255.255.255.255/32"), # Limited Broadcast
]

BLOCKED_IPV6_NETWORKS = [
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6
    ipaddress.ip_network("64:ff9b::/96"),       # IPv4/IPv6 translation
    ipaddress.ip_network("100::/64"),           # Discard prefix
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Unicast
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

# Cloud Metadata & Internal Hostnames
BLOCKED_HOSTNAMES: Set[str] = {
    "localhost",
    "metadata",
    "metadata.google.internal",
    "instance-data",
    "169.254.169.254",
    "fd00:ec2::254",
    "local",
    "internal",
    "intranet",
}

# Permitted Web Protocols and Standard Web Ports
ALLOWED_SCHEMES: Set[str] = {"http", "https"}
ALLOWED_PORTS: Set[int] = {80, 443, 8080, 8443}

# File extensions to ignore during web text crawling (e.g., media, archives, binaries)
NON_HTML_EXTENSIONS: Set[str] = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
    ".exe", ".dmg", ".pkg", ".deb", ".rpm", ".iso", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp", ".tiff",
    ".mp4", ".mp3", ".avi", ".mov", ".wav", ".m4a", ".ogg", ".webm",
    ".css", ".js", ".json", ".xml", ".rss", ".atom",
    ".woff", ".woff2", ".ttf", ".eot", ".otf"
}

# Marketing tracking query parameters to strip for clean canonical URLs
TRACKING_PARAMS: Set[str] = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "ref", "source", "token", "session_id",
    "_hsenc", "_hsmi", "mc_cid", "mc_eid"
}


def is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Checks whether an IP address belongs to any private, loopback, link-local, or reserved network."""
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True

    if isinstance(ip, ipaddress.IPv4Address):
        for net in BLOCKED_IPV4_NETWORKS:
            if ip in net:
                return True
    elif isinstance(ip, ipaddress.IPv6Address):
        for net in BLOCKED_IPV6_NETWORKS:
            if ip in net:
                return True

    return False


def validate_url_security(url: str) -> str:
    """Validates URL protocol, port, hostname, and resolves DNS to prevent SSRF attacks.

    Args:
        url: Target URL to inspect.

    Returns:
        Clean, validated URL string.

    Raises:
        SSRFProtectionError: If scheme is forbidden, port is unsafe, or DNS points to a private/internal address.
    """
    if not url or not isinstance(url, str):
        raise SSRFProtectionError("Empty or invalid URL provided.")

    url = url.strip()
    parsed = urlparse(url)

    # 1. Scheme Check
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise SSRFProtectionError(
            f"Prohibited URL scheme '{scheme}'. Only HTTP and HTTPS protocols are permitted."
        )

    # 2. Hostname Check
    hostname = parsed.hostname
    if not hostname:
        raise SSRFProtectionError("URL is missing a valid hostname.")

    hostname_clean = hostname.lower().strip(".")

    # Direct hostname blocklist
    if hostname_clean in BLOCKED_HOSTNAMES:
        raise SSRFProtectionError(f"Access to restricted hostname '{hostname_clean}' is prohibited.")

    # Block local/internal TLDs
    if (
        hostname_clean.endswith(".local")
        or hostname_clean.endswith(".localhost")
        or hostname_clean.endswith(".internal")
        or hostname_clean.endswith(".lan")
    ):
        raise SSRFProtectionError(f"Access to internal domain suffix on '{hostname_clean}' is prohibited.")

    # 3. Port Check
    port = parsed.port
    if port is not None and port not in ALLOWED_PORTS:
        raise SSRFProtectionError(
            f"Access to non-standard port {port} is blocked. Permitted ports: {sorted(list(ALLOWED_PORTS))}."
        )

    # 4. Check if hostname is directly an IP address literal
    try:
        ip_obj = ipaddress.ip_address(hostname_clean)
        if is_ip_blocked(ip_obj):
            raise SSRFProtectionError(
                f"Direct access to private or reserved IP '{hostname_clean}' is prohibited."
            )
    except ValueError:
        # Not a raw IP literal, proceed to DNS resolution check
        pass

    # 5. Pre-connection DNS Resolution & Verification
    try:
        resolved_addrinfo = socket.getaddrinfo(hostname_clean, port or (443 if scheme == "https" else 80))
        resolved_ips = set()
        for item in resolved_addrinfo:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            resolved_ips.add(ip_str)

        if not resolved_ips:
            raise SSRFProtectionError(f"Unable to resolve DNS for hostname '{hostname_clean}'.")

        for ip_str in resolved_ips:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if is_ip_blocked(ip_obj):
                    raise SSRFProtectionError(
                        f"SSRF Alert: Hostname '{hostname_clean}' resolved to restricted IP address: {ip_str}."
                    )
            except ValueError:
                raise SSRFProtectionError(f"Invalid resolved IP format: {ip_str}.")

    except socket.gaierror as e:
        # If DNS lookup fails during validation, reject as unroutable host
        raise SSRFProtectionError(f"DNS lookup failed for hostname '{hostname_clean}': {str(e)}")

    return url


def clean_domain_string(domain: str) -> str:
    """Normalizes an official domain string to lowercase without protocol, ports, or paths."""
    d = domain.lower().strip()
    if "://" in d:
        d = urlparse(d).hostname or d
    d = d.split(":")[0].strip("/")
    return d


def is_url_in_college_domain(
    url: str,
    official_domain: str,
    allowed_subdomains: Optional[str] = None
) -> bool:
    """Enforces strict tenant domain boundaries for crawled links.

    Args:
        url: Target web page URL.
        official_domain: College's verified primary domain (e.g. 'aitindia.in').
        allowed_subdomains: Optional comma-separated or wildcard subdomains (e.g. 'admissions,engineering' or '*').

    Returns:
        True if the URL strictly belongs to the college tenant's approved web boundaries.
    """
    try:
        parsed = urlparse(url)
        target_host = (parsed.hostname or "").lower().strip(".")
        base_domain = clean_domain_string(official_domain)

        if not target_host or not base_domain:
            return False

        # Exact domain match (e.g., aitindia.in == aitindia.in or www.aitindia.in)
        if target_host == base_domain:
            return True
        if target_host == f"www.{base_domain}":
            return True
        if base_domain.startswith("www.") and target_host == base_domain[4:]:
            return True

        # Subdomain match (e.g. admissions.aitindia.in)
        if target_host.endswith(f".{base_domain}"):
            subdomain = target_host[: -(len(base_domain) + 1)]
            if not allowed_subdomains or allowed_subdomains.strip() in ("", "*"):
                return True

            allowed_list = [s.strip().lower() for s in allowed_subdomains.split(",") if s.strip()]
            for pattern in allowed_list:
                if pattern == "*" or pattern == subdomain or target_host.endswith(f".{pattern}.{base_domain}"):
                    return True
                if pattern in target_host:
                    return True

            return False

        return False
    except Exception:
        return False


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """Normalizes URL by resolving relative paths, lowercasing hostname, and removing tracking params.

    Args:
        url: Link discovered on a web page or submitted by user.
        base_url: Optional origin page URL for relative path resolution.

    Returns:
        Canonicalized absolute URL string.
    """
    if not url:
        return ""

    url = url.strip()

    # Resolve relative URL if base_url is provided
    if base_url:
        url = urljoin(base_url, url)

    parsed = urlparse(url)

    # Lowercase scheme and hostname
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove standard default ports (:80 on http, :443 on https)
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Normalize path (keep root '/', strip trailing slash for child routes)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Strip fragments and tracking queries
    query = ""
    if parsed.query:
        qs = parse_qs(parsed.query, keep_blank_values=True)
        filtered_qs = {k: v for k, v in qs.items() if k.lower() not in TRACKING_PARAMS}
        if filtered_qs:
            query = urlencode(filtered_qs, doseq=True)

    # Reconstruct canonical URL (fragment is completely dropped)
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def is_crawleable_resource(url: str) -> bool:
    """Determines whether a URL points to an HTML web page rather than a binary file, media, or script."""
    parsed = urlparse(url)
    path = parsed.path.lower()

    # Ignore non-web schemes
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False

    # Check file extension
    for ext in NON_HTML_EXTENSIONS:
        if path.endswith(ext):
            return False

    return True

