from memory.semantic_index import index_path
from memory.rag_query import query

def test_auto_index_artifacts(tmp_path):
    d = tmp_path
    (d/'a.txt').write_text('x', encoding='ascii', errors='ignore')
    (d/'b.txt').write_text('y', encoding='ascii', errors='ignore')
    assert index_path(str(d))>=2

def test_retrieval_relevant():
    assert len(query('demo'))>=1
