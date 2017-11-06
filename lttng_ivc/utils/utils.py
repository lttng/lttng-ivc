import signal
import hashlib
import os
import time

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
    previous_handler = signal.signal(signal.SIGUSR1, __dummy_sigusr1_handler)
    sessiond = runtime.spawn_subprocess("lttng-sessiond -vvv -S")
    signal.sigtimedwait({signal.SIGUSR1}, 60)
    previous_handler = signal.signal(signal.SIGUSR1, previous_handler)
    return sessiond




def file_contains(stderr_file, list_of_string):
    with open(stderr_file, 'r') as stderr:
        for line in stderr:
            for s in list_of_string:
                if s in line:
                    return True
