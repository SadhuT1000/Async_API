#!/usr/bin/env python3
import os
import time

from elasticsearch import Elasticsearch

if __name__ == "__main__":
    es_url = os.getenv("ES_URL", "http://localhost:9200")
    es_client = Elasticsearch(es_url)
    res = es_client.info()
    while True:
        if es_client.ping():
            break
        time.sleep(1)
