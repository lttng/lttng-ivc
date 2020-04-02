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
import os
import shutil
import subprocess

import lttng_ivc.utils.ProjectFactory as ProjectFactory
import lttng_ivc.utils.utils as utils
import lttng_ivc.utils.runtime as Run
import lttng_ivc.settings as Settings

from lttng_ivc.utils.utils import xpath_query

"""
"""


"""
TODO JORAJ why is there missing version here ??????
"""
test_matrix_app_contexts = [
    ("lttng-tools-2.8", "lttng-tools-2.7",   False),
    ("lttng-tools-2.9", "lttng-tools-2.8",   True),
    ("lttng-tools-2.8", "lttng-tools-2.9",   True),
    ("lttng-tools-2.8", "lttng-tools-2.10",  True),
]

test_matrix_blocking_timeout = [
        ("lttng-tools-2.10", "lttng-tools-2.7",   False),
        ("lttng-tools-2.10", "lttng-tools-2.8",   False),
        ("lttng-tools-2.10", "lttng-tools-2.9",   False),
        ("lttng-tools-2.10", "lttng-tools-2.10",  True),
        ("lttng-tools-2.10", "lttng-tools-2.11",  True),
        ("lttng-tools-2.10", "lttng-tools-2.12",  True),
        ("lttng-tools-2.11", "lttng-tools-2.7",   False),
        ("lttng-tools-2.11", "lttng-tools-2.8",   False),
        ("lttng-tools-2.11", "lttng-tools-2.9",   False),
        ("lttng-tools-2.11", "lttng-tools-2.10",  True),
        ("lttng-tools-2.11", "lttng-tools-2.11",  True),
        ("lttng-tools-2.11", "lttng-tools-2.12",  True),
        ("lttng-tools-2.12", "lttng-tools-2.7",   False),
        ("lttng-tools-2.12", "lttng-tools-2.8",   False),
        ("lttng-tools-2.12", "lttng-tools-2.9",   False),
        ("lttng-tools-2.12", "lttng-tools-2.10",  True),
        ("lttng-tools-2.12", "lttng-tools-2.11",  True),
        ("lttng-tools-2.12", "lttng-tools-2.12",  True),

]

test_matrix_monitor_timer_interval = [
        ("lttng-tools-2.10", "lttng-tools-2.7",   False),
        ("lttng-tools-2.10", "lttng-tools-2.8",   False),
        ("lttng-tools-2.10", "lttng-tools-2.9",   False),
        ("lttng-tools-2.10", "lttng-tools-2.10",  True),
        ("lttng-tools-2.10", "lttng-tools-2.11",  True),
        ("lttng-tools-2.10", "lttng-tools-2.12",  True),
        ("lttng-tools-2.11", "lttng-tools-2.7",   False),
        ("lttng-tools-2.11", "lttng-tools-2.8",   False),
        ("lttng-tools-2.11", "lttng-tools-2.9",   False),
        ("lttng-tools-2.11", "lttng-tools-2.10",  True),
        ("lttng-tools-2.11", "lttng-tools-2.11",  True),
        ("lttng-tools-2.11", "lttng-tools-2.12",  True),
        ("lttng-tools-2.12", "lttng-tools-2.7",   False),
        ("lttng-tools-2.12", "lttng-tools-2.8",   False),
        ("lttng-tools-2.12", "lttng-tools-2.9",   False),
        ("lttng-tools-2.12", "lttng-tools-2.10",  True),
        ("lttng-tools-2.12", "lttng-tools-2.11",  True),
        ("lttng-tools-2.12", "lttng-tools-2.12",  True),

]

runtime_matrix_app_contexts = Settings.generate_runtime_test_matrix(test_matrix_app_contexts, [0, 1])
runtime_matrix_blocking_timeout = Settings.generate_runtime_test_matrix(test_matrix_blocking_timeout, [0, 1])
runtime_matrix_monitor_timer_interval = Settings.generate_runtime_test_matrix(test_matrix_monitor_timer_interval, [0, 1])


