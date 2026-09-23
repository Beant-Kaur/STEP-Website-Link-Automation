"""
Kajabi Link Updater & Audit Ledger Engine
Handles updating broken/outdated links directly on Kajabi and maintaining a permanent audit log.
Supports both AI-recommended replacements and manual user overrides with reviewer notes.
"""
import re
import json
import uuid
import datetime
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
SESSION_DIR = BASE_DIR / "kajabi_session"
AUDIT_LOG_FILE = BASE_DIR / "kajabi" / "audit_log.json"
REPORT_FILE = BASE_DIR / "data" / "report.json"
KAJABI_EDIT_URL = "https://app.kajabi.com/admin/themes/2161766380/settings/edit#/"

BLOCK_MAP = {
    "Bahrain": "BARHEIN",
    "China": "CHINA",
    "European Union": "EUROPEAN UNION",
    "India": "INDIA",
    "Kingdom of Saudi Arabia": "KSA",
    "Kuwait": "KUWAIT",
    "Nigeria": "Accordion",
    "Oman": "OMAN",
    "Qatar": "QATAR",
    "Singapore": "SINGAPORE",
    "United Arab Emirates": "UAE",
    "United Kingdom": "UK",
    "United States": "USA"
}

def load_audit_log() -> list:
    if AUDIT_LOG_FILE.exists():
        try:
            return json.loads(AUDIT_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_audit_log(entries: list) -> None:
    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_LOG_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

def is_kajabi_session_available() -> bool:
    if not SESSION_DIR.exists():
        return False
    # Check if directory has network cookies
    cookie_file = SESSION_DIR / "Default" / "Network" / "Cookies"
    return cookie_file.exists() and cookie_file.stat().st_size > 1024

def clean_u(u: str) -> str:
    if not u:
        return ""
    return urllib.parse.unquote(u).strip().replace('\u00a0', '').replace('&amp;', '&').rstrip('/')

def replace_link_in_html(html: str, old_url: str, new_url: str) -> tuple[str, bool]:
    target = clean_u(old_url)
    if not target:
        return html, False

    replaced = False

    def repl_href(m):
        nonlocal replaced
        attr, q1, val, q2 = m.group(1), m.group(2), m.group(3), m.group(4)
        c_val = clean_u(val)
        if c_val == target or (len(target) > 15 and target in c_val) or (len(c_val) > 15 and c_val in target):
            replaced = True
            return f'{attr}{q1}{new_url}{q2}'
        return m.group(0)

    # 1. Regex match href attribute
    pattern = re.compile(r'(href\s*=\s*)(["\'])([^"\']+)(["\'])', re.IGNORECASE)
    updated_html = pattern.sub(repl_href, html)

    # 2. Also check if the visible anchor text was the raw old URL
    def repl_text(m):
        tag_open, inner_text, tag_close = m.group(1), m.group(2), m.group(3)
        if clean_u(inner_text) == target or (len(target) > 15 and target in clean_u(inner_text)):
            return f'{tag_open}{new_url}{tag_close}'
        return m.group(0)

    text_pattern = re.compile(r'(<a\b[^>]*>)(.*?)(</a>)', re.IGNORECASE | re.DOTALL)
    updated_html = text_pattern.sub(repl_text, updated_html)

    return updated_html, replaced

def sync_link_to_kajabi(jurisdiction: str, old_url: str, new_url: str) -> dict:
    """
    Automates updating the link in the Kajabi Theme Editor using Playwright.
    """
    if not is_kajabi_session_available():
        return {
            "ok": False,
            "status": "SESSION_REQUIRED",
            "message": "Kajabi session not found. Please run kajabi/login.py once to authenticate."
        }

    block_name = BLOCK_MAP.get(jurisdiction, jurisdiction.upper())

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_DIR),
                headless=True,
                viewport={"width": 1400, "height": 900},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(KAJABI_EDIT_URL, timeout=45000)
            page.wait_for_timeout(5000)

            # Check if redirected to login
            if "login" in page.url.lower():
                context.close()
                return {
                    "ok": False,
                    "status": "SESSION_EXPIRED",
                    "message": "Kajabi session expired. Please run kajabi/login.py to re-authenticate."
                }

            # Click FAQ in sidebar
            faq = page.locator("text='FAQ'").first
            if not faq.is_visible():
                sec_tab = page.locator("text='Sections'").first
                if sec_tab.is_visible():
                    sec_tab.click()
                    page.wait_for_timeout(1000)
                faq = page.locator("text='FAQ'").first

            if not faq.is_visible():
                context.close()
                return {"ok": False, "status": "ERROR", "message": "Could not locate FAQ section in Kajabi sidebar."}

            faq.click()
            page.wait_for_timeout(2000)

            # Click the country block
            block_locator = page.locator(f"text='{block_name}'").first
            if not block_locator.is_visible():
                context.close()
                return {"ok": False, "status": "ERROR", "message": f"Could not find block '{block_name}' in FAQ."}

            block_locator.click()
            page.wait_for_timeout(2500)

            # Wait for TinyMCE editor
            has_editor = page.evaluate("() => !!(window.tinymce && window.tinymce.activeEditor)")
            if not has_editor:
                page.wait_for_timeout(2000)

            curr_html = page.evaluate("() => window.tinymce && window.tinymce.activeEditor ? window.tinymce.activeEditor.getContent() : ''")
            if not curr_html:
                context.close()
                return {"ok": False, "status": "ERROR", "message": f"Could not read content from editor for '{block_name}'."}

            updated_html, replaced = replace_link_in_html(curr_html, old_url, new_url)

            if not replaced:
                context.close()
                return {
                    "ok": False,
                    "status": "LINK_NOT_FOUND_IN_BLOCK",
                    "message": f"The target link was not found in the Kajabi content for {jurisdiction}."
                }

            # Update content in TinyMCE
            page.evaluate("(newHtml) => { window.tinymce.activeEditor.setContent(newHtml); }", updated_html)

            # Trigger change in Kajabi React state by focusing and typing in editor iframe
            try:
                iframe_locator = page.frame_locator('iframe[id*="tiny-react"]')
                body = iframe_locator.locator('body')
                body.click()
                page.keyboard.press('End')
                page.keyboard.type(' ')
                page.keyboard.press('Backspace')
                page.wait_for_timeout(1000)
            except Exception:
                pass

            # Wait for Save button to be active
            save_btn = page.locator("button:has-text('Save')").first
            page.wait_for_function(
                "() => { const b = Array.from(document.querySelectorAll('button')).find(x => x.innerText.trim() === 'Save'); return b && !b.disabled; }",
                timeout=5000
            )

            # Click Save!
            save_btn.click()
            page.wait_for_timeout(4000)

            context.close()
            return {
                "ok": True,
                "status": "LIVE_APPLIED",
                "message": f"Successfully updated link in Kajabi ({block_name}) and saved live."
            }

    except Exception as exc:
        return {
            "ok": False,
            "status": "AUTOMATION_ERROR",
            "message": f"Kajabi automation error: {str(exc)[:150]}"
        }

