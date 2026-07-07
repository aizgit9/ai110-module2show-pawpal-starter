"""Makes the project root importable so tests can `import pawpal_system`.

pytest inserts each conftest.py's directory onto sys.path, so placing this at
the repo root lets `tests/test_pawpal.py` import the logic layer directly.
"""
