import json
from config import DATA_DIR

if __name__ == '__main__':
    path = DATA_DIR / 'chunks.json'
    if not path.is_file():
        raise SystemExit('Run python text_splitter.py first.')
    chunks = json.loads(path.read_text(encoding='utf-8'))
    print('Total chunks:', len(chunks))
    for row in chunks[:5]:
        print(row['metadata'])
        print(row['text'][:700], '\n')
