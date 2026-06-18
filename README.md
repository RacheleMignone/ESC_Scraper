---
license: other
language:
- en
- fr
tags:
- legal
- council-of-europe
- european-social-charter
- human-rights
- bilingual
- parallel-corpus
pretty_name: HUDOC European Social Charter (ESC) Corpus
size_categories:
- 10K<n<100K
task_categories:
- text-classification
- translation
- document-retrieval
- question-answering
---

# Dataset Card for the HUDOC European Social Charter (ESC) Corpus

## Dataset Description

- **Repository:** [Insert your repository link here]
- **Point of Contact:** [Insert your name/contact here]

### Dataset Summary

The **HUDOC European Social Charter (ESC) Corpus** is a comprehensive, bilingual (English and French) dataset containing the decisions, conclusions, and metadata of the European Committee of Social Rights. The data is sourced directly from the Council of Europe's official HUDOC ESC database.

This dataset maps the complex, fragmented API responses into a clean, unified schema. Documents are grouped by their core identifier, providing English and French translations (titles and full texts) alongside 24 highly detailed legal metadata fields on a single row.

### Supported Tasks and Leaderboards

- **`text-classification`**: Classifying documents by article (`escarticle`), state party (`escrawstateparty`), or document type (`escdctype`).
- **`translation`**: Serving as a high-quality, domain-specific comparable/parallel corpus for EN-FR legal translation tasks.
- **`document-retrieval` / `question-answering`**: Building RAG (Retrieval-Augmented Generation) pipelines for human rights law, specific to the European Social Charter.

### Languages

The dataset contains texts in **English** (`en`) and **French** (`fr`).

---

## Dataset Structure

### Data Instances

Each row in the Parquet file represents a single, unique base document. If the document exists in both English and French, both versions of the text and title are included in the same row.

An example instance looks like this:

```json
{
  "base_id": "XXII-4/def/HRV/8/1",
  "api_id_en": "XXII-4/def/HRV/8/1/EN",
  "api_id_fr": "XXII-4/def/HRV/8/1/FR",
  "title_en": "Conclusions XXII-4 (2021) - Croatia - Article 8-1",
  "title_fr": "Conclusions XXII-4 (2021) - Croatie - Article 8-1",
  "text_en": "[Full English document text...]",
  "text_fr": "[Full French document text...]",
  "available_languages": ["EN", "FR"],
  "escarticle": "8",
  "escrawstateparty": "Croatia",
  "escdatedec": "2021-12-07T00:00:00Z",
  "escdctype": "Conclusions"
  // ... plus 20 other metadata fields
}