def validate_app_context(session_name, save_file):
    xpath_provider_name = '/sessions/session[name="{}"]/domains/domain[type="JUL" or type="LOG4J"]/channels/channel/contexts/context/app/provider_name'.format(session_name)
    xpath_ctx_name = '/sessions/session[name="{}"]/domains/domain[type="JUL" or type="LOG4J"]/channels/channel/contexts/context/app/ctx_name'.format(session_name)
    xpath_node_expected = 2

    # Check that the file is present
    assert(os.path.isfile(save_file))
    # Validate provider name
    node_list = xpath_query(save_file, xpath_provider_name)
    assert(len(node_list) == xpath_node_expected)
    for node in node_list:
        assert(node.text == "myRetriever")

    # Validate ctx_name
    node_list = xpath_query(save_file, xpath_ctx_name)
    assert(len(node_list) == xpath_node_expected)
    for node in node_list:
        assert(node.text == "intCtx")


@pytest.mark.parametrize("tools_save_l,tools_load_l,should_load", runtime_matrix_app_contexts)
def test_save_load_app_contexts(tmpdir, tools_save_l, tools_load_l, should_load):

    # Prepare environment
    t_save = ProjectFactory.get_precook(tools_save_l)
    t_load = ProjectFactory.get_precook(tools_load_l)

    t_save_runtime_path = os.path.join(str(tmpdir), "tools-save")
    t_load_runtime_path = os.path.join(str(tmpdir), "tools-load")
    save_load_path = os.path.join(str(tmpdir), 'save_load')
    validation_path = os.path.join(str(tmpdir), 'validation')

    trace_name = "saved_trace"
    trace_filename = trace_name + Settings.save_ext
    trace_file_path = os.path.join(save_load_path, trace_filename)

    validation_file_path = os.path.join(validation_path, trace_filename)

    # Craft the save
    with Run.get_runtime(t_save_runtime_path) as runtime:
        runtime.add_project(t_save)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime)

        runtime.run("lttng create {}".format(trace_name))
        runtime.run("lttng enable-event --jul hello")
        runtime.run("lttng enable-event --log4j hello")
        # NOTE:  For now there is a bug/quirk for which app context is applied
        # everywhere. Might need to be revisited. This influence the number of
        # node we expect in the saved file.
        runtime.run("lttng add-context --jul --type='$app.myRetriever:intCtx'")
        runtime.run("lttng save --output-path={}".format(save_load_path))

        cp = runtime.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond on save return code")

    validate_app_context(trace_name, trace_file_path)

    # Load the save
    with Run.get_runtime(t_load_runtime_path) as runtime:
        runtime.add_project(t_load)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime)

        cmd = "lttng load --input-path={} {}".format(save_load_path, trace_name)

        if not should_load:
            cp, out, err = runtime.run(cmd, check_return=False)
            assert(cp.returncode != 0)
            assert(utils.file_contains(err, ['Session configuration file validation failed']))
            return

        runtime.run(cmd)

        # Since lttng list does not include context we need to re-save and
        # validate that the contexts are presend in the newly saved file.
        runtime.run("lttng save --output-path={}".format(validation_path))

        cp = runtime.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond on load return code")

    validate_app_context(trace_name, validation_file_path)


