"""utilities/email_helper.py

Helper for verifying that the HP One Early Cancellation e-mail
has been received by the subscriber.

The implementation supports two modes:
  1. IMAP – connect to a real mailbox and search for the email.
  2. API  – query a test-mail-service (e.g. MailHog / MailSlurp).
"""

import imaplib
import logging
import time

logger = logging.getLogger(__name__)

# Subject strings that identify an Early Cancellation e-mail
EARLY_CANCELLATION_SUBJECT_KEYWORDS = (
    "early cancellation",
    "cancellation confirmed",
    "subscription cancelled",
    "cancel subscription",
)


class EmailHelper:
    """Utility for verifying the Early Cancellation e-mail."""

    def __init__(
        self,
        imap_host: str,
        imap_port: int = 993,
        username: str = "",
        password: str = "",
        use_ssl: bool = True,
    ):
        """
        :param imap_host: IMAP server hostname.
        :param imap_port: IMAP server port (default 993 for SSL).
        :param username: Mailbox username / email address.
        :param password: Mailbox password or app-token.
        :param use_ssl: Use IMAP-over-SSL when True.
        """
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def wait_for_early_cancellation_email(
        self,
        poll_interval: int = 15,
        max_wait: int = 300,
        mailbox: str = "INBOX",
    ) -> bool:
        """Poll the IMAP mailbox until an early-cancellation e-mail arrives.

        :param poll_interval: Seconds between IMAP checks.
        :param max_wait: Maximum total wait time in seconds.
        :param mailbox: IMAP folder to search (default ``INBOX``).
        :returns: True when the e-mail is found.
        :raises TimeoutError: If the e-mail is not found within *max_wait*.
        """
        deadline = time.monotonic() + max_wait
        while True:
            if self._check_inbox_for_cancellation_email(mailbox):
                logger.info("Early Cancellation e-mail found in %s.", mailbox)
                return True

            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Early Cancellation e-mail not received within {max_wait}s. "
                    "Check the subscriber mailbox."
                )

            logger.debug(
                "Early Cancellation e-mail not yet found. "
                "Retrying in %ds …",
                poll_interval,
            )
            time.sleep(poll_interval)

    def verify_early_cancellation_email_received(
        self,
        mailbox: str = "INBOX",
    ) -> bool:
        """Assert that an early-cancellation e-mail is already present.

        :param mailbox: IMAP folder to search.
        :returns: True when found.
        :raises AssertionError: When no matching e-mail is found.
        """
        if self._check_inbox_for_cancellation_email(mailbox):
            logger.info("Early Cancellation e-mail verified in %s.", mailbox)
            return True

        raise AssertionError(
            "Early Cancellation e-mail was NOT found in the mailbox. "
            "Verify that the cancellation flow triggered the notification."
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_inbox_for_cancellation_email(self, mailbox: str) -> bool:
        """Search *mailbox* for any e-mail matching the cancellation subjects.

        :returns: True when at least one matching message is found.
        """
        try:
            conn = (
                imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
                if self.use_ssl
                else imaplib.IMAP4(self.imap_host, self.imap_port)
            )
            conn.login(self.username, self.password)
            conn.select(mailbox)

            for keyword in EARLY_CANCELLATION_SUBJECT_KEYWORDS:
                # Escape double-quotes to prevent malformed IMAP search commands
                safe_keyword = keyword.replace("\\", "\\\\").replace('"', '\\"')
                status, data = conn.search(None, f'(SUBJECT "{safe_keyword}")')
                if status == "OK" and data and data[0]:
                    conn.logout()
                    return True

            conn.logout()
        except imaplib.IMAP4.error as exc:
            logger.warning("IMAP error while checking for cancellation email: %s", exc)
        except OSError as exc:
            logger.warning("Network error while checking for cancellation email: %s", exc)

        return False
