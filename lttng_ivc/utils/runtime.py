import os
import sys
import shlex
import subprocess
import uuid
import logging
import shutil
import contextlib
import pprint
import traceback

from tempfile import TemporaryDirectory

import lttng_ivc.settings as Settings
_logger = logging.getLogger("Runtime")


@contextlib.contextmanager
def get_runtime(runtime_dir):
    runtime = Runtime(runtime_dir)
    try:
        yield runtime
    finally:
        runtime.close()


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

        """
        Path of the copy of lttng_home folder after Runtime.close() is issued. This is
        to be used for post runtime analysis and mostly debugging on error.
        """
        self.__post_runtime_lttng_home_path = os.path.join(runtime_dir,
                "lttng_home")

        self._runtime_log_aggregation = os.path.join(self.__runtime_log, "runtime.log")

        self._run_command_count = 0

        self.special_env_variables = {"LTTNG_UST_DEBUG": "1",
                                      #"LTTNG_APP_SOCKET_TIMEOUT": "-1",
                                      #"LTTNG_UST_REGISTER_TIMEOUT": "-1",
                                      "LTTNG_NETWORK_SOCKET_TIMEOUT": "-1"}

        # Keep a reference on the object to keep it alive. It will close/clean on
        # exit.
        self.__lttng_home_dir = TemporaryDirectory(prefix=Settings.tmp_object_prefix)
        self.lttng_home = self.__lttng_home_dir.name

        if len(self.lttng_home) > 88:
            raise Exception("TemporaryDirectory for lttng_home is to long. Use a short TMPDIR")

        os.makedirs(self.__runtime_log)
        os.makedirs(self.__runtime_log_sub)

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
        return process

    def subprocess_kill(self, subprocess_uuid):
        process = self.__subprocess[subprocess_uuid]
        process.kill()
        process.wait()
        stdout, stderr = self.__stdout_stderr[subprocess_uuid]
        stdout.close()
        stderr.close()
        return process

    def get_subprocess_stdout_path(self, subprocess_uuid):
        stdout, stderr = self.__stdout_stderr[subprocess_uuid]
        return stdout.name

    def get_subprocess_stderr_path(self, subprocess_uuid):
        stdout, stderr = self.__stdout_stderr[subprocess_uuid]
        return stderr.name

    def spawn_subprocess(self, command_line, cwd=None):
        args = shlex.split(command_line)
        env = self.get_env()

        if not os.path.isdir(self.lttng_home):
            raise Exception("lttng home does not exist")

        tmp_id = uuid.uuid1()
        out_path = os.path.join(self.__runtime_log_sub, str(tmp_id) + ".out")
        err_path = os.path.join(self.__runtime_log_sub, str(tmp_id) + ".err")

        stdout = open(out_path, 'w')
        stderr = open(err_path, 'w')

        env_path = os.path.join(self.__runtime_log_sub, str(tmp_id) + ".env")
        with open(env_path, 'w') as env_out:
            pprint.pprint(env, stream=env_out)

        p = subprocess.Popen(args, stdout=stdout, stderr=stderr, env=env, cwd=cwd)
        self.__subprocess[tmp_id] = p
        self.__stdout_stderr[tmp_id] = (stdout, stderr)
        _logger.debug("Spawned sub pid: {} args: {} stdout: {} stderr{}".format(p.pid, p.args, out_path, err_path))
        return tmp_id

    def run(self, command_line, cwd=None, check_return=True, ld_preload=""):
        """
        Run the command and return a tuple of a (CompletedProcess, stdout_path,
        stderr_path). The subprocess is already executed and returned. The
        callecaller is responsible for checking for errors.
        """
        args = shlex.split(command_line)
        env = self.get_env()

        if ld_preload:
            env['LD_PRELOAD'] = ld_preload


        tmp_id = self._run_command_count
        self._run_command_count += 1

        cmd_map = os.path.join(self.__runtime_log, "cmd.map")
        with open(cmd_map, 'a') as out:
            out.write("{}: {}\n".format(tmp_id, args))

        out_path = os.path.join(self.__runtime_log, str(tmp_id) + ".out")
        err_path = os.path.join(self.__runtime_log, str(tmp_id) + ".err")
        stdout = open(out_path, "w")
        stderr = open(err_path, "w")

        env_path = os.path.join(self.__runtime_log, str(tmp_id) + ".env")
        with open(env_path, 'w') as env_out:
            for key, value in env.items():
                env_out.write('{}={}\n'.format(key, value))

        cp = subprocess.run(args, stdout=stdout, stderr=stderr, env=env, cwd=cwd)
        _logger.debug("Command #{} args: {} stdout: {} stderr{}".format(tmp_id, cp.args, out_path, err_path))

        # Add to the global log file. This can help a little. Leave the other
        # file available for per-run analysis
        with open(self._runtime_log_aggregation, "a") as log:
            with open(out_path, "r") as out:
                log.write("Output for command #{} {}\n".format(tmp_id, command_line))
                log.write("Start >>>>>>>>>>>>>>>>\n")
                log.write(out.read())
                log.write("End <<<<<<<<<<<<<<<<\n")
            with open(err_path, "r") as out:
                log.write("Error for command #{} {}\n".format(tmp_id, command_line))
                log.write("Start >>>>>>>>>>>>>>>>\n")
                log.write(out.read())
                log.write("End <<<<<<<<<<<<<<<<\n")

        if check_return:
            cp.check_returncode()

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
        return ":".join(library_path)

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
                     "LD_LIBRARY_PATH": (self.get_ld_library_path(), ":"),
                     "PATH": (self.get_bin_path(), ":"),
                     }
        for key, (value, delimiter) in env_fetch.items():
            tmp_var = ""
            if key in env:
                tmp_var = env[key]
            env[key] = delimiter.join([value, tmp_var])

        for var, value in self.special_env_variables.items():
            if var in env:
                # Raise for now since no special cases is known
                _logger.warning("% Special var % is already defined",
                                self.label, var)
                raise Exception("Multiple definition of a special environment variable")
            else:
                env[var] = value

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

    def load_test_module(self):
        # Base directory is provided by env
        self.run("modprobe lttng-test")

    def unload_test_module(self, check_return=True):
        # Base directory is provided by env
        self.run("modprobe -r lttng-test", check_return=check_return)

    def close(self):
        for key, subp in self.__subprocess.items():
            subp.terminate()
        for key, subp in self.__subprocess.items():
            # TODO move timeout to settings
            subp.wait(timeout=60)
        for key, (stdout, stderr) in self.__stdout_stderr.items():
            stdout.close()
            stderr.close()

        # Always try to remove test module but do not perform check on return
        # value.
        self.unload_test_module(False)

        # Copy the lttng_home used at runtime using hardlink to prevent useless
        # data duplication
        shutil.copytree(self.lttng_home, self.__post_runtime_lttng_home_path, copy_function=os.link)

