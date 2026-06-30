import logging
import time
import random
import httpx
from typing import Optional
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, before_sleep_log
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HudocDownloader:
    def __init__(self, base_download_url: str = "https://hudoc.esc.coe.int/app/conversion/docx/html/body"):
        # Update this URL to the exact one HUDOC uses to serve text/html files!
        self.base_url = base_download_url
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        self.client = httpx.Client(headers=self.headers, timeout=60.0)

    @retry(
        wait=wait_exponential(multiplier=1.5, min=5, max=60),
        stop=stop_after_attempt(4),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def download_text(self, document_id: str, store_type: str) -> Optional[str]:
        """Downloads the document, parses HTML, and returns clean text."""
        time.sleep(random.uniform(1.0, 2.5))  # Politeness delay
        print(self.base_url)

        response = None

        try:
            raw_url = f"{self.base_url.replace('docx',store_type.lower())}?library=ESC&id={document_id.replace(' ','')}"
            response = self.client.get(raw_url, follow_redirects=True)
            response.raise_for_status()

        except Exception as fallback_e:
            print(f"❌ Unable to download {document_id}")
            return None  # Safely exit and let the Orchestrator move on

        try:
            raw_html = response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(raw_html, features='html.parser')
            text = soup.get_text(separator="\n", strip=True)

        except Exception as e:
            print(f"⚠️ BeautifulSoup parsing failed for {document_id}: {e}")
            text = response.content.decode("utf-8", errors="ignore")

        # --- PHASE 3: VALIDATION ---
        # Checks if the string exists and is not just empty spaces
        if text and text.strip():
            return text
        else:
            print(f"⚠️ UNABLE TO DOWNLOAD: Document {document_id} is completely empty.")
            return None

    def close(self):
        self.client.close()

def test_downloader():
    logger.info("🚀 Initializing the Downloader test...")

    downloader = HudocDownloader()

    # 👇 PASTE A REAL ID FROM YOUR FETCHER TEST HERE 👇
    # Example: "XXII-4/def/HRV/8/1/EN"
    test_id = "CR_2016_GEO_FRE"

    try:
        logger.info(f"Attempting to download text for ID: {test_id}")
        logger.info("Waiting for the politeness delay (1-3 seconds)...")

        # 1. Fire the download request
        text_content = downloader.download_text(test_id, 'xml')

        if not text_content:
            logger.error("❌ The downloader returned None. The file might not exist, or the COE server blocked us.")
            return

        logger.info(f"✅ Success! Downloaded {len(text_content)} characters of text.")

        # 2. Print just the first 500 characters so we don't flood your terminal
        logger.info("Inspecting the first 500 characters of the document:")
        print("\n" + "=" * 60)
        print(text_content[:500] + "\n\n...[TEXT TRUNCATED FOR DISPLAY]...")
        print("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"❌ Test crashed with an error: {e}", exc_info=True)
    finally:
        logger.info("Closing HTTP client connections...")
        downloader.close()
        logger.info("🏁 Downloader test complete.")

if __name__ == '__main__':
    test_downloader()