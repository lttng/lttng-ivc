import os
import pytest

root = pytest.mark.skipif(os.geteuid() != 0, reason="Must be run as root")
