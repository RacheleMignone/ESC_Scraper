import logging
from orchestrator import HudocOrchestrator
from fetcher import HudocApiFetcher
from downloader import HudocDownloader
from storage import HudocStorage

# Configure global logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MAIN")


def main():
    logger.info("🚀 Launching FULL Production Scraper...")

    # 1. Initialize the real modules
    fetcher = HudocApiFetcher()
    downloader = HudocDownloader()

    # We are now using your real, permanent production paths
    storage = HudocStorage(
        final_parquet="ESC_Corpus_Final.parquet"
    )

    # 2. Wire them into the Orchestrator
    orchestrator = HudocOrchestrator(
        api_fetcher=fetcher,
        downloader=downloader,
        storage_manager=storage
    )

    try:
        # 3. NO LIMITS!
        # This will loop through offset 500, 1000, 1500... until the API is empty.
        orchestrator.run_pipeline()

    except KeyboardInterrupt:
        logger.warning("Pipeline manually stopped by user.")
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
    finally:
        logger.info("Closing network connections...")
        fetcher.close()
        downloader.close()
        logger.info("Pipeline shutdown complete.")


if __name__ == "__main__":
    main()