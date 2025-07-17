from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse
from extractor import call_llm_with_context
from md2xlsx import markdown_table_to_excel
import tempfile
import fitz  # PyMuPDF 用于 PDF 解析
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.staticfiles import StaticFiles

app = FastAPI(title="智能合同提取助手", docs_url=None)

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


def extract_text_from_pdf(file: UploadFile) -> str:
    # 用 PyMuPDF 提取 PDF 文本
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    doc = fitz.open(tmp_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()


@app.post("/extract")
async def extract_contract_info(
    question: str = Form(..., description="请输入你想问合同的内容"),
    file: UploadFile = File(..., description="上传合同 PDF 文件")
):
    try:
        # Step 1: 提取文件文本
        contract_text = extract_text_from_pdf(file)
        if not contract_text:
            return JSONResponse({"error": "合同内容为空"}, status_code=400)

        # Step 2: 调用 LLM 生成 Markdown 格式答案
        markdown_result = call_llm_with_context(contract_text, question)
        print("=============")
        print(markdown_result)
        print("=============")
        # Step 3: 将 Markdown 转为 Excel 文件流
        excel_io = markdown_table_to_excel(markdown_result)



        # Step 4: 返回 Excel 文件
        return StreamingResponse(
            excel_io,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=contract_info.xlsx"}
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
