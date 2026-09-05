from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_DIR = Path.home() / "Documents" / "barchart-downloader"
PROFILE_DIR = BASE_DIR / "barchart-profile"
URL = "https://www.barchart.com/futures/quotes/NMU25/historical-download"


def main() -> None:
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            accept_downloads=True,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(URL, wait_until="domcontentloaded")
        print("Browser opened.")
        print("Log into Barchart manually if needed.")
        print("When the Historical Data page is visible, return here and press ENTER.")
        input()
        print("Current URL:", page.url)
        print("Page title:", page.title())
        context.close()


if __name__ == "__main__":
    main()
