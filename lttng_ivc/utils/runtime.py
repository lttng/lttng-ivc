import os
import shlex
import subprocess
import uuid
import logging

_logger = logging.getLogger("Runtime")


class Runtime(object):
    def __init__(self, runtime_dir):
        """
        A dictionary of popen object eg. lttng-sessiond, relayd,
        anything really. Key is a uuid.
        """
        self.__subprocess = {}
        self.__stdout_stderr = {}
        self.__projects = []

        self.__runtime_log = os.path.join(runtime_dir, "log")
        self.__runtime_log_sub = os.path.join(self.__runtime_log, "subprocess")

        self._runtime_log_aggregation = os.path.join(self.__runtime_log, "runtime.log")

        self._run_command_count = 0

        self.lttng_home = os.path.join(runtime_dir, "lttng_home")

        # TODO move exist_ok to false !!!! ONLY for testing
        os.makedirs(self.__runtime_log, exist_ok=True)
        os.makedirs(self.__runtime_log_sub, exist_ok=True)
        os.makedirs(self.lttng_home, exist_ok=True)

    def add_project(self, project):
        self.__projects.append(project)

    def subprocess_signal(self, subprocess_uuid, signal):
        self.__subproces[subprocess_uuid].send_signal(signal)

    def subprocess_terminate(self, subprocess_uuid, timeout=60):
        process = self.__subprocess[subprocess_uuid]
        process.terminate()
        process.wait(timeout)
        stdout, stderr = self.__stdout_stderr[subprocess_uuid]
        stdout.close()
        stderr.close()

    def subprocess_kill(self, subprocess_uuid):
        process = self.__subprocess[subprocess_uuid]
        process.kill()
        process.wait()
        stdout, stderr = self.__stdout_stderr[subprocess_uuid]
        stdout.close()
        stderr.close()

    def get_subprocess_stdout_path(self, subprocess_uuid):
        stdout, stderr = self.__stdout_stderr[subprocess_uuid]
        return stdout.name

    def get_subprocess_stderr_path(self, subprocess_uuid):
        stdout, stderr = self.__stdout_stderr[subprocess_uuid]
        return stderr.name

    def spawn_subprocess(self, command_line):
        args = shlex.split(command_line)
        env = self.get_env()

        tmp_id = uuid.uuid1()
        out_path = os.path.join(self.__runtime_log_sub, str(tmp_id) + ".out")
        err_path = os.path.join(self.__runtime_log_sub, str(tmp_id) + ".err")
        stdout = open(out_path, "w")
        stderr = open(err_path, "w")

        p = subprocess.Popen(args, stdout=stdout, stderr=stderr, env=env)
        self.__subprocess[tmp_id] = p
        self.__stdout_stderr[tmp_id] = (stdout, stderr)
        _logger.debug("Spawned sub pid: {} args: {} stdout: {} stderr{}".format(p.pid, p.args, out_path, err_path))

    def run(self, command_line):
        """
        Run the command and return a tuple of a (CompletedProcess, stdout_path,
        stderr_path). The subprocess is already executed and returned. The
        callecaller is responsible for checking for errors.
        """
        args = shlex.split(command_line)
        env = self.get_env()

        tmp_id = self._run_command_count
        self._run_command_count += 1

        out_path = os.path.join(self.__runtime_log, str(tmp_id) + ".out")
        err_path = os.path.join(self.__runtime_log, str(tmp_id) + ".err")
        stdout = open(out_path, "w")
        stderr = open(err_path, "w")

        stdout.write("Output for command #{} {}\n".format(tmp_id, command_line))
        stdout.write("Start >>>>>>>>>>>>>>>>\n")
        stdout.flush()

        stderr.write("Output for command #{} {}\n".format(tmp_id, command_line))
        stderr.write("Start >>>>>>>>>>>>>>>>\n")
        stderr.flush()

        cp = subprocess.run(args, stdout=stdout, stderr=stderr, env=env)
        _logger.debug("Command #{} args: {} stdout: {} stderr{}".format(tmp_id, cp.args, out_path, err_path))

        stdout.write("End <<<<<<<<<<<<<<<<\n")
        stdout.close()

        stderr.write("End <<<<<<<<<<<<<<<<\n")
        stderr.close()

        # Add to the global log file. This can help a little. Leave the other
        # file available for per-run analysis
        with open(self._runtime_log_aggregation, "a") as log:
            with open(out_path, "r") as out:
                log.write(out.read())
            with open(err_path, "r") as out:
                log.write(out.read())

        return (cp, out_path, err_path)

    def get_cppflags(self):
        cppflags = []
        for project in self.__projects:
            cppflags.append(project.get_cppflags())
        return " ".join(cppflags)

    def get_ldflags(self):
        ldflags = []
        for project in self.__projects:
            ldflags.append(project.get_ldflags())
        return " ".join(ldflags)

    def get_ld_library_path(self):
        library_path = []
        for project in self.__projects:
            library_path.append(project.get_ld_library_path())
        return " ".join(library_path)

    def get_bin_path(self):
        path = []
        for project in self.__projects:
            path.append(project.get_bin_path())
        return ":".join(path)

    def get_env(self):
        env = os.environ.copy()

        env["LTTNG_HOME"] = self.lttng_home

        env_fetch = {"CPPFLAGS": (self.get_cppflags(), " "),
                     "LDFLAGS": (self.get_ldflags(), " "),
                     "LD_LIRABRY_PATH": (self.get_ld_library_path(), ":"),
                     "PATH": (self.get_bin_path(), ":"),
                     }
        for key, (value, delimiter) in env_fetch.items():
            tmp_var = ""
            if key in env:
                tmp_var = env[key]
            env[key] = delimiter.join([value, tmp_var])

        for project in self.__projects:
            for var, value in project.special_env_variables.items():
                if var in env:
                    # Raise for now since no special cases is known
                    _logger.warning("% Special var % is already defined",
                                    self.label, var)
                    raise Exception("Multiple definition of a special environment variable")
                else:
                    env[var] = value
        return env

    def close(self):
        for key, subp in self.__subprocess.items():
            subp.terminate()
        for key, subp in self.__subprocess.items():
            try:
                # TODO move timeout to settings
                subp.wait(timeout=60)
            except subprocess.TimeoutExpired as e:
                # Force a little bit
                subp.kill()
                subp.wait()
        for key, (stdout, stderr) in self.__stdout_stderr.items():
            stdout.close()
            stderr.close()
