#!/usr/bin/env python3
"""Regression gate for stale PostgreSQL sockets after a serverless thaw."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": "postgresql://runtime:password@example.test:5432/snowflake",
            "DB_POOL_MIN_SIZE": "1",
            "DB_POOL_MAX_SIZE": "6",
            "DB_POOL_MAX_IDLE_SECONDS": "60",
            "DB_POOL_MAX_LIFETIME_SECONDS": "300",
            "DB_POOL_RECONNECT_TIMEOUT_SECONDS": "10",
        }
    )
    code = """
import app.postgres_backend as backend

captured = {}
class FakePool:
    @staticmethod
    def check_connection(connection):
        return None
    def __init__(self, **kwargs):
        captured.update(kwargs)
    def wait(self, **kwargs):
        captured['wait'] = kwargs

backend.ConnectionPool = FakePool
backend._POOL = None
backend._pool()
assert callable(captured['check']), captured
assert captured['max_idle'] == 60, captured
assert captured['max_lifetime'] == 300, captured
assert captured['reconnect_timeout'] == 10, captured
assert captured['min_size'] == 1 and captured['max_size'] == 6, captured

class Raw:
    def __init__(self): self.closed = False
    def close(self): self.closed = True
class CheckoutPool:
    def __init__(self): self.raw = Raw(); self.returned = []
    def getconn(self): return self.raw
    def putconn(self, connection): self.returned.append(connection)
checkout_pool = CheckoutPool()
backend._pool = lambda: checkout_pool
backend._prepare_connection = lambda connection: (_ for _ in ()).throw(RuntimeError('stale socket'))
try:
    backend.get_conn()
except RuntimeError:
    pass
else:
    raise AssertionError('stale checkout unexpectedly succeeded')
assert checkout_pool.raw.closed and checkout_pool.returned == [checkout_pool.raw]
print('Serverless PostgreSQL pool: PASS (checkout validation and bounded socket lifetime)')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise AssertionError(f"Serverless pool regression failed:\n{result.stdout}\n{result.stderr}")
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
