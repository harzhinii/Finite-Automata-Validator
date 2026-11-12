"""
Optional helper: take REAL screenshots of the running app with Playwright.

    pip install playwright && playwright install chromium
    streamlit run app.py          (in another terminal)
    python scripts/capture_screenshots.py [http://localhost:8501]

Screenshots are saved to screenshots/.  (You can also just press Win+Shift+S / Cmd+Shift+4.)
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
OUT = Path(__file__).resolve().parent.parent / "screenshots"
OUT.mkdir(exist_ok=True)


def nav(page, text):
    page.get_by_text(text, exact=False).first.click()
    page.wait_for_timeout(2500)


def fill_and_validate(page, label, value):
    box = page.get_by_label(label)
    box.fill(value)
    box.press("Enter")
    page.wait_for_timeout(600)
    page.get_by_role("button", name="Validate").first.click()
    page.wait_for_timeout(2500)


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=2)
    page.goto(URL)
    page.wait_for_timeout(4000)
    shots = []

    def snap(name, full=True):
        page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
        shots.append(name)

    snap("01_home")
    nav(page, "ATM PIN Validator")
    fill_and_validate(page, "Enter a PIN", "48a1")
    snap("02_pin_rejected")
    page.get_by_role("tab", name="Card-lock simulator").click()
    page.wait_for_timeout(1000)
    for name in ["Wrong PIN (W)", "Wrong PIN (W)", "Correct PIN (C)", "Wrong PIN (W)", "Wrong PIN (W)", "Wrong PIN (W)"]:
        page.get_by_role("button", name=name).click()
        page.wait_for_timeout(700)
    snap("03_card_lock_after_WWCWWW")
    nav(page, "Password Validator")
    fill_and_validate(page, "Enter a password", "Srm@2026")
    snap("04_password_accepted")
    nav(page, "E-mail Validator")
    fill_and_validate(page, "Enter an e-mail address", "harshini.rk@srmist.edu.in")
    snap("05_email_accepted")
    nav(page, "Automata Visualizer")
    snap("06_visualizer")
    nav(page, "Testing and Results")
    page.wait_for_timeout(6000)
    snap("07_testing_results")
    b.close()
print("saved:", ", ".join(shots))
