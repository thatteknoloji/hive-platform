import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: gerçek Cloudflare API testleri (env gerekli)",
    )


@pytest.fixture
def sample_keywords():
    return [
        {"kelime": "Kuşadası gece kulübü", "rekabet": "orta", "arama_hacmi": "500-1000", "rakip_var": True, "cpc": "0"},
        {"kelime": "Kuşadası bar", "rekabet": "düşük", "arama_hacmi": "100-500", "rakip_var": False, "cpc": "0"},
    ]
