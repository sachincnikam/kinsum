import os
import tempfile

# Tests never touch the real data folder.
os.environ.setdefault("KINSUM_DATA_DIR", tempfile.mkdtemp(prefix="kinsum-test-"))
os.environ.setdefault("ANTHROPIC_API_KEY", "")
