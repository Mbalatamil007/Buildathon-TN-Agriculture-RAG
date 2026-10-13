"""Collect official scheme rows, configured detail views and linked GO PDFs.
Portal-specific selectors must be verified locally before claiming full coverage.
"""
import argparse
import hashlib
import json
import time
from urllib.parse import urljoin, urlparse
from config import (DATA_DIR, PORTAL_URL, ALLOWED_HOSTS, ROW_SELECTOR,
                    DETAIL_SELECTOR, MODAL_SELECTOR, NEXT_SELECTOR, FILTER_SELECTOR,
                    FILTER_VALUES, MAX_ROWS, MAX_PDF_MB)
from playwright.sync_api import sync_playwright
from ocr import read_pdf

def require_official(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.username or parsed.password:
        raise ValueError(f'Unapproved source URL: {url}')
    return url

def links_from(locator, base):
    return [urljoin(base, href) for href in locator.locator('a[href]').evaluate_all(
        '(nodes) => nodes.map(n => n.getAttribute("href"))') if href and not href.startswith(('javascript:', '#'))]

def collect(output):
    require_official(PORTAL_URL)
    records, pdf_urls, seen_rows = [], set(), set()
    budget = {'used': 0}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        # Prevent navigation/download redirects to an unapproved host.
        def guard(route):
            try:
                require_official(route.request.url)
                route.continue_()
            except ValueError:
                route.abort()
        context.route('**/*', guard)
        page = context.new_page()
        for filter_value in FILTER_VALUES or [None]:
            page.goto(PORTAL_URL, wait_until='domcontentloaded', timeout=60000)
            if filter_value is not None:
                if not FILTER_SELECTOR:
                    raise ValueError('FILTER_VALUES requires FILTER_SELECTOR.')
                page.locator(FILTER_SELECTOR).select_option(filter_value)
            page.locator(ROW_SELECTOR).first.wait_for(timeout=30000)
            page_signatures = set()
            while True:
                rows = page.locator(ROW_SELECTOR)
                signature = '\n'.join(rows.all_inner_texts())
                if signature in page_signatures:
                    raise RuntimeError('Pagination repeated a page; check NEXT_SELECTOR.')
                page_signatures.add(signature)
                for index in range(rows.count()):
                    row = rows.nth(index)
                    text = row.inner_text().strip()
                    if not text:
                        continue
                    identity = (filter_value, text)
                    if identity in seen_rows:
                        continue
                    seen_rows.add(identity)
                    if len(seen_rows) > MAX_ROWS:
                        raise RuntimeError('MAX_ROWS exceeded; collection stopped rather than truncated.')
                    title = text.splitlines()[0][:200]
                    records.append({'text': text, 'source': 'Official scheme table',
                                    'scheme': title, 'source_url': PORTAL_URL, 'extraction': 'browser_text'})
                    candidates = links_from(row, page.url)
                    if DETAIL_SELECTOR:
                        target = row.locator(DETAIL_SELECTOR)
                        if target.count() != 1:
                            raise RuntimeError('Each row must match exactly one DETAIL_SELECTOR.')
                        opened = []
                        context.on('page', opened.append)
                        old_url = page.url
                        target.click()
                        try:
                            page.wait_for_function('(s) => Array.from(document.querySelectorAll(s)).some(e => e.getClientRects().length > 0)', arg=MODAL_SELECTOR, timeout=5000)
                        except Exception:
                            # A separate window or same-tab details are handled below.
                            pass
                        context.remove_listener('page', opened.append)
                        if opened:
                            detail = opened[-1]
                            detail.wait_for_load_state('domcontentloaded')
                            require_official(detail.url)
                            scope = detail.locator('body')
                        elif page.url != old_url:
                            require_official(page.url)
                            detail, scope = page, page.locator('body')
                        else:
                            detail, scope = page, page.locator(MODAL_SELECTOR).filter(visible=True)
                            if not scope.count():
                                raise RuntimeError('No detail view found. Check MODAL_SELECTOR; partial collection rejected.')
                            scope = scope.first
                        detail_text = scope.inner_text().strip()
                        if not detail_text:
                            raise RuntimeError('Empty scheme detail view.')
                        records.append({'text': detail_text, 'source': 'Official scheme details',
                                        'scheme': title, 'source_url': detail.url, 'extraction': 'browser_text'})
                        candidates.extend(links_from(scope, detail.url))
                        if detail is not page:
                            detail.close()
                        elif page.url != old_url:
                            page.go_back(wait_until='domcontentloaded')
                        else:
                            close = scope.locator('[data-dismiss="modal"], [data-bs-dismiss="modal"], button.close')
                            if not close.count():
                                raise RuntimeError('No modal close button; adjust collector for portal markup.')
                            close.first.click()
                            scope.wait_for(state='hidden')
                    elif row.locator('button, a[onclick], a[href^="javascript:"]').count():
                        raise RuntimeError('Interactive details detected. Set DETAIL_SELECTOR before collecting.')
                    for url in candidates:
                        if '.pdf' in url.lower():
                            pdf_urls.add(require_official(url))
                if not NEXT_SELECTOR:
                    break
                nxt = page.locator(NEXT_SELECTOR)
                if not nxt.count() or not nxt.first.is_visible() or nxt.first.is_disabled() or nxt.first.get_attribute('aria-disabled') == 'true' or 'disabled' in (nxt.first.get_attribute('class') or ''):
                    break
                nxt.first.click()
                page.wait_for_function('(arg) => Array.from(document.querySelectorAll(arg.s)).map(n=>n.innerText).join("\\n") !== arg.old', arg={'s': ROW_SELECTOR, 'old': signature}, timeout=30000)
        if not records:
            raise RuntimeError('No scheme rows collected.')
        download_dir = DATA_DIR / 'go_pdfs'
        download_dir.mkdir(parents=True, exist_ok=True)
        for url in sorted(pdf_urls):
            # API requests are separately checked; do not follow redirects automatically.
            response = context.request.get(url, max_redirects=0, timeout=60000)
            if not response.ok:
                raise RuntimeError(f'GO download failed ({response.status}): {url}')
            body = response.body()
            if not body.startswith(b'%PDF-') or len(body) > MAX_PDF_MB * 1024 * 1024:
                raise RuntimeError(f'Invalid or oversized GO PDF: {url}')
            path = download_dir / (hashlib.sha256(url.encode()).hexdigest()[:24] + '.pdf')
            path.write_bytes(body)
            records.extend(read_pdf(path, url, budget))
            time.sleep(0.5)
        browser.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'portal_url': PORTAL_URL, 'collected_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                  'scheme_rows': len(seen_rows), 'go_pdf_count': len(pdf_urls),
                                  'records': records}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Collected {len(seen_rows)} rows, {len(pdf_urls)} GO PDFs. Review coverage before publication.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=str(DATA_DIR / 'collected.json'))
    args = parser.parse_args()
    collect(__import__('pathlib').Path(args.output))
