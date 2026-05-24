import os
import time
import re
import math
from datetime import date
from playwright.sync_api import sync_playwright
from atproto import Client

# Securely pulls your hidden credentials from GitHub Secrets
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")
TARGET_URL = "https://oversightdemocrats.house.gov/trump-family-corruption-tracker"

def format_currency(raw_string):
    clean_str = raw_string.replace('$', '')
    parts = clean_str.split('.')
    whole_parts = parts[0].split(',')
    fixed_whole = []
    
    for i, block in enumerate(whole_parts):
        if i == 0:
            fixed_whole.append(block)
        else:
            fixed_whole.append(block[:3])
            
    final_number = "".join(fixed_whole)
    if len(parts) > 1:
        final_number += "." + parts[1][:2]
        
    try:
        return f"${float(final_number):,.2f}"
    except ValueError:
        return raw_string

def fetch_tracker_data_sync():
    print("Launching invisible browser...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            print("Page loaded, waiting 5 seconds for numbers to render...")
            time.sleep(5) 
            
            visible_text = page.evaluate("document.body.innerText")
            browser.close()
            
            clean_text = re.sub(r'\s+', '', visible_text).upper()
            
            wealth_match = re.search(r"TOTALTRUMPFAMILYDIGITALGRIFTWEALTH.*?(\$[0-9,.]+)", clean_text)
            foreign_match = re.search(r"FROMFOREIGNINTERESTS.*?(\$[0-9,.]+)", clean_text)

            if wealth_match and foreign_match:
                return {
                    "total_wealth": format_currency(wealth_match.group(1)),
                    "foreign": format_currency(foreign_match.group(1))
                }
            else:
                print("Could not locate the live numbers.")
                return None
    except Exception as e:
        print(f"Error scraping data: {repr(e)}") 
        return None

def post_to_bluesky():
    print("Fetching updated data...")
    data = fetch_tracker_data_sync()
    
    if not data:
        print("Could not update data. Skipping post.")
        return

    # --- THE MATH SECTION ---
    # 1. Calculate days since Jan 20, 2025
    inauguration_date = date(2025, 1, 20)
    today = date.today()
    days_without_impeachment = (today - inauguration_date).days

    # 2. Calculate Hunter Biden Paintings
    # Strip the formatting back off the total wealth so Python can do math with it
    raw_wealth = float(data['total_wealth'].replace('$', '').replace(',', ''))
    hunter_paintings = math.ceil(raw_wealth / 55000)

    post_text = (
        f"🚨 Trump Family Digital Grift Tracker Update 🚨\n\n"
        f"{data['total_wealth']} Total Dollars of Treason\n"
        f"{data['foreign']} Foreign Bribes\n"
        f"🎨 {hunter_paintings:,} Hunter Biden Paintings\n\n"
        f"🗓️ Days without impeachment: {days_without_impeachment}\n\n"
        f"Source: https://oversightdemocrats.house.gov/trump-family-corruption-tracker"
    )

    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
        client.send_post(text=post_text)
        print("Successfully posted to BlueSky!")
    except Exception as e:
        print(f"Error posting to BlueSky: {e}")

# --- THE START BUTTON ---
if __name__ == "__main__":
    post_to_bluesky()
