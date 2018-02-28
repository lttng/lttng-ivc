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

import signal
import hashlib
import os
import time
import socket

from lxml import etree
from contextlib import closing


def line_count(file_path):
    line_count = 0
    with open(file_path) as f:
        for line in f:
            line_count += 1
    return line_count


def sha256_checksum(filename, block_size=65536):
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()


# TODO: timeout as a parameter or Settings
# TODO: Custom exception
def wait_for_file(path):
    i = 0
    timeout = 60
    while not os.path.exists(path):
        time.sleep(1)
        i = i + 1
        if i > timeout:
            raise Exception("File still does not exists. Timeout expired")


# TODO: find better exception
def create_empty_file(path):
    if os.path.exists(path):
        raise Exception("Path already exist")
    open(path, 'w').close()


def __dummy_sigusr1_handler(signum, frame):
    pass


def sessiond_spawn(runtime, opt_args=""):
    agent_port = find_free_port()
    previous_handler = signal.signal(signal.SIGUSR1, __dummy_sigusr1_handler)
    cmd = "lttng-sessiond -vvv --verbose-consumer -S --agent-tcp-port {}".format(agent_port)
    cmd = " ".join([cmd, opt_args])
    sessiond = runtime.spawn_subprocess(cmd)
    signal.sigtimedwait({signal.SIGUSR1}, 60)
    previous_handler = signal.signal(signal.SIGUSR1, previous_handler)
    return sessiond


def relayd_spawn(runtime, url="localhost"):
    """
    Return a tuple (relayd_uuid, ctrl_port, data_port, live_port)
    """
    ports = find_multiple_free_port(3)
    data_port = ports.pop()
    ctrl_port = ports.pop()
    live_port = ports.pop()

    base_cmd = "lttng-relayd -vvv"
    data_string = "-D tcp://{}:{}".format(url, data_port)
    ctrl_string = "-C tcp://{}:{}".format(url, ctrl_port)
    live_string = "-L tcp://{}:{}".format(url, live_port)

    cmd = " ".join([base_cmd, data_string, ctrl_string, live_string])
    relayd = runtime.spawn_subprocess(cmd)

    # Synchronization based on verbosity since no -S is available for
    # lttng-relayd yet.
    log_path = runtime.get_subprocess_stderr_path(relayd)

    # TODO: Move to settings.
    ready_cue = "Listener accepting live viewers connections"
    # TODO: Move to settings.
    timeout = 60
    ready = False
    for i in range(timeout):
        if file_contains(log_path, ready_cue):
            ready = True
            break
        time.sleep(1)

    if not ready:
        # Cleanup is performed by runtime
        raise Exception("Relayd readyness timeout expired")

    return (relayd, ctrl_port, data_port, live_port)


def find_free_port():
    # There is no guarantee that the port will be free at runtime but should be
    # good enough
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def find_multiple_free_port(number):
    """
    Return a list of supposedly free port
    """
    assert(number >= 0)
    ports = []
    while(len(ports) != number):
        port = find_free_port()
        if port in ports:
            continue
        ports.append(port)
    return ports


def file_contains(file_path, list_of_string):
    with open(file_path, 'r') as f:
        for line in f:
            for s in list_of_string:
                if s in line:
                    return True


def find_dir(root, name):
    """
    Returns the absolute path or None.
    """
    abs_path = None
    for base, dirs, files in os.walk(root):
        for tmp in dirs:
            if tmp.endswith(name):
                abs_path = os.path.abspath(os.path.join(base, tmp))
    return abs_path


def find_file(root, name):
    """
    Returns the absolute path or None.
    """
    abs_path = None
    for base, dirs, files in os.walk(root):
        for tmp in files:
            if tmp.endswith(name):
                abs_path = os.path.abspath(os.path.join(base, tmp))
    return abs_path


def validate(xml_path, xsd_path):

    xmlschema_doc = etree.parse(xsd_path)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    xml_doc = etree.parse(xml_path)
    result = xmlschema.validate(xml_doc)

    return result

def xpath_query(xml_file, xpath):
    """
    Return a list of xml node corresponding to the xpath. The list can be of lenght
    zero.
    """
    with open(xml_file, 'r') as f:
        tree = etree.parse(f)
        root = tree.getroot()
        # Remove all namespace
        # https://stackoverflow.com/questions/18159221/remove-namespace-and-prefix-from-xml-in-python-using-lxml
        for elem in root.getiterator():
            if not hasattr(elem.tag, 'find'):
                continue
            i = elem.tag.find('}')
            if i >= 0:
                elem.tag = elem.tag[i+1:]

        return root.xpath(xpath)
