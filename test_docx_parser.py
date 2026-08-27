from docx import Document

def extract_text_from_docx(file_path: str) -> str:
    """读取本地docx文件, 提取全部段落文本"""
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():   # 跳过空行
            full_text.append(para.text)
    return "\n".join(full_text)

if __name__ == "__main__":
    docx_content = extract_text_from_docx("test.docx")
    print("=== Word提取结果前500字 ===")
    print(docx_content[:500])
    print("\n=== 提取总字符数: ", len(docx_content))

