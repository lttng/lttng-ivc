import signal

def line_count(file_path):
    line_count = 0
    with open(file_path) as f:
        for line in f:
            line_count += 1
    return line_count


def __dummy_sigusr1_handler():
    pass


def sessiond_spawn(runtime):
        previous_handler = signal.signal(signal.SIGUSR1, __dummy_sigusr1_handler)
        sessiond = runtime.spawn_subprocess("lttng-sessiond -vvv -S")
        signal.sigtimedwait({signal.SIGUSR1}, 60)
        previous_handler = signal.signal(signal.SIGUSR1, previous_handler)
        return sessiond