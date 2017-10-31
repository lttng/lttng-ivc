import os
import pytest

must_be_root = pytest.mark.skipif(os.geteuid() != 0, reason="Must be run as root")
