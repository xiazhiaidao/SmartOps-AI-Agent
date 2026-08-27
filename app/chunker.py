"""文本切分：适配中英文混合内容。"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 中文优先按段落 / 句号切分，保留更多语义完整性
SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]


def create_splitter(chunk_size: int = 500, chunk_overlap: int = 80):
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
        keep_separator=True,
    )
