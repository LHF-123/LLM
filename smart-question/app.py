from fastapi import FastAPI, UploadFile, File, Form
from embedding import process_pdf_and_store_embeddings
from retriever import search_similar_chunks
import dashscope
from llm_generator import generate_question
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.staticfiles import StaticFiles
from toword import generate_word_response

app = FastAPI(title="智能出题助手 - 千问 + 向量检索", docs_url=None)

# 挂载静态文件路径
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Custom Swagger UI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css"
    )

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_path = f"data/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    added = process_pdf_and_store_embeddings(file_path)
    return {"message": f"成功添加 {added} 段文本到向量数据库"}

@app.post("/generate/")
async def generate(user_question: str = Form(...)):
    # 1. 获取 query 向量
    query_vector = dashscope.TextEmbedding.call(model="text-embedding-v4",  dimension=1024,input=[user_question]).output['embeddings'][0]['embedding']

    print("🧠 query_vector 维度:", len(query_vector))
    # 2. 检索知识块
    top_chunks = search_similar_chunks(query_vector)

    # 3. 构建 Prompt
    with open("prompt_template.txt", "r", encoding="utf-8") as f:
        template = f.read()
    prompt = template.format(user_question=user_question, retrieved_text="\n".join(top_chunks))

    # 4. 调用千问生成
    result = generate_question(prompt)

    # 5. 写入 Word
    # write_to_word(result)

    # return {"message": "✅ 出题完成", "question": result}
    return generate_word_response(result)
