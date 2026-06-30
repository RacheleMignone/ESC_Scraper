import logging
from typing import Any
from tqdm.auto import tqdm

logger = logging.getLogger(__name__)


class HudocOrchestrator:
    def __init__(self, api_fetcher: Any, downloader: Any, storage_manager: Any):
        self.fetcher = api_fetcher
        self.downloader = downloader
        self.storage = storage_manager

    def run_pipeline(self):
        logger.info("🚀 Starting HUDOC ESC Direct-Append Scraper...")

        existing_ids = self.storage.get_existing_ids()
        batch_size = 500
        new_docs_downloaded = 0

        # Build Year Queries
        queries = []
        # for year in range(1965, 2027):
        for year in range(2026, 2027):
            queries.append({
                "label": f"Year {year}",
                "query_string": f"contentsitename:ESC AND escpublicationdate:[{year}-01-01T00:00:00Z TO {year}-12-31T23:59:59Z]"
            })
        queries.append({
            "label": "Missing Dates (Catch-all)",
            "query_string": "contentsitename:ESC AND NOT escpublicationdate:[1000-01-01T00:00:00Z TO 9999-12-31T23:59:59Z]"
        })

        try:
            for q in queries:
                logger.info(f"\n📅 --- SCANNING BATCH: {q['label']} ---")
                offset = 0
                pbar = tqdm(desc=f"📡 {q['label']}", unit=" docs", dynamic_ncols=True)

                while True:
                    pbar.set_postfix_str("Fetching API...")
                    batch = self.fetcher.fetch_metadata_batch(query=q['query_string'], start=offset, length=batch_size)

                    if not batch:
                        pbar.write(f"✅ Finished {q['label']}")
                        break

                        # 1. Filter against existing final parquet
                    new_docs = [doc for doc in batch if doc['document_id'] not in existing_ids]
                    print('NEW DOCS', new_docs)

                    if not new_docs:
                        offset += batch_size
                        pbar.update(batch_size)
                        continue

                    # Initialize the list here so the emergency save block can always see it
                    docs_to_save = []

                    # 2. Download texts directly into the dictionaries
                    for doc in new_docs:
                        doc_id = doc['document_id']
                        pbar.set_postfix_str(f"Downloading: {doc_id}")
                        content_store_type = doc['content_store_type']

                        try:
                            text = self.downloader.download_text(doc_id, content_store_type)
                            doc['document_text'] = text
                            docs_to_save.append(doc)
                            new_docs_downloaded += 1
                        except Exception as e:
                            pbar.write(f"⚠️ Failed {doc_id}: {e}")

                    # 3. DIRECT APPEND: Save the fully populated docs instantly to the final file
                    if docs_to_save:

                        self.storage.append_to_final_dataset(docs_to_save)
                        # Add newly saved IDs to memory so we don't duplicate them
                        for d in docs_to_save:
                            existing_ids.add(d['document_id'])

                    offset += batch_size
                    pbar.update(batch_size)

                pbar.close()

        except KeyboardInterrupt:
            print("\n")
            logger.warning("⚠️ Pipeline interrupted by user.")

            # 👇 THE SAFE SHUTDOWN FEATURE 👇
            try:
                # If we have partially downloaded documents in memory, save them!
                if 'docs_to_save' in locals() and docs_to_save:
                    self.storage.append_to_final_dataset(docs_to_save)
                    logger.info(
                        f"💾 EMERGENCY SAVE: Rescued {len(docs_to_save)} partially processed documents before shutting down.")
            except Exception as e:
                logger.error(f"Could not rescue partial batch: {e}")

        except Exception as e:
            print("\n")
            logger.error(f"❌ Pipeline crashed: {e}", exc_info=True)
        finally:
            if 'pbar' in locals():
                pbar.close()
            logger.info(f"🏁 Scraping loop ended. Total new documents downloaded: {new_docs_downloaded}")