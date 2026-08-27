"""文本切分器单元测试。"""
from app.chunker import create_splitter


def test_split_long_chinese_text_into_multiple_chunks():
    text = "这是第一句。这是第二句。这是第三句。" * 100
    splitter = create_splitter(chunk_size=50, chunk_overlap=5)
    chunks = splitter.split_text(text)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_split_preserves_short_text():
    splitter = create_splitter(chunk_size=500, chunk_overlap=80)
    chunks = splitter.split_text("你好，SmartOps 智能客服。")
    assert chunks
    assert "你好" in chunks[0]