"""Weekly job entry point; publishes only fully built index snapshots."""
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from config import BASE_DIR, PDF_PATH, DATA_DIR
from data_ingestion import collect
from clean_pdf import build_pdf
from pdf_validation import validate_pdf
from create_faiss_db import build_index, publish_snapshot

def main(existing_pdf=False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock = DATA_DIR / 'refresh.lock'
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError('A refresh is running, or a crash left data/refresh.lock. Check before removing it.')
    try:
        os.write(handle, str(os.getpid()).encode())
        with tempfile.TemporaryDirectory(dir=DATA_DIR) as temporary:
            work = Path(temporary)
            if existing_pdf:
                candidate = PDF_PATH
            else:
                collected = work / 'collected.json'
                collect(collected)
                baseline_file = BASE_DIR / 'collection_baseline.json'
                if not baseline_file.is_file():
                    shutil.copy2(collected, DATA_DIR / 'collected_for_review.json')
                    raise RuntimeError('Inspect data/collected_for_review.json and configure collection_baseline.json before publishing.')
                baseline = json.loads(baseline_file.read_text(encoding='utf-8'))
                counts = json.loads(collected.read_text(encoding='utf-8'))
                if counts['scheme_rows'] < baseline['minimum_scheme_rows'] or counts['go_pdf_count'] < baseline['minimum_go_pdfs']:
                    raise RuntimeError('Collection fell below reviewed coverage baseline. Previous knowledge stays active.')
                candidate = work / 'TN_Agriculture_Schemes.pdf'
                build_pdf(collected, candidate)
            validate_pdf(candidate)
            snapshot = build_index(candidate, publish=False)
            if not existing_pdf:
                PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, PDF_PATH)
                shutil.copy2(candidate.with_suffix('.sources.json'), PDF_PATH.with_suffix('.sources.json'))
            publish_snapshot(snapshot)
        print('Refresh completed; the new snapshot is active.')
    finally:
        os.close(handle)
        lock.unlink(missing_ok=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--existing-pdf', action='store_true')
    args = parser.parse_args()
    main(args.existing_pdf)
