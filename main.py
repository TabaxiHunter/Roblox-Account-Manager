from playwright.sync_api import sync_playwright

def get_cookie(cookies):
    for cookie in cookies:
        if cookie["name"] == ".ROBLOSECURITY":
            return cookie["value"]

def run(playwright):
    chromium = playwright.chromium
    browser = chromium.launch(headless=False)

    context = browser.new_context(bypass_csp=True)
    page = context.new_page()

    page.goto("https://www.roblox.com/login")
    page.wait_for_url("https://www.roblox.com/home", timeout=0)

    cookie = get_cookie(context.cookies())

    print(cookie)

    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)