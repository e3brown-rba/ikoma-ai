import logging
import random
import string
import time

from tools.citation_manager import CitationSource
from tools.vector_store import get_citation_by_id, store_citation_with_metadata

logging.basicConfig(level=logging.INFO)


def random_string(length: int = 32) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def make_citation(idx: int) -> CitationSource:
    return CitationSource(
        id=idx,
        url=f"https://example.com/{idx}",
        title=f"Test Citation {idx}",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        content_preview=random_string(100),
        source_type="web",
        domain="example.com",
        confidence_score=0.9,
    )


def test_citation_store_and_retrieve(batch_size: int = 50) -> None:
    print(f"\n🚀 Performance test: Storing and retrieving {batch_size} citations...")
    store_times = []
    retrieve_times = []
    for i in range(batch_size):
        citation = make_citation(i)
        content = random_string(500)
        t0 = time.time()
        store_citation_with_metadata(citation, content)
        t1 = time.time()
        store_times.append(t1 - t0)
        t0 = time.time()
        result = get_citation_by_id(citation.id)
        t1 = time.time()
        retrieve_times.append(t1 - t0)
        assert result is not None
    print(f"✅ All {batch_size} citations stored and retrieved.")
    print(f"Avg store time: {sum(store_times) / len(store_times):.4f} s")
    print(f"Avg retrieve time: {sum(retrieve_times) / len(retrieve_times):.4f} s")
    print(f"Max store time: {max(store_times):.4f} s")
    print(f"Max retrieve time: {max(retrieve_times):.4f} s")


if __name__ == "__main__":
    test_citation_store_and_retrieve(50)
