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


def __dummy_sigusr1_handler():
    pass


def sessiond_spawn(runtime):
    agent_port = find_free_port()
    previous_handler = signal.signal(signal.SIGUSR1, __dummy_sigusr1_handler)
    sessiond = runtime.spawn_subprocess("lttng-sessiond -vvv -S --agent-tcp-port {}".format(agent_port))
    signal.sigtimedwait({signal.SIGUSR1}, 60)
    previous_handler = signal.signal(signal.SIGUSR1, previous_handler)
    return sessiond


def find_free_port():
    # There is no guarantee that the port will be free at runtime but should be
    # good enough
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


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
    print(root)
    print(name)
    abs_path = None
    for base, dirs, files in os.walk(root):
        for tmp in files:
            if tmp.endswith(name):
                abs_path = os.path.abspath(os.path.join(base, tmp))
    print(abs_path)
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
