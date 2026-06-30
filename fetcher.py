import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, before_sleep_log
from pydantic import BaseModel, Field, ValidationError
import collections

logger = logging.getLogger(__name__)


class HudocDocument(BaseModel):
    """Complete 24-field Schema for HUDOC ESC"""
    document_id: str = Field(alias="escdcidentifier")
    title: Optional[str] = Field(default=None, alias="esctitle")
    language: Optional[str] = Field(default=None, alias="escdclanguage")

    publication_date: Optional[str] = Field(default=None, alias="escpublicationdate")
    publication_date_text: Optional[str] = Field(default=None, alias="escpublicationdateastext")
    decision_date: Optional[str] = Field(default=None, alias="escdatedec")
    decision_date_text: Optional[str] = Field(default=None, alias="escdatedecastext")
    period_start_date: Optional[str] = Field(default=None, alias="escperiodstartdate")
    period_start_date_text: Optional[str] = Field(default=None, alias="escperiodstartdateastext")
    period_end_date: Optional[str] = Field(default=None, alias="escperiodenddate")
    period_end_date_text: Optional[str] = Field(default=None, alias="escperiodenddateastext")

    document_type: Optional[str] = Field(default=None, alias="escdctype")
    raw_document_type: Optional[str] = Field(default=None, alias="escrawdctype")
    document_type_order: Optional[Any] = Field(default=None, alias="escdctypeorder")
    content_store_type: Optional[str] = Field(default=None, alias="esccontentstoretype")
    decision_type: Optional[str] = Field(default=None, alias="escdecisiontype")

    article: Optional[str] = Field(default=None, alias="escarticle")
    article_order: Optional[Any] = Field(default=None, alias="escarticleorder")
    charter_id: Optional[str] = Field(default=None, alias="esccharterid")
    charter_id_order: Optional[Any] = Field(default=None, alias="esccharteridorder")
    state_party: Optional[str] = Field(default=None, alias="escrawstateparty")
    state_party_order: Optional[Any] = Field(default=None, alias="escstatepartyorder")
    complaint_number: Optional[str] = Field(default=None, alias="esccomplnum")
    cycle: Optional[str] = Field(default=None, alias="esccycle")


class HudocApiFetcher:
    def __init__(self, base_url: str = "https://hudoc.esc.coe.int/app/query/results"):
        self.base_url = base_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        self.client = httpx.Client(headers=self.headers, timeout=20.0)
        self.total_fetched = 0
        self.fetched_ids= []
        self.duplicates = 0

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=30),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def sanitize(self, doc):
        if ' ' in doc['columns']['escdcidentifier'] or ';' in doc['columns']['escdcidentifier']:
            for char in [';', ' ']:
                if doc and doc['columns']['escdcidentifier'] and char in doc['columns']['escdcidentifier']:
                    id_list= doc['columns']['escdcidentifier'].split(char)
                    if 'en' in doc['columns']['escdclanguage'].lower():
                        lang = 'en'
                    else:
                        lang = 'fr'

                    new_id=[i for i in id_list if lang in i.lower()][0]
                    if new_id:
                        doc['columns']['escdcidentifier']= new_id
                    else:
                        print('DOC_ID not found for doc ', doc['columns']['escdcidentifier'])
        return doc

    def fetch_metadata_batch(self, query: str, start: int = 0, length: int = 500) -> List[Dict[str, Any]]:
        params = {
            # 👇 We now pass the specific year query dynamically
            "query": query,
            "select": "escarticle,esccontentstoretype,esccomplnum,esccycle,escdatedec,escdecisiontype,escdcidentifier,escdclanguage,escdctype,escperiodstartdate,escperiodenddate,escrawdctype,escrawstateparty,esctitle,esccharterid,escpublicationdate,escdctypeorder,escstatepartyorder,escarticleorder,esccharteridorder,escdatedecastext,escperiodenddateastext,escperiodstartdateastext,escpublicationdateastext",
            "sort": "escpublicationdate Descending",
            "start": start,
            "length": length
        }

        response = self.client.get(self.base_url, params=params)
        response.raise_for_status()

        raw_data = response.json()
        valid_records = []

        for item in raw_data.get("results", []):
            try:
                sanitized_item= self.sanitize(item)
                validated_item = HudocDocument(**sanitized_item.get("columns", sanitized_item))
                valid_records.append(validated_item.model_dump())
            except ValidationError as e:
                logger.error(f"Skipping malformed record: {e}")



        valid_records_ids=[i['document_id'] for i in valid_records]
        valid_records_set = set(valid_records_ids)

        self.total_fetched += len(valid_records_ids)
        self.fetched_ids.extend(list(valid_records_ids))

        self.duplicates += len([item for item, count in collections.Counter(valid_records_ids).items() if count > 1])


        return valid_records


    def close(self):
        self.client.close()


if __name__ == '__main__':

    logger.info("🚀 Initializing the Fetcher test...")

    # 1. Initialize only the fetcher
    fetcher = HudocApiFetcher()
    print(fetcher.sanitize({'columns': {'escdcidentifier': 'CR_XX-1_CZE_FRE (2)', 'escdclanguage':'fr'}}))
    try:
        logger.info("Requesting a micro-batch of 5 documents from HUDOC...")

        # 2. Fetch a tiny batch to see if the network and Pydantic schema work
        batch = fetcher.fetch_metadata_batch(query='contentsitename:ESC AND escpublicationdate:[2012-01-01T00:00:00Z TO 2012-12-31T23:59:59Z]',start=0, length=5)

        if not batch:
            logger.error(
                "❌ The fetcher returned an empty list. The API might be blocking us or the Pydantic schema is rejecting everything.")

        logger.info(f"✅ Success! Successfully fetched and validated {len(batch)} documents.")

        # 3. Pretty-print the first record to verify all your fields are there
        logger.info("Inspecting the fully parsed data of the first document:")
        print("\n" + "=" * 60)
        print(json.dumps(batch, indent=4, ensure_ascii=False))
        print("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"❌ Test crashed with an error: {e}", exc_info=True)
    finally:
        # 4. Clean up
        logger.info("Closing HTTP client connections...")
        fetcher.close()
        logger.info("🏁 Fetcher test complete.")