def apply_link_update(
    link_id: str,
    new_url: str,
    reviewer: str = "Sustainability Manager",
    note: str = "",
    is_manual: bool = False,
    sync_to_kajabi: bool = True
) -> Dict[str, Any]:
    """
    Applies a link replacement (AI or manual) and logs it into the audit ledger.
    """
    if not link_id or not new_url:
        return {"ok": False, "error": "link_id and new_url are required"}

    # 1. Update report.json
    record = None
    if REPORT_FILE.exists():
        try:
            data = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
            for r in data:
                if str(r.get("link_id")) == str(link_id) or str(r.get("id")) == str(link_id):
                    record = r
                    r["previous_url"] = r.get("original_url") or r.get("current_url")
                    r["original_url"] = new_url
                    r["current_url"] = new_url
                    r["final_url"] = new_url
                    r["final_status"] = "KEEP"
                    r["status"] = "CONFIRMED_LATEST"
                    r["classification"] = "CONFIRMED_LATEST"
                    r["freshness_status"] = "CURRENT_IN_FORCE"
                    r["regulatory_status"] = "IN_FORCE"
                    r["replacement_url"] = ""  # Cleared because now active
                    r["last_updated_at"] = datetime.datetime.now().isoformat()
                    r["last_updated_by"] = reviewer
                    r["audit_note"] = note
                    r["is_manual_override"] = is_manual
                    break

            if record:
                REPORT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print("Error updating report.json:", e)

    orig_url = (record.get("previous_url") if record else "") or ""
    country = (record.get("jurisdiction") if record else "") or "General"
    reg_title = (record.get("page_title") if record else "") or link_id

    # 2. Sync to live Kajabi page if requested
    kajabi_status = "SAVED_LOCALLY"
    kajabi_message = "Updated in dashboard report."

    if sync_to_kajabi:
        if is_kajabi_session_available():
            sync_res = sync_link_to_kajabi(country, orig_url, new_url)
            kajabi_status = sync_res.get("status", "UNKNOWN")
            kajabi_message = sync_res.get("message", "")
        else:
            kajabi_status = "PENDING_MFA_LOGIN"
            kajabi_message = "Saved locally. Kajabi session not found; run kajabi/login.py once to authenticate."

    # 3. Create Audit Log Entry
    log_entry = {
        "id": f"audit_{uuid.uuid4().hex[:10]}",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "link_id": link_id,
        "jurisdiction": country,
        "regulation_title": reg_title,
        "original_url": orig_url,
        "new_url": new_url,
        "is_manual_override": is_manual,
        "reviewer": reviewer,
        "note": note or ("Updated to official sovereign regulation" if not is_manual else "Manual URL override"),
        "kajabi_status": kajabi_status,
        "kajabi_message": kajabi_message
    }

    logs = load_audit_log()
    logs.insert(0, log_entry)  # newest first
    save_audit_log(logs)

    return {
        "ok": True,
        "status": kajabi_status,
        "message": kajabi_message,
        "entry": log_entry
    }

if __name__ == "__main__":
    print("Kajabi Updater Ready.")
    print("Session available:", is_kajabi_session_available())
