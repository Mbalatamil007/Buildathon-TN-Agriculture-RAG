# Tamil Nadu Agriculture Schemes Assistant

A district-selectable Streamlit assistant with English and Tamil answers,
OpenAI embeddings, FAISS + BM25 hybrid retrieval, LangChain query planning,
streaming and LangSmith tracing/feedback. Every Python file has a descriptive
filename.

## Included knowledge PDF

**Title: Tamil Nadu Agriculture Schemes**

**Subtitle: District-wise Reference Guide**

The included PDF represents all 38 Tamil Nadu districts with selected summaries
from inspected official district-government sources. District names and
websites were checked against:
https://lokbhavan.tn.gov.in/districts-of-tamil-nadu/

It is a prepared reference guide, not an official Government Order or a full
current catalogue. Some district entries cover only services or document links;
others contain scheme descriptions and dated benefit examples. Source dates
are displayed. A recent webpage update does not make older scheme-year figures
current. Full original GO PDFs are not bundled.

Files to keep together:

- TN_Agriculture_Schemes.pdf
- TN_Agriculture_Schemes.sources.json

The source sidecar contains exact district tags, source links, dates and PDF
page positions. It is checked against the PDF hash. Cover/directory text is
excluded from retrieval; the indexed records contain district source summaries.
The starter corpus is text-based and does not need paid OCR.

## Application behaviour

- The district dropdown includes **All districts** and all **38 districts**, with
  English/Tamil labels.
- The default answer option is **English + Tamil**. Ask in English and the model
  is instructed to return an English section followed by its Tamil translation,
  preserving citations, numbers and conditions.
- Optional English-only and Tamil-only output are also available.
- District matching uses metadata, including spelling aliases. It does not
  assume a statewide programme is available in every district.
- Both the FAISS candidate corpus and BM25 corpus are scoped to the selected
  district before retrieval. Existing vectors are reused without re-embedding.
- Statewide records are included only if explicitly tagged scope=statewide.
  Untagged records are excluded from a specific-district search.
- The conversation resets when the district or index snapshot changes.
- A question about another district cannot expand the selected scope. Change
  the dropdown when switching districts.
- The UI shows dated source passages and source links. RRF is ranking, not
  answer confidence. Missing information must not be confused with ineligibility.

## Project files

| File | Purpose |
|---|---|
| app.py | Streamlit, district/language dropdowns, chat, voice and sharing |
| config.py | Paths, API/model settings and collector settings |
| districts.py | 38 bilingual district labels, aliases and metadata scope |
| answer_utils.py | Language instructions and missing-evidence replies |
| knowledge_loader.py | Verify source sidecar, PDF hash and page ranges |
| text_splitter.py | Split records while retaining district metadata |
| chunk_inspection.py | Preview chunks |
| embeddings.py | OpenAI embeddings |
| create_faiss_db.py | Build and publish versioned FAISS snapshots |
| similarity_search.py | CLI semantic search |
| retriever.py | District-only vectors, BM25 and reciprocal rank fusion |
| dynamic_user_query.py | Query planning and follow-up resolution |
| rag_pipeline.py | Grounded bilingual streaming answers and trace feedback |
| data_ingestion.py | Optional live portal collection with configurable selectors |
| ocr.py | Cached GPT-4o vision OCR for low-text/scanned PDF pages |
| clean_pdf.py | Optional collected-text PDF generation |
| pdf_validation.py | PDF checks |
| build_knowledge_pdf.py | Rebuild the standard-title PDF from curated sources |
| district_sources.json | Curated official-source summaries for all districts |
| voice.py | OpenAI transcription and read-aloud audio |
| refresh.py | Optional live collection/index refresh job |
| refresh_weekly.cmd | Windows scheduled-job entry point |
| .env.example | Configuration template; copy to .env |
| requirements.txt | Dependencies |
| .gitignore | Exclude secrets and generated files |
| .streamlit/config.toml | Theme |
| assets/ | Optional agriculture_banner.png and tn_logo.png |
| collection_baseline.example.json | Live-collection coverage minimum template |
| tests/ | Offline district, provenance and retrieval tests |

## Step 1 - Extract and install

Open the extracted TN-Agriculture-RAG folder in VS Code. Use 64-bit Python 3.11
or 3.12. Run these commands in Windows CMD inside the project folder:

```bat
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
copy .env.example .env
```

If you already have a venv and .env from the earlier version, activate that venv
and update dependencies. Do not overwrite your existing .env/API keys.
Dependencies are compatible ranges, not an exact tested version lock.

## Step 2 - Configure API keys

Edit .env:

```dotenv
OPENAI_API_KEY=your_actual_key
PDF_PATH=TN_Agriculture_Schemes.pdf
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_MODEL=gpt-4o-mini
OCR_MODEL=gpt-4o
LANGSMITH_TRACING=false
```

The PDF is included: you do not have to scrape the portal to start.
OpenAI embeddings require API billing and send chunk text to OpenAI.
A ChatGPT subscription does not cover API usage.

## Step 3 - Inspect the knowledge

```bat
python pdf_validation.py
python text_splitter.py
python chunk_inspection.py
```

Check the generated chunks for district, source date, source URL and page
metadata. Do not remove or alter the companion source file independently.

## Step 4 - Build or rebuild FAISS

```bat
python create_faiss_db.py
```

**Rebuild even if you used the previous bundle:** this PDF and its district
metadata have changed. Previous snapshots remain as backups, but CURRENT must
point to the newly built snapshot.

Generated files are under vector_db/faiss_index/<snapshot-id>/:

- index.faiss
- documents.json
- TN_Agriculture_Schemes.pdf
- TN_Agriculture_Schemes.sources.json, when supplied

