from contextlib import contextmanager

import allure


@contextmanager
def step(page, title):
    with allure.step(title):
        try:
            yield
        finally:
            driver = getattr(page, "driver", None)
            if driver is not None:
                try:
                    allure.attach(
                        driver.get_screenshot_as_png(),
                        name=f"{title} - screenshot",
                        attachment_type=allure.attachment_type.PNG,
                    )
                except Exception:
                    pass
                try:
                    allure.attach(
                        f"URL: {driver.current_url}",
                        name=f"{title} - log",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                except Exception:
                    pass
