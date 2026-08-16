from __future__ import annotations

import uuid
from typing import Optional
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
from automation.exceptions import ControlOwnershipError, SessionError
from automation.models import ControlOwner, SessionState, SessionStatus


class SessionManager:
    """Manages browser lifecycle, persistent context, page, session state, and control ownership."""

    def __init__(
        self,
        headless: bool = True,
        viewport: Optional[dict] = None,
        slow_mo: Optional[float] = None,
        session_id: Optional[str] = None,
    ):
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 800}
        self.slow_mo = slow_mo
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        self._state = SessionState(session_id=self.session_id)

    @property
    def page(self) -> Page:
        if not self._page:
            raise SessionError("Browser session has not been started. Call start() first.")
        return self._page

    @property
    def context(self) -> BrowserContext:
        if not self._context:
            raise SessionError("Browser session context is not initialized.")
        return self._context

    @property
    def state(self) -> SessionState:
        if self._page:
            self._state.current_url = self._page.url
        return self._state

    async def start(self) -> Page:
        """Launch Playwright browser, persistent context, and page."""
        if self._playwright:
            return self.page

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
        )
        self._context = await self._browser.new_context(
            viewport=self.viewport,
            ignore_https_errors=True,
        )
        self._page = await self._context.new_page()
        self._state.status = SessionStatus.ACTIVE
        self._state.control_owner = ControlOwner.AUTOMATION
        self._state.current_url = self._page.url
        return self._page

    def assert_action_permitted(self) -> None:
        """Validate if automation is allowed to perform actions currently."""
        if self._state.status == SessionStatus.CLOSED:
            raise SessionError("Session is closed. Cannot execute actions.")
        if self._state.control_owner == ControlOwner.HUMAN:
            raise ControlOwnershipError("Session control is currently ceded to a human operator.")
        if self._state.status == SessionStatus.PAUSED:
            raise SessionError("Session is currently paused.")

    async def pause(self) -> None:
        """Pause automation."""
        if self._state.status == SessionStatus.CLOSED:
            raise SessionError("Cannot pause a closed session.")
        self._state.status = SessionStatus.PAUSED

    async def resume(self) -> None:
        """Resume automation."""
        if self._state.status == SessionStatus.CLOSED:
            raise SessionError("Cannot resume a closed session.")
        self._state.status = SessionStatus.ACTIVE

    async def cede_control(self) -> None:
        """Cede control to human operator."""
        if self._state.status == SessionStatus.CLOSED:
            raise SessionError("Cannot cede control on a closed session.")
        self._state.control_owner = ControlOwner.HUMAN
        self._state.status = SessionStatus.PAUSED

    async def reclaim_control(self) -> None:
        """Reclaim control back to automation."""
        if self._state.status == SessionStatus.CLOSED:
            raise SessionError("Cannot reclaim control on a closed session.")
        self._state.control_owner = ControlOwner.AUTOMATION
        self._state.status = SessionStatus.ACTIVE

    async def close(self) -> None:
        """Close page, context, browser, and playwright."""
        if self._page:
            try:
                await self._page.close()
            except Exception:
                pass
            self._page = None

        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

        self._state.status = SessionStatus.CLOSED