@pytest.mark.parametrize("tools_save_l,tools_load_l,should_load", runtime_matrix_blocking_timeout)
def test_save_load_blocking_timeout(tmpdir, tools_save_l, tools_load_l, should_load):

    # Prepare environment
    t_save = ProjectFactory.get_precook(tools_save_l)
    t_load = ProjectFactory.get_precook(tools_load_l)

    t_save_runtime_path = os.path.join(str(tmpdir), "tools-save")
    t_load_runtime_path = os.path.join(str(tmpdir), "tools-load")
    save_load_path = os.path.join(str(tmpdir), 'save_load')

    trace_name = "saved_trace"
    channel_name = "my_channel"
    trace_filename = trace_name + Settings.save_ext
    trace_file_path = os.path.join(save_load_path, trace_filename)

    blocking_timeout = 1000

    # Craft the save
    with Run.get_runtime(t_save_runtime_path) as runtime:
        runtime.add_project(t_save)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime)

        runtime.run("lttng create {}".format(trace_name))
        runtime.run("lttng enable-channel -u --blocking-timeout {} {}".format(blocking_timeout, channel_name))
        runtime.run("lttng save --output-path={}".format(save_load_path))


        cp = runtime.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond on save return code")

    assert(os.path.isfile(trace_file_path))

    xpath_blocking_timeout = '/sessions/session[name="{}"]/domains/domain[type="UST"]/channels/channel[name="{}"]/blocking_timeout'.format(trace_name, channel_name)
    node = xpath_query(trace_file_path, xpath_blocking_timeout)
    assert(len(node) == 1)
    assert(node[0].text == str(blocking_timeout))

    # Load the save
    with Run.get_runtime(t_load_runtime_path) as runtime:
        runtime.add_project(t_load)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime)

        if should_load:
            runtime.run("lttng load --input-path={} {}".format(save_load_path, trace_name))
        else:
            with pytest.raises(subprocess.CalledProcessError):
                runtime.run("lttng load --input-path={} {}".format(save_load_path, trace_name))
            cp = runtime.subprocess_terminate(sessiond)
            if cp.returncode != 0:
                pytest.fail("Sessiond on load return code")
            return

        cp, mi_out, err = runtime.run("lttng --mi xml list {}".format(trace_name))

        cp = runtime.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond on load return code")

    assert(os.path.isfile(mi_out))
    xpath_mi_blocking_timeout = '/command/output/sessions/session/domains/domain/channels/channel/attributes/blocking_timeout'
    node = xpath_query(mi_out, xpath_mi_blocking_timeout)
    assert(len(node) == 1)
    assert(node[0].text == str(blocking_timeout))


@pytest.mark.parametrize("tools_save_l,tools_load_l,should_load", runtime_matrix_monitor_timer_interval)
def test_save_load_timer_interval(tmpdir, tools_save_l, tools_load_l, should_load):

    # Prepare environment
    t_save = ProjectFactory.get_precook(tools_save_l)
    t_load = ProjectFactory.get_precook(tools_load_l)

    t_save_runtime_path = os.path.join(str(tmpdir), "tools-save")
    t_load_runtime_path = os.path.join(str(tmpdir), "tools-load")
    save_load_path = os.path.join(str(tmpdir), 'save_load')

    trace_name = "saved_trace"
    channel_name = "my_channel"
    trace_filename = trace_name + Settings.save_ext
    trace_file_path = os.path.join(save_load_path, trace_filename)

    monitor_timer_interval = 1000

    # Craft the save
    with Run.get_runtime(t_save_runtime_path) as runtime:
        runtime.add_project(t_save)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime)

        runtime.run("lttng create {}".format(trace_name))
        runtime.run("lttng enable-channel -u --monitor-timer={} {}".format(monitor_timer_interval, channel_name))
        runtime.run("lttng save --output-path={}".format(save_load_path))

        assert(os.path.isfile(trace_file_path))

        cp = runtime.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond on save return code")

    assert(os.path.isfile(trace_file_path))

    xpath_monitor_interval = '/sessions/session/domains/domain[type="UST"]/channels/channel/monitor_timer_interval'
    node = xpath_query(trace_file_path, xpath_monitor_interval)
    assert(len(node) == 1)
    assert(node[0].text == str(monitor_timer_interval))

    # Load the save
    with Run.get_runtime(t_load_runtime_path) as runtime:
        runtime.add_project(t_load)

        # Start lttng-sessiond
        sessiond = utils.sessiond_spawn(runtime)

        if should_load:
            runtime.run("lttng load --input-path={} {}".format(save_load_path, trace_name))
        else:
            with pytest.raises(subprocess.CalledProcessError):
                runtime.run("lttng load --input-path={} {}".format(save_load_path, trace_name))
            cp = runtime.subprocess_terminate(sessiond)
            if cp.returncode != 0:
                pytest.fail("Sessiond on load return code")
            return

        cp, mi_out, err = runtime.run("lttng --mi xml list {}".format(trace_name))

        cp = runtime.subprocess_terminate(sessiond)
        if cp.returncode != 0:
            pytest.fail("Sessiond on load return code")

    assert(os.path.isfile(mi_out))
    xpath_mi = '/command/output/sessions/session/domains/domain/channels/channel/attributes/monitor_timer_interval'
    node = xpath_query(mi_out, xpath_mi)
    assert(len(node) == 1)
    assert(node[0].text == str(monitor_timer_interval))
