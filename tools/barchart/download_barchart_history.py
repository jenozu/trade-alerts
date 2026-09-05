from __future__ import annotations

import csv
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_DIR = Path.home() / "Documents" / "barchart-downloader"
PROFILE_DIR = BASE_DIR / "barchart-profile"
MANIFEST = BASE_DIR / "manifest.csv"
DOWNLOAD_DIR = Path.home() / "Downloads" / "barchart-history"

PAGE_TIMEOUT_MS = 60_000
DOWNLOAD_TIMEOUT_MS = 60_000
PAGE_SETTLE_MS = 2_500
BETWEEN_DOWNLOADS_SECONDS = 3


def load_manifest() -> list[dict[str, str]]:
    with MANIFEST.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_manifest(rows: list[dict[str, str]]) -> None:
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["contract", "start_date", "end_date", "filename", "status"],
        )
        writer.writeheader()
        writer.writerows(rows)


def find_date_inputs(page):
    inputs = page.locator('input[type="text"]')
    candidates = []
    for index in range(inputs.count()):
        item = inputs.nth(index)
        try:
            if not item.is_visible():
                continue
            value = item.input_value()
            placeholder = item.get_attribute("placeholder") or ""
            if (
                "-" in value
                or "/" in value
                or "date" in placeholder.lower()
                or "yyyy" in placeholder.lower()
                or "mm" in placeholder.lower()
                or "dd" in placeholder.lower()
            ):
                candidates.append(item)
        except Exception:
            continue
    if len(candidates) < 2:
        raise RuntimeError(
            "Could not identify Barchart's two historical date inputs. "
            f"Found only {len(candidates)} candidate(s)."
        )
    return candidates[0], candidates[1]


def set_date(input_locator, value: str) -> None:
    input_locator.click()
    input_locator.fill(value)
    input_locator.press("Tab")


def find_download_button(page):
    locator = page.locator("a.download-btn").filter(has_text="DOWNLOAD")
    visible = []
    for index in range(locator.count()):
        item = locator.nth(index)
        try:
            if item.is_visible():
                visible.append(item)
        except Exception:
            continue
    if not visible:
        raise RuntimeError("Could not find a visible Barchart historical DOWNLOAD link.")
    return visible[0], len(visible)


def basic_validate_download(path: Path) -> None:
    if not path.exists() or path.stat().st_size <= 0:
        raise RuntimeError("Downloaded file is missing or empty.")
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        first_line = handle.readline().strip()
    if not first_line:
        raise RuntimeError("Downloaded CSV has no header.")
    header = first_line.lower()
    required = ["time", "open", "high", "low", "volume"]
    missing = [term for term in required if term not in header]
    if missing:
        raise RuntimeError(
            "Downloaded file does not look like expected market data. "
            f"Missing header terms: {missing}. Header was: {first_line}"
        )
    if "close" not in header and "latest" not in header:
        raise RuntimeError(
            "Downloaded file does not contain a closing-price column. "
            f"Header was: {first_line}"
        )


def main() -> None:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        raise SystemExit(f"Manifest not found: {MANIFEST}")

    rows = load_manifest()
    print(f"Total jobs: {len(rows)}")
    print(f"Pending jobs: {sum(r['status'] != 'complete' for r in rows)}")
    print(f"Download directory: {DOWNLOAD_DIR}")

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            accept_downloads=True,
        )
        page = context.pages[0] if context.pages else context.new_page()

        for number, row in enumerate(rows, start=1):
            if row["status"] == "complete":
                continue

            contract = row["contract"].strip()
            start_date = row["start_date"].strip()
            end_date = row["end_date"].strip()
            filename = row["filename"].strip()
            destination = DOWNLOAD_DIR / filename

            if destination.exists() and destination.stat().st_size > 0:
                row["status"] = "complete"
                save_manifest(rows)
                print(f"[{number}/{len(rows)}] EXISTS -> {filename}")
                continue

            url = f"https://www.barchart.com/futures/quotes/{contract}/historical-download"
            print(f"[{number}/{len(rows)}] {contract} {start_date} -> {end_date}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
                page.wait_for_timeout(PAGE_SETTLE_MS)
                start_input, end_input = find_date_inputs(page)
                set_date(start_input, start_date)
                set_date(end_input, end_date)
                page.wait_for_timeout(750)
                print(
                    "Page dates:",
                    start_input.input_value(),
                    "->",
                    end_input.input_value(),
                )
                download_button, visible_count = find_download_button(page)
                print(f"Visible DOWNLOAD controls: {visible_count}")
                with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as download_info:
                    download_button.click()
                download = download_info.value
                print(f"Browser filename: {download.suggested_filename}")
                download.save_as(str(destination))
                basic_validate_download(destination)
                row["status"] = "complete"
                save_manifest(rows)
                print(f"SAVED: {filename} ({destination.stat().st_size:,} bytes)")
                time.sleep(BETWEEN_DOWNLOADS_SECONDS)
            except PlaywrightTimeoutError as exc:
                row["status"] = "timeout"
                save_manifest(rows)
                print(f"TIMEOUT: {exc}")
                break
            except Exception as exc:
                row["status"] = "error"
                save_manifest(rows)
                print(f"ERROR: {exc!r}")
                break

        context.close()

    rows = load_manifest()
    print("DOWNLOAD SESSION FINISHED")
    print(f"Complete: {sum(r['status'] == 'complete' for r in rows)}/{len(rows)}")
    print(f"Pending: {sum(r['status'] == 'pending' for r in rows)}")
    print(f"Errors: {sum(r['status'] == 'error' for r in rows)}")
    print(f"Timeouts: {sum(r['status'] == 'timeout' for r in rows)}")


if __name__ == "__main__":
    main()
