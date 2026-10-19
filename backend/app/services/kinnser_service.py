"""
Kinnser EMR browser automation service using Playwright.

This service handles:
  - Authentication (username/password + optional TOTP)
  - Patient navigation
  - Clinical note entry for different visit types
  - Screenshot capture and upload
  - Session/cookie reuse
"""

import asyncio
import base64
import io
import json
import logging
import random
import time
from typing import Any, Optional

import pyotp
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Kinnser URL constants
# ---------------------------------------------------------------------------
KINNSER_BASE_URL = "https://www.kinnser.net"
KINNSER_LOGIN_URL = f"{KINNSER_BASE_URL}/index.cfm"
KINNSER_DASHBOARD_URL = f"{KINNSER_BASE_URL}/members/index.cfm"


# ---------------------------------------------------------------------------
# Field mapping registry
# ---------------------------------------------------------------------------
# Maps structured_note keys to Kinnser form field selectors
FIELD_MAP: dict[str, dict[str, str]] = {
    "visit_minutes": {
        "selector": "input[name='visitMinutes'], input[id*='visitMin']",
        "type": "text",
    },
    "subjective.pain_scale": {
        "selector": "select[name='painScale'], input[name*='pain'][name*='scale']",
        "type": "select_or_text",
    },
    "subjective.chief_complaint": {
        "selector": "textarea[name='chiefComplaint'], textarea[id*='chiefComplaint']",
        "type": "textarea",
    },
    "objective.observation": {
        "selector": "textarea[name='observation'], textarea[id*='observation']",
        "type": "textarea",
    },
    "assessment.clinical_impression": {
        "selector": "textarea[name*='assessment'], textarea[id*='assessment']",
        "type": "textarea",
    },
    "plan.interventions": {
        "selector": "textarea[name*='plan'], textarea[id*='plan']",
        "type": "textarea_list",
    },
    "plan.frequency": {
        "selector": "select[name='visitFrequency'], input[name*='frequency']",
        "type": "select_or_text",
    },
}


