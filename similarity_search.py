import argparse
from retriever import load_knowledge, search_faiss

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('question', nargs='?', default='What agriculture subsidies are available?')
    args = parser.parse_args()
    for doc in search_faiss(args.question, load_knowledge()):
        print(doc.metadata)
        print(doc.page_content[:700], '\n')
