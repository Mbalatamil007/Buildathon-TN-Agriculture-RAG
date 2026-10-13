"""Central settings. Import before model/tracing integrations."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

def setting_path(name, default):
    path = Path(os.getenv(name, default)).expanduser()
    return path if path.is_absolute() else BASE_DIR / path

PDF_PATH = setting_path('PDF_PATH', 'TN_Agriculture_Schemes.pdf')
DATA_DIR = BASE_DIR / 'data'
INDEX_ROOT = BASE_DIR / 'vector_db' / 'faiss_index'
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
OCR_MODEL = os.getenv('OCR_MODEL', 'gpt-4o')
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1200'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))
SEARCH_K, TOP_K, RRF_K = 10, 6, 60
BM25_WEIGHT, FAISS_WEIGHT = 0.5, 0.5
PORTAL_URL = os.getenv('PORTAL_URL', 'https://www.tnagrisnet.tn.gov.in/home/schemes/')
ALLOWED_HOSTS = set(os.getenv('ALLOWED_HOSTS', 'www.tnagrisnet.tn.gov.in,tnagrisnet.tn.gov.in').split(','))
ROW_SELECTOR = os.getenv('ROW_SELECTOR', 'table tbody tr')
DETAIL_SELECTOR = os.getenv('DETAIL_SELECTOR', '')
MODAL_SELECTOR = os.getenv('MODAL_SELECTOR', '.modal.show, .modal.in')
NEXT_SELECTOR = os.getenv('NEXT_SELECTOR', '')
FILTER_SELECTOR = os.getenv('FILTER_SELECTOR', '')
FILTER_VALUES = [v.strip() for v in os.getenv('FILTER_VALUES', '').split(',') if v.strip()]
MAX_OCR_PAGES = int(os.getenv('MAX_OCR_PAGES', '100'))
MAX_ROWS = int(os.getenv('MAX_ROWS', '2000'))
MAX_PDF_MB = int(os.getenv('MAX_PDF_MB', '30'))

def validate_api_keys():
    if not os.getenv('OPENAI_API_KEY', '').strip():
        raise ValueError('Add OPENAI_API_KEY to .env.')
    if os.getenv('LANGSMITH_TRACING', 'false').lower() == 'true' and not os.getenv('LANGSMITH_API_KEY', '').strip():
        raise ValueError('Set LANGSMITH_API_KEY or LANGSMITH_TRACING=false.')
    if not 0 <= CHUNK_OVERLAP < CHUNK_SIZE:
        raise ValueError('CHUNK_OVERLAP must be smaller than CHUNK_SIZE.')
