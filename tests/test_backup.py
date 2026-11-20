import io
import os

import pytest

from app.backup import read_encrypted, verify_file, write_encrypted
from app.coolify import CloneError


def test_large_stream_roundtrip_and_no_plaintext(tmp_path):
    key = os.urandom(32)
    data = b"PRIVATE-DATABASE-PASSWORD" + os.urandom(2500000)
    path = tmp_path / "test.ccb"
    with path.open("wb") as output:
        metadata = write_encrypted(io.BytesIO(data), output, key)
    assert b"PRIVATE-DATABASE-PASSWORD" not in path.read_bytes()
    verify_file(path, key, metadata)
    with path.open("rb") as source:
        assert b"".join(read_encrypted(source, key)) == data


@pytest.mark.parametrize("mutation", ["truncate", "tamper", "append", "wrong-key"])
def test_rejects_tampered_or_incomplete_backup(mutation):
    key = os.urandom(32)
    output = io.BytesIO()
    write_encrypted(io.BytesIO(b"data" * 5000), output, key)
    data = bytearray(output.getvalue())
    if mutation == "truncate":
        data = data[:-20]
    elif mutation == "tamper":
        data[100] ^= 1
    elif mutation == "append":
        data += b"extra"
    else:
        key = os.urandom(32)
    with pytest.raises(CloneError):
        list(read_encrypted(io.BytesIO(data), key))
