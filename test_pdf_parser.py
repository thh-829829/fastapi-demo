import fitz

def extract_text_from_pdf(file_path: str) ->str:
    """读取本地PDF文件, 提取全部文本"""
    doc = fitz.open(file_path)
    full_text = ""
    for page_num, page in enumerate(doc):
        page_text = page.get_text()
        full_text += f"---第{page_num+1}页 ---\n{page_text}\n"
    doc.close()
    return full_text
if __name__ == "__main__":
    pdf_content = extract_text_from_pdf("test.pdf")
    print("=== PDF提取结果前500字 ===")
    print(pdf_content[:500])
    print("\n=== 提取总字符数: ", len(pdf_content))
