"""Headless Browser JavaScript Renderer.

Provides a Playwright-backed async function to fetch the fully-rendered HTML of
a JavaScript-heavy page.  Used as a fallback when static HTML extraction
returns insufficient content.

If Playwright is not installed, ``PLAYWRIGHT_AVAILABLE`` is ``False`` and
calling ``render_page_with_browser`` raises ``RuntimeError`` immediately so the
caller can apply graceful degradation.
"""

from urllib.parse import urlparse

try:
    from playwright.async_api import async_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


async def render_page_with_browser(url: str, timeout_ms: int = 15000) -> str:
    """Renders a page with a headless Chromium browser and returns the full HTML.

    Args:
        url: The page URL to render.  Must already have passed SSRF validation
             before this function is called; this function only checks that the
             final rendered page stays on the same hostname.
        timeout_ms: Navigation timeout in milliseconds.  Defaults to 15 000 ms.

    Returns:
        Full page HTML after JavaScript execution as a string.

    Raises:
        RuntimeError: If Playwright is not installed.
        RuntimeError: If the browser navigates to a different hostname than
                      the one in ``url`` (cross-domain redirect detected).
        Exception: Re-raises Playwright ``TimeoutError`` or other browser
                   errors — the caller is responsible for fallback handling.
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright not installed")

    expected_hostname = urlparse(url).hostname or ""

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)

            # Validate that the final URL hasn't escaped to a different domain
            final_url = page.url
            final_hostname = urlparse(final_url).hostname or ""
            if final_hostname and expected_hostname and final_hostname != expected_hostname:
                raise RuntimeError(
                    f"JS renderer: cross-domain redirect detected — "
                    f"started at '{expected_hostname}', ended at '{final_hostname}'. "
                    f"Refusing to return content from '{final_url}'."
                )

            html = await page.content()
            return html
        finally:
            await browser.close()
