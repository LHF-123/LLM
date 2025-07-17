import pandas as pd
import re
from io import BytesIO
import markdown2
from bs4 import BeautifulSoup


def markdown_table_to_excel(md_text: str) -> BytesIO:
    """
    参数:
        md_text (str): 包含 Markdown 表格的字符串

    返回:
        BytesIO: 包含 Excel 文件数据的字节流

    异常:
        ValueError: 如果未检测到表格
    """
    # 预处理：修复表格中的换行问题
    cleaned_md = re.sub(r'\|(\s*\n\s*)\|', r'| |', md_text)
    cleaned_md = re.sub(r'\n{2,}', '\n', cleaned_md)

    # 将 Markdown 转换为 HTML
    html = markdown2.markdown(cleaned_md)

    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(html, 'html.parser')

    # 查找所有表格
    tables = soup.find_all('table')

    if not tables:
        # 尝试手动解析表格
        return parse_table_directly(md_text)

    # 获取第一个表格的 HTML 字符串
    table_html = str(tables[0])

    try:
        # 使用 pandas 读取 HTML 表格
        df = pd.read_html(table_html, flavor='html5lib')[0]
    except Exception:
        # 如果 pandas 解析失败，使用手动解析
        return parse_table_directly(md_text)

    # 创建字节流对象
    output = BytesIO()

    # 将 DataFrame 写入 Excel
    df.to_excel(output, index=False, engine='openpyxl')

    # 重置流位置
    output.seek(0)
    return output


def parse_table_directly(md_text: str) -> BytesIO:
    """手动解析 Markdown 表格"""
    # 分割表格行
    rows = []
    for line in md_text.split('\n'):
        line = line.strip()
        if line.startswith('|') and line.endswith('|'):
            # 移除首尾的管道符并分割单元格
            cells = [cell.strip() for cell in line[1:-1].split('|')]
            rows.append(cells)

    if len(rows) < 2:
        raise ValueError("未检测到有效的 Markdown 表格")

    # 创建 DataFrame
    header = rows[0]
    data = rows[2:] if len(rows) > 2 and '---' in rows[1] else rows[1:]

    df = pd.DataFrame(data, columns=header)

    # 创建字节流对象
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output


