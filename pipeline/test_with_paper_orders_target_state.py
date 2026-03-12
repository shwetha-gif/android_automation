"""
pipeline/test_with_paper_orders_target_state.py

Tests for HP One subscription cancellation flow including:
  - Early cancellation with a received printer
  - SSS entity-state verification (all entities must be 'pending')
  - Early Cancellation e-mail receipt verification

Usage::

    pytest pipeline/test_with_paper_orders_target_state.py \
        -k test_cancel_subscription_received_printer_early_cancellation \
        --env stage --tenant-id <TENANT_ID>
"""

import logging
import os
import pytest

from overview_printer import OverviewPrinterPage
from utilities.sss_helper import SSSHelper, SSS_ENTITY_KEYS
from utilities.email_helper import EmailHelper

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption("--env", default="stage", help="Target environment (stage/prod)")
    parser.addoption("--tenant-id", default=None, help="Subscription Tenant ID")
    parser.addoption("--username", default=None, help="Test-account username (email)")
    parser.addoption("--password", default=None, help="Test-account password")


@pytest.fixture(scope="session")
def env(request):
    return request.config.getoption("--env", default="stage")


@pytest.fixture(scope="session")
def tenant_id(request):
    tid = (
        request.config.getoption("--tenant-id", default=None)
        or os.environ.get("TENANT_ID")
    )
    return tid


@pytest.fixture(scope="session")
def test_credentials(request):
    username = (
        request.config.getoption("--username", default=None)
        or os.environ.get("TEST_USERNAME", "")
    )
    password = (
        request.config.getoption("--password", default=None)
        or os.environ.get("TEST_PASSWORD", "")
    )
    return {"username": username, "password": password}


@pytest.fixture(scope="session")
def sss_helper(env):
    """Return a configured SSSHelper for the target environment."""
    base_urls = {
        "stage": "https://sss.stage.hpone.io",
        "prod": "https://sss.hpone.io",
    }
    base_url = base_urls.get(env, base_urls["stage"])
    auth_token = os.environ.get("SSS_AUTH_TOKEN", "")
    return SSSHelper(base_url=base_url, auth_token=auth_token)


@pytest.fixture(scope="session")
def email_helper(test_credentials):
    """Return a configured EmailHelper using test account IMAP credentials."""
    imap_host = os.environ.get("IMAP_HOST", "imap.gmail.com")
    return EmailHelper(
        imap_host=imap_host,
        username=test_credentials["username"],
        password=test_credentials["password"],
    )


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("user", ["shwetha"])
class TestAddPaper:
    """Tests related to HP One paper-add subscription scenarios."""

    # ------------------------------------------------------------------
    # Early cancellation with a received printer
    # ------------------------------------------------------------------

    def test_cancel_subscription_received_printer_early_cancellation(
        self,
        user,
        driver,           # provided by conftest / session fixture
        basic_actions,    # BasicActions helper from conftest
        tenant_id,
        sss_helper,
        email_helper,
        env,
    ):
        """Cancel subscription when printer has been received (early cancellation).

        Steps
        -----
        1. Navigate to the subscription overview page and trigger cancellation.
        2. Click the confirm-cancellation button in the dialog.
        3. Verify SSS entities are all 'pending'.
        4. Verify the Early Cancellation e-mail is received.
        """
        logger.info(
            "Starting test_cancel_subscription_received_printer_early_cancellation "
            "(user=%s, env=%s)",
            user,
            env,
        )

        overview_page = OverviewPrinterPage(driver=driver, basic_actions=basic_actions)

        # ---- Step 1 & 2: Confirm cancellation ----
        logger.info("Step 1: Clicking confirm-cancellation button …")
        overview_page.click_on_confirm_cancellation()
        logger.info("Confirm-cancellation button clicked successfully.")

        # ---- Step 3: SSS entity verification ----
        if tenant_id:
            logger.info(
                "Step 3: Verifying SSS entities are all 'pending' for tenant %s …",
                tenant_id,
            )
            # Wait up to 5 minutes for SSS to transition all entities to pending
            states = sss_helper.wait_for_all_pending(
                tenant_id=tenant_id,
                expected_keys=SSS_ENTITY_KEYS,
                poll_interval=10,
                max_wait=300,
            )
            for entity_key in SSS_ENTITY_KEYS:
                assert states.get(entity_key) == "pending", (
                    f"SSS entity '{entity_key}' expected 'pending', "
                    f"got {states.get(entity_key)!r}"
                )
            logger.info("All SSS entities verified as 'pending': %s", states)
        else:
            logger.warning(
                "No --tenant-id provided; skipping SSS entity verification."
            )

        # ---- Step 4: Early Cancellation e-mail verification ----
        logger.info("Step 4: Verifying Early Cancellation e-mail receipt …")
        email_helper.wait_for_early_cancellation_email(
            poll_interval=15,
            max_wait=300,
        )
        logger.info("Early Cancellation e-mail verified successfully.")
