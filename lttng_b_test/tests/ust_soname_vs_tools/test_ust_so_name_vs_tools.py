import pytest
import lttng_b_test.utils.ProjectFactory as ProjectFactory
import lttng_b_test.settings as project_settings
import subprocess

"""
TODO: Document how the tests is donne and what it tests

At configure time
At build time
At run time

Always include a documentation matrix:
FC: Fully Compatible
BC: Backward Compatible
I: Incompatible

+------------------------------------------------------------------+
| LTTng UST control library vs LTTng Tools                         |
+-----------------------------------------+-----+-----+-----+------+
| LTTng UST Control(soname) / LTTng Tools | 2.7 | 2.8 | 2.9 | 2.10 |
+-----------------------------------------+-----+-----+-----+------+
| 2.7 (2.0.0)                             | FC  | I   | I   | I    |
| 2.8 (2.0.0)                             | BC  | FC  | I   | I    |
| 2.9 (2.0.0)                             | BC  | BC  | FC  | I    |
| 2.10 (4.0.0)                            | I   | I   | I   | FC   |
+-----------------------------------------+-----+-----+-----+------+

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
    ("lttng-ust-2.7", "lttng-tools-2.7", "lttng-ust-2.7", True),
    ("lttng-ust-2.7", "lttng-tools-2.8", "lttng-ust-2.8", False),
    ("lttng-ust-2.7", "lttng-tools-2.9", "lttng-ust-2.9", False),
    ("lttng-ust-2.7", "lttng-tools-2.10", "lttng-ust-2.10", False),
    ("lttng-ust-2.8", "lttng-tools-2.7", "lttng-ust-2.7", True),
    ("lttng-ust-2.8", "lttng-tools-2.8", "lttng-ust-2.8", True),
    ("lttng-ust-2.8", "lttng-tools-2.9", "lttng-ust-2.9", False),
    ("lttng-ust-2.8", "lttng-tools-2.10", "lttng-ust-2.10", False),
    ("lttng-ust-2.9", "lttng-tools-2.7", "lttng-ust-2.7", True),
    ("lttng-ust-2.9", "lttng-tools-2.8", "lttng-ust-2.8", True),
    ("lttng-ust-2.9", "lttng-tools-2.9", "lttng-ust-2.9", True),
    ("lttng-ust-2.9", "lttng-tools-2.10", "lttng-ust-2.10", False),
    ("lttng-ust-2.10", "lttng-tools-2.7", "lttng-ust-2.7", False),
    ("lttng-ust-2.10", "lttng-tools-2.8", "lttng-ust-2.8", False),
    ("lttng-ust-2.10", "lttng-tools-2.9", "lttng-ust-2.9", False),
    ("lttng-ust-2.10", "lttng-tools-2.10", "lttng-ust-2.10", True),
]

runtime_matrix_label = []
if not project_settings.test_only:
    runtime_matrix_label = test_matrix_label
else:
    for tup in test_matrix_label:
        ust_label, tools_label = tup[0], tup[1]
        if (ust_label in project_settings.test_only or tools_label in
                project_settings.test_only):
            runtime_matrix_label.append(tup)


@pytest.mark.parametrize("ust_label,tools_label,base_tools_ust_dep,should_pass", runtime_matrix_label)
def test_soname_configure(tmpdir, ust_label, tools_label, base_tools_ust_dep, should_pass):
    ust = ProjectFactory.get(ust_label, str(tmpdir.mkdir("lttng-ust")))
    tools = ProjectFactory.get(tools_label, str(tmpdir.mkdir("lttng-tools")))

    ust.autobuild()

    tools.dependencies.append(ust)
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


@pytest.mark.parametrize("ust_label,tools_label,base_tools_ust_dep,should_pass", runtime_matrix_label)
def test_soname_build(tmpdir, ust_label, tools_label, base_tools_ust_dep, should_pass):
    ust = ProjectFactory.get(ust_label, str(tmpdir.mkdir("lttng-ust")))
    tools = ProjectFactory.get(tools_label, str(tmpdir.mkdir("lttng-tools")))
    ust_configure_mockup = ProjectFactory.get(ust_label, str(tmpdir.mkdir("lttng-ust-base")))

    ust.autobuild()
    ust_configure_mockup.autobuild()

    # Fool configure
    tools.dependencies.append(ust_configure_mockup)
    tools.configure()

    # Use ust under test
    tools.special_env_variables["CPPFLAGS"] = ust.get_cppflags()
    tools.special_env_variables["LDFLAGS"] = ust.get_ldflags()
    tools.special_env_variables["LD_LIBRARY_PATH"] = ust.get_ld_library_path()

    if not should_pass:
        # Making sure we get a error here
        with pytest.raises(subprocess.CalledProcessError) as error:
            tools.build()
        print(error)
    else:
        # An exception is thrown on errors
        tools.build()