CURRENT is published atomically after the snapshot is built. The indexed PDF,
model, chunk settings, vector count/dimensions and document mapping are checked.
Documents are JSON, not pickle. Stop the app before manual maintenance.

## Step 5 - Start the app

```bat
python -m streamlit run app.py
```

Select **Tiruvarur** and **English + Tamil**, then ask in English:

> What micro-irrigation subsidy is described in the notice dated 5 October 2026?

Try:

- Coimbatore: What documents are listed for horticulture applications?
- Perambalur: What year do the listed maize demonstration guidelines refer to?
- Chennai: What documents are listed for a small/marginal-farmer certificate?
- Theni: Does the indexed notice state the insurance enrolment deadline?
- All districts: Compare the district sources mentioning micro irrigation.

The output should show **English** and **தமிழ்** sections and [S1]-style
citations in both. Compare the passages and source dates. The language
instructions do not guarantee a perfect translation; verify important numbers
and conditions. The Tamil missing-evidence reply is deterministic.

Chat memory is session-only, up to ten turns; the planner receives the last
three turns. Previous answers are not factual evidence. Selecting another
district clears the conversation to prevent follow-up references crossing scopes.

## Step 6 - Enable LangSmith

Set and restart:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_actual_langsmith_key
LANGSMITH_PROJECT=TN-Agriculture-Hybrid-RAG
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

Use your workspace ID or region endpoint when required. Inspect the root
TamilNaduAgricultureRAG run, QueryPlanning, HybridRetrieval,
BM25KeywordSearch, FAISSSemanticSearch and GenerateGroundedAnswer.
The user feedback form attaches feedback to the answer's root run when tracing
is enabled. Tracing is not an independent answer correctness test.

## Step 7 - Optional voice, audio and WhatsApp

Record a voice question, transcribe, review the text and then ask. English,
Tamil and automatic detection for bilingual mode are supported through OpenAI
transcription. Browser microphone permission is required. Read aloud uses an
AI-generated voice and the first 4000 characters; Tamil pronunciation depends
on the service and must be checked. WhatsApp sharing opens a prefilled link and
does not automatically send a message.

## Step 8 - Update the curated PDF

Add or correct verified records in district_sources.json. Keep district names
from districts.py. Retain source_url, source_date, scope, extraction and
coverage_status. A district record must not be labelled statewide without
source evidence of statewide applicability.

```bat
python build_knowledge_pdf.py
python pdf_validation.py
python create_faiss_db.py
```

The builder regenerates the PDF and sidecar together. It does not visit the
source websites automatically. Current source verification remains necessary.
PDF_FONT_PATH and PDF_BOLD_FONT_PATH can point to local TrueType fonts if needed.
The PDF reference is in English; the app generates both answer languages.

## Step 9 - Optional live collection and weekly refresh

The TNAgrisnet portal collector was not live-tested here. First install Chromium:

```bat
python -m playwright install chromium
```

Verify ROW_SELECTOR, DETAIL_SELECTOR, MODAL_SELECTOR, NEXT_SELECTOR,
FILTER_SELECTOR and FILTER_VALUES in .env against the real portal. Exact
ALLOWED_HOSTS must be official hosts required by the source page/GO links.

```bat
python data_ingestion.py
```

Review every row, popup and linked GO PDF before publication. Direct .pdf links,
configured HTML modals, new windows and same-tab HTML details are supported.
JS-only downloads, PDF-viewer iframes, form-based/non-.pdf links, CAPTCHA and
other custom portal actions require adapting the collector. Failed collection
aborts instead of silently omitting detected detail views or failed PDF links.

**District applicability requires review.** The generic portal collector does
not infer district eligibility. Add verified district/districts metadata or
explicit scope=statewide to collected records before district-based answering.
Untagged live records remain available only under All districts. Live refresh
can replace the curated dataset, so do not enable it until its coverage and
metadata mapping meet your needs. It is not a weekly refresh of all 38 district
webpages; the bundled district summaries are a dated snapshot.

Set reviewed minimum_scheme_rows and minimum_go_pdfs in collection_baseline.json,
using the example only as a template. Counts cannot prove full coverage.

```bat
python clean_pdf.py
python pdf_validation.py
python create_faiss_db.py
python refresh.py
```

For an existing PDF rebuild without collection:

```bat
python refresh.py --existing-pdf
```

For a weekly live-portal job, configure Windows Task Scheduler to run cmd.exe
with `/c "C:\path\TN-Agriculture-RAG\refresh_weekly.cmd"`, weekly on Sunday at
09:00, starting in the project folder. Use your real path and the same user
who installed Chromium. Test Run; inspect logs/refresh.log and Last Run Result.
The laptop must be available and online. No schedule is registered by this
bundle. Do not run manual builders concurrently with a refresh. Check any
leftover data/refresh.lock after a crash before removing it.

OCR uses GPT-4o only for low-text pages and has a budget/cache. Mixed scanned
pages and legacy-font Tamil may need manual OCR decisions. OCR is not guaranteed
accurate. Review amounts, dates and table rows against the original images.

## Verification and limitations

```bat
python -m compileall -q .
python -m unittest discover -s tests -v
```

22 offline tests passed in the authoring environment, covering Unicode handling,
rank fusion, provenance/page validation, district aliases, strict district
filtering, pre-candidate scope and bilingual missing-evidence output. The PDF
was rendered and visually checked; all 38 district tags are represented.

Live OpenAI generation/translation, FAISS API integration, LangSmith feedback,
voice, Streamlit UI and portal automation were not executed here. No independent
answer verifier, authentication or production hosting is provided.
OpenAI processes embeddings text, selected passages and optional OCR/audio;
LangSmith receives trace content when enabled. Keep .env out of Git.
