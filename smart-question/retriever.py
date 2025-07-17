import os
import faiss
import pickle
from typing import List

INDEX_PATH = "index/faiss.index"
TEXT_PATH = "index/texts.pkl"

def load_faiss():
    if os.path.exists(INDEX_PATH):
        index = faiss.read_index(INDEX_PATH)
        with open(TEXT_PATH, "rb") as f:
            texts = pickle.load(f)
    else:
        index = faiss.IndexFlatL2(1024)
        texts = []
    print("📏 当前 FAISS 索引维度:", index.d)
    return index, texts

def save_faiss(index, texts):
    faiss.write_index(index, INDEX_PATH)
    with open(TEXT_PATH, "wb") as f:
        pickle.dump(texts, f)

def add_text_chunks_to_faiss(chunks: List[str], vectors: List[List[float]]):
    index, texts = load_faiss()
    import numpy as np
    index.add(np.array(vectors).astype("float32"))
    texts.extend(chunks)
    save_faiss(index, texts)

def search_similar_chunks(query_vector, top_k=5):
    index, texts = load_faiss()
    import numpy as np
    D, I = index.search(np.array([query_vector]).astype("float32"), top_k)
    return [texts[i] for i in I[0]]
