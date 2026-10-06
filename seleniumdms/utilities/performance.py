import allure

_TIMING_SCRIPT = """
const nav = performance.getEntriesByType('navigation')[0];
if (!nav) return null;
return {
    url: location.href,
    ttfb_ms: Math.round(nav.responseStart - nav.requestStart),
    dom_interactive_ms: Math.round(nav.domInteractive - nav.startTime),
    dom_content_loaded_ms: Math.round(nav.domContentLoadedEventEnd - nav.startTime),
    page_load_ms: Math.round(nav.loadEventEnd - nav.startTime),
};
"""


def get_navigation_timing(driver):
    return driver.execute_script(_TIMING_SCRIPT)


def attach_page_performance(driver, label):
    try:
        timing = get_navigation_timing(driver)
    except Exception:
        return None
    if not timing:
        return None
    allure.attach(
        f"Page: {label}\n"
        f"URL: {timing['url']}\n"
        f"Time To First Byte: {timing['ttfb_ms']} ms\n"
        f"DOM Interactive: {timing['dom_interactive_ms']} ms\n"
        f"DOM Content Loaded: {timing['dom_content_loaded_ms']} ms\n"
        f"Full Page Load: {timing['page_load_ms']} ms",
        name=f"Performance - {label}",
        attachment_type=allure.attachment_type.TEXT,
    )
    return timing
