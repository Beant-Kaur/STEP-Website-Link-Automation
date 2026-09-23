"""
Kajabi Interactive Login & MFA Helper
Launches an interactive browser window to log in to Kajabi and complete MFA.
Automatically fills in credentials from .env and saves session state in `kajabi_session/`
so subsequent link replacements from the dashboard can run automatically in the background.
"""
import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

EDIT_URL = "https://app.kajabi.com/admin/themes/2161766380/settings/edit#/"
BASE_DIR = Path(__file__).resolve().parent.parent
SESSION_DIR = BASE_DIR / "kajabi_session"

def load_env_credentials():
    email = os.environ.get("KAJABI_EMAIL") or os.environ.get("STEP_API_KEY") or ""
    password = os.environ.get("KAJABI_PASSWORD") or os.environ.get("STEP_API_SECRET") or ""

    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k in ("KAJABI_EMAIL", "STEP_API_KEY") and not email:
                email = v
            elif k in ("KAJABI_PASSWORD", "STEP_API_SECRET") and not password:
                password = v
    return email, password

def login_kajabi():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    email, password = load_env_credentials()

    print("=" * 65, flush=True)
    print("  KAJABI ONE-TIME MFA LOGIN HELPER", flush=True)
    print("=" * 65, flush=True)
    print(f"Session directory: {SESSION_DIR}", flush=True)
    if email:
        print(f"Loaded credentials for: {email}", flush=True)
    else:
        print("Note: No credentials found in .env; you can type them manually.", flush=True)
    print("Launching browser window...", flush=True)
    print("-" * 65, flush=True)

    with sync_playwright() as p:
        context = None
        for channel in [None, "chrome", "msedge"]:
            try:
                kwargs = {
                    "user_data_dir": str(SESSION_DIR),
                    "headless": False,
                    "viewport": {"width": 1280, "height": 850},
                    "args": ["--disable-blink-features=AutomationControlled"]
                }
                if channel:
                    kwargs["channel"] = channel
                context = p.chromium.launch_persistent_context(**kwargs)
                break
            except Exception:
                continue

        if not context:
            print("Error: Could not launch browser. Ensure Playwright browsers are installed.", flush=True)
            return False

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(EDIT_URL)

        # If redirected to login page and credentials exist, auto-fill them!
        time.sleep(2)
        if "login" in page.url.lower() and email and password:
            try:
                print("Auto-filling email and password...", flush=True)
                email_input = page.wait_for_selector('input[type="email"], input[name="email"], #user_email', timeout=6000)
                if email_input:
                    email_input.fill(email)
                pw_input = page.wait_for_selector('input[type="password"], input[name="password"], #user_password', timeout=4000)
                if pw_input:
                    pw_input.fill(password)
                remember = page.query_selector('input[type="checkbox"]')
                if remember:
                    remember.check()
                submit_btn = page.query_selector('button[type="submit"], input[type="submit"]')
                if submit_btn:
                    print("Submitting login form... Please enter your MFA verification code.", flush=True)
                    submit_btn.click()
            except Exception as exc:
                print("Note: Could not auto-submit login fields, please proceed in the browser window:", exc, flush=True)

        print("\nWaiting for you to complete Multi-Factor Authentication (MFA) in the browser...", flush=True)
        print("The script will automatically detect when you land in the Theme Editor...", flush=True)

        authenticated = False
        start_time = time.time()
        timeout = 600  # 10 minutes

        while time.time() - start_time < timeout:
            try:
                urls = [p.url for p in context.pages]
                is_authed = any(
                    ("themes/2161766380" in u) or ("settings/edit" in u) or ("admin/sites" in u and "login" not in u)
                    for u in urls
                )
                if is_authed:
                    print("\n" + "=" * 65, flush=True)
                    print("  [SUCCESS] Authenticated into Kajabi!", flush=True)
                    print(f"  Current URLs: {urls}", flush=True)
                    print("  Session cookies and tokens saved successfully in kajabi_session/.", flush=True)
                    print("=" * 65, flush=True)
                    authenticated = True
                    time.sleep(2)
                    break
                time.sleep(1.5)
            except Exception as e:
                print(f"\nBrowser window closed: {e}", flush=True)
                break

        context.close()
        return authenticated

if __name__ == "__main__":
    success = login_kajabi()
    if success:
        print("\nReady! You can now update links directly from the STEP ESG Dashboard.", flush=True)
    else:
        print("\nLogin process did not complete. Run this script again when you are ready to log in.", flush=True)
