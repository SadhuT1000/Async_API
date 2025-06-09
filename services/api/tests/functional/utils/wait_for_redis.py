#!/usr/bin/env python3
import os
import time

from redis import Redis, exceptions

if __name__ == "__main__":
    redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
    r = Redis(redis_host, socket_connect_timeout=1)

    while True:
        try:
            r.ping()
            break
        except exceptions.ConnectionError:
            print("Ping redis attempt: ", redis_host)
            time.sleep(1)
