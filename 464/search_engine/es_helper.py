import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_engine import ElasticsearchClient
from config.config import ES_HOST, ES_INDEX


def ensure_index(client):
    if not client.es.indices.exists(index=client.index):
        client.create_index()
    return True
