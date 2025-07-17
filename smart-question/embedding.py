import time
import pdfplumber
from retriever import add_text_chunks_to_faiss
import dashscope
from http import HTTPStatus

dashscope.api_key = "sk-49dd3d589cfe4e55b72d63e35a771fff"

def extract_text_from_pdf(file_path):
    text = ''
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + '\n'
    return text

def split_text(text, chunk_size=200):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size) if len(text[i:i+chunk_size]) > 10]

def embed_text_qwen(chunks):
    # 过滤太短的内容
    chunks = [c.strip() for c in chunks if len(c.strip()) > 5]
    if not chunks:
        raise ValueError("⚠️ chunks 不能为空")

    batch_size = 10
    all_vectors = []

    # print("👉 传入 embedding 的文本块数量:", len(chunks))
    # print("👉 示例前3个 chunk：", chunks[:3])

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        response = dashscope.TextEmbedding.call(model="text-embedding-v4", dimension=1024, input=batch)

        if response.status_code != HTTPStatus.OK or response.output is None:
            print(f"❌ 第{i // batch_size + 1}批 embedding 调用失败")
            print("状态码:", response.status_code)
            print("错误信息:", response.message)
            raise RuntimeError("Embedding 接口调用失败")
        vectors = [item["embedding"] for item in response.output["embeddings"]]
        all_vectors.extend(vectors)

        # 加一点间隔以防速率限制
        time.sleep(0.5)

    return all_vectors

def process_pdf_and_store_embeddings(file_path):
    text = extract_text_from_pdf(file_path)
    chunks = split_text(text)
    vectors = embed_text_qwen(chunks)

    print(f"✅ 成功生成 {len(vectors)} 条向量")

    add_text_chunks_to_faiss(chunks, vectors)
    return len(chunks)
