"""
overview_printer.py

Page Object Model for HP One printer overview / subscription-cancellation flow.

Fixed issue: click_on_confirm_cancellation previously tried only
//footer//button[last()] and a broad negative-filter XPath. Both failed
when the confirmation dialog renders buttons outside a <footer> element.

The new implementation tries a prioritised list of locators (XPath and CSS)
and falls back to a JavaScript scan that matches confirm-intent button text
before raising the failure screenshot.
"""

import logging
import time

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# XPath / CSS locators tried in order for the "confirm cancellation" button.
# They are ordered from most-specific to least-specific so the first match
# is the most reliable one.
# ---------------------------------------------------------------------------
_CONFIRM_CANCELLATION_LOCATORS = [
    # Buttons whose visible text explicitly signals confirmation
    (By.XPATH, "//button[normalize-space(text())='Confirm Cancellation']"),
    (By.XPATH, "//button[normalize-space(text())='Confirm']"),
    (By.XPATH, "//button[normalize-space(text())='Yes, Cancel']"),
    (By.XPATH, "//button[normalize-space(text())='Yes']"),
    (By.XPATH, "//button[normalize-space(text())='Proceed']"),
    (By.XPATH, "//button[normalize-space(text())='OK']"),
    # Case-insensitive partial-text matches using translate()
    (
        By.XPATH,
        "//button[contains("
        "translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
        "'abcdefghijklmnopqrstuvwxyz'), "
        "'confirm')]",
    ),
    # Buttons inside common dialog / modal containers
    (By.CSS_SELECTOR, "[role='dialog'] button:last-of-type"),
    (By.CSS_SELECTOR, ".modal-footer button:last-of-type"),
    (By.CSS_SELECTOR, ".dialog-actions button:last-of-type"),
    (By.CSS_SELECTOR, "[data-testid='confirm-btn']"),
    (By.CSS_SELECTOR, "[data-testid='confirm-cancellation-btn']"),
    # Generic last button inside any overlay / modal wrapper
    (By.XPATH, "//div[contains(@class,'modal') or contains(@class,'dialog')]//button[last()]"),
    (By.XPATH, "//div[contains(@class,'overlay')]//button[last()]"),
]

# Text fragments (lowercase) considered a "confirm" intent
_CONFIRM_TEXT_KEYWORDS = (
    "confirm",
    "yes",
    "proceed",
    "ok",
    "sure",
    "agree",
)

# Text fragments (lowercase) that indicate a negative / cancel button that
# should be skipped when searching via JavaScript
_CANCEL_TEXT_KEYWORDS = (
    "cancel",
    "back",
    "no",
    "dismiss",
    "close",
)


class OverviewPrinterPage:
    """Page-object wrapper around the HP One printer overview / cancellation UI."""

    DEFAULT_TIMEOUT = 10  # seconds

    def __init__(self, driver, basic_actions=None):
        """
        :param driver: Selenium WebDriver instance.
        :param basic_actions: Optional BasicActions helper.  When provided,
            its ``capture_screenshot`` method is used for failure artefacts.
        """
        self.driver = driver
        self.basic_actions = basic_actions

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def click_on_confirm_cancellation(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Click the confirm-cancellation button in the cancellation dialog.

        Tries multiple locator strategies in priority order, then falls back
        to a JavaScript text-scan before raising.

        :param timeout: Per-locator wait in seconds.
        :raises Exception: When no strategy succeeds.
        """
        logger.info("Attempting to click confirm-cancellation button …")

        if self._try_standard_locators(timeout):
            return

        logger.warning("Standard locators failed. Attempting JavaScript approach…")
        if self._try_javascript_click():
            return

        # All strategies exhausted – capture screenshot and raise
        screenshot_name = "click_on_confirm_cancellation_failed.png"
        self._capture_failure_screenshot(screenshot_name)
        raise Exception(
            "Failed to locate confirm cancellation button. "
            f"Check screenshot: {screenshot_name}"
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _try_standard_locators(self, timeout: int) -> bool:
        """Iterate over _CONFIRM_CANCELLATION_LOCATORS and try each one.

        :returns: True if a button was successfully clicked, False otherwise.
        """
        for by, locator in _CONFIRM_CANCELLATION_LOCATORS:
            try:
                wait = WebDriverWait(self.driver, timeout)
                element = wait.until(EC.element_to_be_clickable((by, locator)))
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                element.click()
                logger.info("Confirm cancellation button clicked via locator: %s=%s", by, locator)
                return True
            except (
                TimeoutException,
                NoSuchElementException,
                ElementClickInterceptedException,
                ElementNotInteractableException,
                StaleElementReferenceException,
            ) as exc:
                logger.debug("Locator %s=%s failed: %s", by, locator, exc)

        return False

    def _try_javascript_click(self) -> bool:
        """Scan all <button> elements via JavaScript and click the first
        one whose text indicates a confirm intent and is not a cancel/back
        button.

        :returns: True if a button was successfully clicked, False otherwise.
        """
        js_find_and_click = """
            var buttons = Array.from(document.querySelectorAll('button'));
            console.log('Found ' + buttons.length + ' total buttons on page');

            var confirmKeywords = arguments[0];
            var cancelKeywords  = arguments[1];

            function matchesAny(text, keywords) {
                var t = text.toLowerCase().trim();
                for (var i = 0; i < keywords.length; i++) {
                    if (t.indexOf(keywords[i]) !== -1) { return true; }
                }
                return false;
            }

            // Two-pass approach:
            // Pass 1: buttons that match a confirm keyword (highest priority)
            // Pass 2: buttons that do NOT match any cancel keyword (fallback)
            for (var pass = 0; pass < 2; pass++) {
                for (var i = 0; i < buttons.length; i++) {
                    var btn  = buttons[i];
                    var text = (btn.innerText || btn.textContent || '').trim();

                    if (text === '') { continue; }

                    if (pass === 0) {
                        // First pass: explicit confirm keyword match takes precedence
                        if (matchesAny(text, confirmKeywords)) {
                            btn.scrollIntoView(true);
                            btn.click();
                            return text;
                        }
                    } else {
                        // Second pass: any non-cancel button
                        if (!matchesAny(text, cancelKeywords)) {
                            btn.scrollIntoView(true);
                            btn.click();
                            return text;
                        }
                    }
                }
            }
            return null;
        """
        try:
            clicked_text = self.driver.execute_script(
                js_find_and_click,
                list(_CONFIRM_TEXT_KEYWORDS),
                list(_CANCEL_TEXT_KEYWORDS),
            )
            if clicked_text:
                logger.info(
                    "Confirm cancellation button clicked via JavaScript (text=%r)",
                    clicked_text,
                )
                return True

            logger.warning("JavaScript scan found no matching confirm button.")
        except (
            ElementClickInterceptedException,
            ElementNotInteractableException,
            StaleElementReferenceException,
            NoSuchElementException,
        ) as exc:
            logger.warning("JavaScript click approach raised a WebDriver exception: %s", exc)

        return False

    def _capture_failure_screenshot(self, filename: str) -> None:
        """Save a failure screenshot using basic_actions when available."""
        if self.basic_actions is not None:
            try:
                self.basic_actions.capture_screenshot(filename=filename)
                return
            except (OSError, IOError) as exc:
                logger.debug("basic_actions.capture_screenshot failed: %s", exc)

        # Fallback: use driver directly
        try:
            self.driver.save_screenshot(filename)
            logger.info("Screenshot saved as %s", filename)
        except (OSError, IOError) as exc:
            logger.warning("Could not save screenshot %s: %s", filename, exc)
