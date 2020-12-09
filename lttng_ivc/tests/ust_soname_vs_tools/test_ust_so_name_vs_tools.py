# Copyright (c) 2017 Jonathan Rajotte-Julien <jonathan.rajotte-julien@efficios.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pytest
import subprocess

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.settings as Settings

"""
TODO: Document how the tests is done and what it tests

At configure time
At build time
At run time

Always include a documentation matrix:
FC: Fully Compatible
BC: Backward Compatible
I: Incompatible

+------------------------------------------------------------------+
| LTTng UST control library vs LTTng Tools                         |
+-----------------------------------------+-----+-----+-----+------+------+------+
| LTTng UST Control(soname) / LTTng Tools | 2.7 | 2.8 | 2.9 | 2.10 | 2.11 | 2.12 |
+-----------------------------------------+-----+-----+-----+------+------+------+
| 2.7 (2.0.0)                             | FC  | I   | I   | I    | I    | I    |
| 2.8 (2.0.0)                             | BC  | FC  | I   | I    | I    | I    |
| 2.9 (2.0.0)                             | BC  | BC  | FC  | I    | I    | I    |
| 2.10 (4.0.0)                            | I   | I   | I   | FC   | FC   | FC   |
| 2.11 (4.0.0)                            | I   | I   | I   | FC   | FC   | FC   |
| 2.12 (4.0.0)                            | I   | I   | I   | FC   | FC   | FC   |
+-----------------------------------------+-----+-----+-----+------+------+------+

In this scenario:

FC and BC must pass configure, build and run time
I must fail at configure, build and run time.

"""

"""
First tuple member: lttng-ust label
Second tuple member: lttng-tool label
Third tuple member: Success.
                    True -> expect success
                    False -> expect failure
"""

test_matrix_label = [
    ("lttng-ust-2.7", "lttng-tools-2.7", True),
    ("lttng-ust-2.7", "lttng-tools-2.8", False),
    ("lttng-ust-2.7", "lttng-tools-2.9", False),
    ("lttng-ust-2.7", "lttng-tools-2.10", False),
    ("lttng-ust-2.7", "lttng-tools-2.11", False),
    ("lttng-ust-2.7", "lttng-tools-2.12", False),
    ("lttng-ust-2.8", "lttng-tools-2.7", True),
    ("lttng-ust-2.8", "lttng-tools-2.8", True),
    ("lttng-ust-2.8", "lttng-tools-2.9", False),
    ("lttng-ust-2.8", "lttng-tools-2.10", False),
    ("lttng-ust-2.8", "lttng-tools-2.11", False),
    ("lttng-ust-2.8", "lttng-tools-2.12", False),
    ("lttng-ust-2.9", "lttng-tools-2.7", True),
    ("lttng-ust-2.9", "lttng-tools-2.8", True),
    ("lttng-ust-2.9", "lttng-tools-2.9", True),
    ("lttng-ust-2.9", "lttng-tools-2.10", False),
    ("lttng-ust-2.9", "lttng-tools-2.11", False),
    ("lttng-ust-2.9", "lttng-tools-2.12", False),
    pytest.param(
        "lttng-ust-2.10",
        "lttng-tools-2.7",
        False,
        marks=pytest.mark.xfail(reason="Should fail but does not ...."),
    ),
    pytest.param(
        "lttng-ust-2.10",
        "lttng-tools-2.8",
        False,
        marks=pytest.mark.xfail(reason="Should fail but does not ...."),
    ),
    pytest.param(
        "lttng-ust-2.10",
        "lttng-tools-2.9",
        False,
        marks=pytest.mark.xfail(reason="Should fail but does not ...."),
    ),
    ("lttng-ust-2.10", "lttng-tools-2.10", True),
    ("lttng-ust-2.10", "lttng-tools-2.11", False),
    pytest.param(
        "lttng-ust-2.11",
        "lttng-tools-2.7",
        False,
        marks=pytest.mark.xfail(reason="Should fail but does not ...."),
    ),
    pytest.param(
        "lttng-ust-2.11",
        "lttng-tools-2.8",
        False,
        marks=pytest.mark.xfail(reason="Should fail but does not ...."),
    ),
    pytest.param(
        "lttng-ust-2.11",
        "lttng-tools-2.9",
        False,
        marks=pytest.mark.xfail(reason="Should fail but does not ...."),
    ),
    ("lttng-ust-2.11", "lttng-tools-2.10", True),
    ("lttng-ust-2.11", "lttng-tools-2.11", True),
    ("lttng-ust-2.11", "lttng-tools-2.12", False),
    pytest.param(
        "lttng-ust-2.12",
        "lttng-tools-2.7",
        False,
        marks=pytest.mark.xfail(reason="Should fail but does not ...."),
    ),
    pytest.param(
        "lttng-ust-2.12",
        "lttng-tools-2.8",
        False,
        marks=pytest.mark.xfail(reason="Should fail but does not ...."),
    ),
    pytest.param(
        "lttng-ust-2.12",
        "lttng-tools-2.9",
        False,
        marks=pytest.mark.xfail(reason="Should fail but does not ...."),
    ),
    ("lttng-ust-2.12", "lttng-tools-2.10", True),
    ("lttng-ust-2.12", "lttng-tools-2.11", True),
    ("lttng-ust-2.12", "lttng-tools-2.12", True),
]

runtime_matrix_label = Settings.generate_runtime_test_matrix(test_matrix_label, [0, 1])


@pytest.mark.parametrize(
    "ust_label,tools_label,should_pass", runtime_matrix_label
)
def test_soname_configure(
    tmpdir, ust_label, tools_label, should_pass
):
    ust = ProjectFactory.get_fresh(ust_label, str(tmpdir.mkdir("lttng-ust")))
    tools = ProjectFactory.get_fresh(tools_label, str(tmpdir.mkdir("lttng-tools")))

    ust.autobuild()

    # Replace the default lttng-ust for lttng-tools
    tools.dependencies["lttng-ust"] = ust

    # TODO: Propose fixes to upstream regarding the check
    if not should_pass:
        # Making sure we get a error here
        pytest.xfail("passing configure but should fail See todo")
        with pytest.raises(subprocess.CalledProcessError) as error:
            tools.configure()
        print(error)
    else:
        # An exception is thrown on errors
        # TODO MAYBE: wrap around a try and perform error printing + save
        # stdout stderr etc. Or move all this handling inside the function and
        # reraise the error (bubble up)
        tools.configure()
