from config import EMBEDDING_MODEL, validate_api_keys
from langchain_openai import OpenAIEmbeddings

def get_embeddings():
    validate_api_keys()
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, max_retries=2, request_timeout=60)

if __name__ == '__main__':
    vector = get_embeddings().embed_query('Tamil Nadu agriculture schemes')
    print('Embedding dimensions:', len(vector))
