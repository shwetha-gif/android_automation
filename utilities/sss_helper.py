"""utilities/sss_helper.py

Helper for checking Subscription-State Service (SSS) entity states
using a Tenant ID.
"""

import logging
import time
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)

# Expected entity keys tracked in SSS for a subscription
SSS_ENTITY_KEYS = (
    "pending association",
    "iot-printer",
    "carepack",
    "instant-ink",
    "instant-paper",
    "page-set",
)


class SSSHelper:
    """Thin wrapper around the Subscription-State Service REST API."""

    def __init__(self, base_url: str, auth_token: str, timeout: int = 30):
        """
        :param base_url: Base URL of the SSS service
                         (e.g. ``https://sss.stage.hpone.io``).
        :param auth_token: Bearer token used for authentication.
        :param timeout: HTTP request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_subscription_states(self, tenant_id: str) -> Dict[str, str]:
        """Return the current entity states for *tenant_id* from SSS.

        :param tenant_id: The subscription tenant identifier.
        :returns: Mapping of entity-key → state string.
        :raises requests.HTTPError: On a non-2xx response.
        """
        url = f"{self.base_url}/api/v1/subscriptions/{tenant_id}/states"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def wait_for_all_pending(
        self,
        tenant_id: str,
        expected_keys: tuple = SSS_ENTITY_KEYS,
        poll_interval: int = 10,
        max_wait: int = 300,
    ) -> Dict[str, str]:
        """Poll SSS until every entity in *expected_keys* shows ``"pending"``.

        :param tenant_id: Subscription tenant identifier.
        :param expected_keys: Entity keys that must all be ``"pending"``.
        :param poll_interval: Seconds between polls.
        :param max_wait: Maximum total wait in seconds before giving up.
        :returns: Final state mapping once all entities are pending.
        :raises TimeoutError: If the desired state is not reached in time.
        """
        deadline = time.monotonic() + max_wait
        while True:
            states = self.get_subscription_states(tenant_id)
            pending = {k for k in expected_keys if states.get(k) == "pending"}
            not_pending = set(expected_keys) - pending

            if not not_pending:
                logger.info("All SSS entities are 'pending' for tenant %s", tenant_id)
                return states

            logger.debug(
                "Waiting for SSS entities to be pending. Still waiting: %s",
                not_pending,
            )

            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"SSS entities not in 'pending' state after {max_wait}s "
                    f"for tenant {tenant_id}. Current states: {states}"
                )

            time.sleep(poll_interval)

    def verify_all_pending(
        self,
        tenant_id: str,
        expected_keys: tuple = SSS_ENTITY_KEYS,
    ) -> bool:
        """Assert that all *expected_keys* are currently ``"pending"`` in SSS.

        :param tenant_id: Subscription tenant identifier.
        :param expected_keys: Entity keys to check.
        :returns: True when all keys are ``"pending"``.
        :raises AssertionError: When any entity is not in the expected state.
        """
        states = self.get_subscription_states(tenant_id)
        failures: Dict[str, Optional[str]] = {}
        for key in expected_keys:
            state = states.get(key)
            if state != "pending":
                failures[key] = state

        if failures:
            raise AssertionError(
                f"SSS entities not in 'pending' state for tenant {tenant_id}: "
                + ", ".join(f"{k}={v!r}" for k, v in sorted(failures.items()))
            )

        logger.info("All SSS entities verified as 'pending' for tenant %s", tenant_id)
        return True