class KinnserAutomationService:
    """
    Automates Kinnser EMR data entry using Playwright.

    Instances maintain a browser context (cookies/session) across calls
    to avoid repeated logins.
    """

    # Human-like delay ranges in milliseconds
    _TYPING_DELAY_MIN = 30
    _TYPING_DELAY_MAX = 80
    _ACTION_DELAY_MIN = 500
    _ACTION_DELAY_MAX = 1500

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._cookies_file = "/tmp/kinnser_session.json"
        self._logged_in = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def login(
        self,
        username: str,
        password: str,
        totp_secret: Optional[str] = None,
    ) -> None:
        """Authenticate to Kinnser. Reuses existing session if valid."""
        await self._ensure_browser()

        # Try to restore session from saved cookies
        if await self._restore_session():
            logger.info("Kinnser session restored from cookies")
            return

        page = await self._get_page()
        await page.goto(KINNSER_LOGIN_URL, wait_until="domcontentloaded")
        await self._human_delay()

        # Fill username
        await page.fill("input[name='username'], input[id='username']", username)
        await self._human_delay(100, 300)

        # Fill password
        await page.fill("input[name='password'], input[type='password']", password)
        await self._human_delay(200, 500)

        # Submit
        await page.click("input[type='submit'], button[type='submit']")
        await page.wait_for_load_state("networkidle", timeout=15000)
        await self._human_delay()

        # Handle TOTP if 2FA page appears
        if totp_secret and await self._is_totp_page(page):
            totp = pyotp.TOTP(totp_secret)
            code = totp.now()
            await page.fill("input[name*='otp'], input[name*='code'], input[name*='mfa']", code)
            await self._human_delay(500, 1000)
            await page.click("input[type='submit'], button[type='submit']")
            await page.wait_for_load_state("networkidle", timeout=10000)

        # Verify login succeeded
        current_url = page.url
        if "login" in current_url.lower() or "index.cfm" in current_url:
            # Check for error messages
            error_text = await page.inner_text("body")
            if "invalid" in error_text.lower() or "incorrect" in error_text.lower():
                raise RuntimeError("Kinnser login failed: invalid credentials")

        # Save session cookies
        await self._save_session()
        self._logged_in = True
        logger.info("Kinnser login successful for user %s", username)

    async def navigate_to_patient(self, patient_id: str, patient_name: str) -> None:
        """Navigate to the patient's record in Kinnser."""
        page = await self._get_page()

        # Navigate to patient search
        await page.goto(f"{KINNSER_BASE_URL}/members/patient/search.cfm", wait_until="domcontentloaded")
        await self._human_delay()

        # Try search by patient ID first
        search_input = await page.query_selector(
            "input[name='patientId'], input[name*='patientId'], input[id*='search']"
        )
        if search_input:
            await search_input.fill(patient_id)
            await self._human_delay(200, 400)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle", timeout=10000)
            await self._human_delay()

            # Click on the first matching result
            result_link = await page.query_selector(
                f"a:has-text('{patient_name.split()[0]}'), td:has-text('{patient_id}')"
            )
            if result_link:
                await result_link.click()
                await page.wait_for_load_state("networkidle", timeout=10000)
                logger.info("Navigated to patient %s (%s)", patient_name, patient_id)
                return

        # Fallback: search by name
        name_input = await page.query_selector("input[name*='lastName'], input[name*='name']")
        if name_input:
            parts = patient_name.split()
            last_name = parts[-1] if parts else patient_name
            await name_input.fill(last_name)
            await self._human_delay(200, 400)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle", timeout=10000)
            await self._human_delay()

            result_link = await page.query_selector(f"a:has-text('{patient_name.split()[0]}')")
            if result_link:
                await result_link.click()
                await page.wait_for_load_state("networkidle", timeout=10000)
                return

        raise RuntimeError(f"Could not find patient {patient_name} ({patient_id}) in Kinnser")

    async def enter_note(self, structured_note: dict[str, Any], visit_type: str) -> None:
        """
        Enter the structured note into the Kinnser visit form.

        Navigates to the appropriate note form for the visit type,
        then fills each field using the FIELD_MAP registry.
        """
        page = await self._get_page()

        # Navigate to the correct note type
        note_url_map = {
            "initial_eval": "evaluation",
            "follow_up": "visit",
            "discharge": "discharge",
            "recert": "recertification",
        }
        note_path = note_url_map.get(visit_type, "visit")
        await page.goto(
            f"{KINNSER_BASE_URL}/members/patient/note/{note_path}.cfm",
            wait_until="domcontentloaded",
        )
        await self._human_delay(1000, 2000)

        # Fill visit date
        date_input = await page.query_selector(
            "input[name='visitDate'], input[id*='visitDate'], input[name='visit_date']"
        )
        if date_input:
            visit_date = structured_note.get("visit_date", "")
            if visit_date:
                await date_input.fill(str(visit_date))
                await self._human_delay()

        # Fill visit minutes
        if structured_note.get("visit_minutes"):
            field_config = FIELD_MAP.get("visit_minutes")
            if field_config:
                await self._fill_field(
                    page, field_config["selector"], str(structured_note["visit_minutes"])
                )

        # Fill SOAP sections
        subjective = structured_note.get("subjective") or {}
        objective = structured_note.get("objective") or {}
        assessment = structured_note.get("assessment") or {}
        plan_section = structured_note.get("plan") or {}

        # Subjective fields
        if subjective.get("chief_complaint"):
            cfg = FIELD_MAP.get("subjective.chief_complaint")
            if cfg:
                await self._fill_field(page, cfg["selector"], subjective["chief_complaint"])

        if subjective.get("pain_scale") is not None:
            cfg = FIELD_MAP.get("subjective.pain_scale")
            if cfg:
                await self._fill_field(page, cfg["selector"], str(int(subjective["pain_scale"])))

        # Objective: build a summary string for the observation textarea
        obs_parts = []
        if objective.get("observation"):
            obs_parts.append(objective["observation"])
        if objective.get("rom_measurements"):
            obs_parts.append("ROM: " + "; ".join(
                f"{r['joint']} {r['movement']}: {r.get('active_rom', 'NT')}° AROM"
                for r in objective["rom_measurements"]
            ))
        if objective.get("strength_tests"):
            obs_parts.append("Strength: " + "; ".join(
                f"{s['muscle_group']}: {s['grade']}/5"
                for s in objective["strength_tests"]
            ))

        if obs_parts:
            cfg = FIELD_MAP.get("objective.observation")
            if cfg:
                await self._fill_field(page, cfg["selector"], "\n".join(obs_parts))

        # Assessment
        if assessment.get("clinical_impression"):
            impression = assessment["clinical_impression"]
            if assessment.get("skilled_care_rationale"):
                impression += f"\n\nSkilled Care Rationale: {assessment['skilled_care_rationale']}"
            cfg = FIELD_MAP.get("assessment.clinical_impression")
            if cfg:
                await self._fill_field(page, cfg["selector"], impression)

        # Plan
        if plan_section.get("interventions"):
            interventions_text = "\n".join(f"- {i}" for i in plan_section["interventions"])
            cfg = FIELD_MAP.get("plan.interventions")
            if cfg:
                await self._fill_field(page, cfg["selector"], interventions_text)

        if plan_section.get("frequency"):
            cfg = FIELD_MAP.get("plan.frequency")
            if cfg:
                await self._fill_field(page, cfg["selector"], plan_section["frequency"])

        logger.info("Note fields populated for visit_type=%s", visit_type)

    async def save_and_verify(self) -> str:
        """
        Save the note form and verify submission. Returns a screenshot S3 URL.
        """
        from app.services.storage_service import S3StorageService

        page = await self._get_page()
        storage = S3StorageService()

        await self._human_delay(500, 1000)

        # Click the save/submit button
        save_button = await page.query_selector(
            "input[value='Save'], input[value='Submit'], button:has-text('Save'), "
            "button:has-text('Submit'), input[name='submit']"
        )
        if save_button:
            await save_button.click()
            await page.wait_for_load_state("networkidle", timeout=15000)
            await self._human_delay(1000, 2000)

        # Check for error messages
        page_content = await page.inner_text("body")
        error_indicators = ["error", "invalid", "required field", "please correct"]
        for indicator in error_indicators:
            if indicator in page_content.lower():
                # Take error screenshot
                screenshot_bytes = await page.screenshot(full_page=True)
                raise RuntimeError(f"Kinnser submission error detected: '{indicator}' found on page")

        # Take confirmation screenshot
        screenshot_bytes = await page.screenshot(full_page=True, type="png")

        # Upload to S3
        import uuid
        screenshot_key = f"kinnser-screenshots/{uuid.uuid4()}"
        screenshot_url = await storage.upload_screenshot(screenshot_bytes, screenshot_key)

        logger.info("Note saved and verified, screenshot at %s", screenshot_url)
        return screenshot_url

    async def close(self) -> None:
        """Close the browser and clean up resources."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._logged_in = False
        logger.info("Kinnser browser session closed")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _ensure_browser(self) -> None:
        if self._browser is None:
            self._playwright = await async_playwright().start()
            launch_kwargs: dict[str, Any] = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            }
            if settings.KINNSER_BROWSER_WS_URL:
                self._browser = await self._playwright.chromium.connect(
                    settings.KINNSER_BROWSER_WS_URL
                )
            else:
                self._browser = await self._playwright.chromium.launch(**launch_kwargs)

            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                java_script_enabled=True,
                accept_downloads=False,
            )
            # Prevent detection of Playwright automation
            await self._context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

    async def _get_page(self) -> Page:
        await self._ensure_browser()
        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
        return self._page

    async def _restore_session(self) -> bool:
        """Attempt to restore session from saved cookies."""
        import os
        if not os.path.exists(self._cookies_file):
            return False

        try:
            with open(self._cookies_file) as f:
                cookies = json.load(f)
            await self._context.add_cookies(cookies)

            # Verify session is still valid
            page = await self._get_page()
            await page.goto(KINNSER_DASHBOARD_URL, wait_until="domcontentloaded", timeout=10000)
            current_url = page.url
            if "members" in current_url and "login" not in current_url.lower():
                self._logged_in = True
                return True
        except Exception as exc:
            logger.debug("Could not restore Kinnser session: %s", exc)

        return False

    async def _save_session(self) -> None:
        """Save browser cookies for session reuse."""
        try:
            cookies = await self._context.cookies()
            with open(self._cookies_file, "w") as f:
                json.dump(cookies, f)
        except Exception as exc:
            logger.warning("Could not save Kinnser session: %s", exc)

    async def _is_totp_page(self, page: Page) -> bool:
        """Check if the current page is requesting a TOTP code."""
        content = await page.inner_text("body")
        totp_indicators = ["authenticat", "two-factor", "verification code", "otp", "one-time"]
        return any(indicator in content.lower() for indicator in totp_indicators)

    async def _fill_field(self, page: Page, selector: str, value: str) -> None:
        """Fill a form field with human-like typing delays."""
        element = await page.query_selector(selector)
        if element is None:
            logger.warning("Field not found: %s", selector)
            return

        tag = await element.evaluate("el => el.tagName.toLowerCase()")

        if tag == "select":
            # For select elements, try to set by value, then by text
            try:
                await element.select_option(value=value)
            except Exception:
                try:
                    await element.select_option(label=value)
                except Exception:
                    logger.warning("Could not select option '%s' in %s", value, selector)
        else:
            await element.click()
            await self._human_delay(50, 150)
            await element.triple_click()  # select all existing content
            await self._human_delay(50, 100)

            # Type with human-like delays
            for char in value:
                await page.keyboard.type(char, delay=random.uniform(
                    self._TYPING_DELAY_MIN, self._TYPING_DELAY_MAX
                ))

        await self._human_delay()

    async def _human_delay(
        self, min_ms: int = None, max_ms: int = None
    ) -> None:
        """Sleep for a random human-like duration."""
        if min_ms is None:
            min_ms = self._ACTION_DELAY_MIN
        if max_ms is None:
            max_ms = self._ACTION_DELAY_MAX
        delay_s = random.uniform(min_ms, max_ms) / 1000
        await asyncio.sleep(delay_s)
