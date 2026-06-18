import re
import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Set

logger = logging.getLogger(__name__)


class HudocStorage:
    def __init__(self, final_parquet: str = "ESC_Corpus_Final.parquet"):
        self.final_parquet = Path(final_parquet)

    def setup(self):
        # No more temp folders needed!
        pass

    def get_existing_ids(self) -> Set[str]:
        """Reads the final dataset and returns fully completed IDs."""
        if not self.final_parquet.exists():
            return set()

        try:
            df = pd.read_parquet(self.final_parquet)
            valid_ids = set()

            for _, row in df.iterrows():
                if 'text_en' in row and pd.notna(row['text_en']) and row['text_en'] != '':
                    if pd.notna(row.get('api_id_en')):
                        valid_ids.add(str(row['api_id_en']))

                if 'text_fr' in row and pd.notna(row['text_fr']) and row['text_fr'] != '':
                    if pd.notna(row.get('api_id_fr')):
                        valid_ids.add(str(row['api_id_fr']))

            return valid_ids

        except Exception as e:
            logger.error(f"Failed to read existing dataset: {e}")
            return set()

    def append_to_final_dataset(self, new_records: List[Dict]):
        """
        Takes a fresh batch of metadata + text, groups it into EN/FR,
        and directly updates the final Parquet file.
        """
        if not new_records:
            return

        # 1. Convert the flat list to the grouped EN/FR schema
        df_new_flat = pd.DataFrame(new_records)
        df_new_merged = self._merge_flat_to_grouped(df_new_flat)

        # 2. Merge directly into the Final Parquet
        if self.final_parquet.exists():
            try:
                df_existing = pd.read_parquet(self.final_parquet)
                if df_existing.index.name != 'base_id':
                    df_existing.set_index('base_id', inplace=True)

                # combine_first ensures we never overwrite existing valid data,
                # but adds new rows and fills in missing languages for existing rows
                df_final = df_new_merged.combine_first(df_existing)
            except Exception as e:
                logger.error(f"Could not read existing parquet to append: {e}")
                df_final = df_new_merged
        else:
            df_final = df_new_merged

        # 3. Save it back to disk instantly
        df_final.to_parquet(self.final_parquet, engine="pyarrow")
        logger.debug(f"💾 Appended {len(df_new_merged)} unique base records to final dataset.")

    def _merge_flat_to_grouped(self, df_flat: pd.DataFrame) -> pd.DataFrame:
        """Transforms raw API rows into single Base ID rows with EN/FR columns."""

        def parse_doc_id(doc_id):
            match = re.search(r'[_/\-](en|fr)$', str(doc_id), re.IGNORECASE)
            if match:
                return doc_id[:match.start()], match.group(1).lower()
            return doc_id, None

        parsed = [parse_doc_id(id) for id in df_flat['document_id']]
        df_flat['base_id'] = [p[0] for p in parsed]
        df_flat['lang'] = [p[1] for p in parsed]

        metadata_cols = [c for c in df_flat.columns if
                         c not in ["document_id", "title", "document_text", "base_id", "lang"]]

        aggregated = []
        for base_id, group in df_flat.groupby('base_id'):
            row = {
                "base_id": base_id,
                "api_id_en": None, "api_id_fr": None,
                "title_en": None, "title_fr": None,
                "text_en": None, "text_fr": None,
                "available_languages": []
            }

            for col in metadata_cols:
                row[col] = group[col].dropna().iloc[0] if not group[col].dropna().empty else None

            for _, g_row in group.iterrows():
                lang = g_row['lang']
                if not isinstance(lang, str):
                    continue

                row["available_languages"].append(lang.upper())
                row[f"api_id_{lang}"] = g_row.get("document_id")
                row[f"title_{lang}"] = g_row.get("title")

                # Safely extract text
                text_val = g_row.get("document_text")
                row[f"text_{lang}"] = text_val if pd.notna(text_val) else None

            aggregated.append(row)

        df_merged = pd.DataFrame(aggregated)
        df_merged.set_index("base_id", inplace=True)
        return df_merged