import os
import sys
import subprocess
import time
import frida

# Relative import setup for adbServer and waydroidManager when inside managers package
try:
    from .adbServer import Adb
    from .waydroidManager import Waydroid
except ImportError:
    from adbServer import Adb
    from waydroidManager import Waydroid

# Constants and default paths
AGENT_TS_FILENAME = "frida_rpc_conn.ts"
AGENT_JS_FILENAME = "frida_rpc_conn.js"
FRIDA_SERVER_FILENAME = "frida-server"
FRIDA_SERVER_DESTPATH = "/data/local/tmp/frida-server"
REALM = "emulated"
TIMEOUT = 5

# Compute absolute paths relative to this file
MANAGERS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(MANAGERS_DIR, ".."))
FRIDA_AGENT_DIR = os.path.join(PROJECT_ROOT, "frida-agent")
FRIDA_SERVER_FILEPATH = os.path.join(PROJECT_ROOT, "assets", FRIDA_SERVER_FILENAME)


class FridaManager:
    def __init__(
        self,
        agent_ts_filename=AGENT_TS_FILENAME,
        agent_js_filename=AGENT_JS_FILENAME,
        frida_agent_dir=FRIDA_AGENT_DIR,
        frida_server_filepath=FRIDA_SERVER_FILEPATH,
        frida_server_destpath=FRIDA_SERVER_DESTPATH,
        adb=None,
        container=None,
    ):
        self.agent_ts_filename = agent_ts_filename
        self.agent_js_filename = agent_js_filename
        self.frida_agent_dir = frida_agent_dir
        self.frida_server_filepath = frida_server_filepath
        self.frida_server_destpath = frida_server_destpath

        self.adb = adb if adb is not None else Adb()
        self.container = container if container is not None else Waydroid()

        self.device  = None
        self.session = None
        self.script = None
        self.api = None

    def compile_script(self, ts_filename=None, js_filename=None):
        """
        Compiles the TypeScript agent using npx frida-compile inside the frida-agent directory.
        Command: npx frida-compile frida_rpc_conn.ts -o frida_rpc_conn.js
        """
        ts_filename = ts_filename or self.agent_ts_filename
        js_filename = js_filename or self.agent_js_filename

        print(f"[FRIDAMANAGER] Compiling {ts_filename} -> {js_filename} in {self.frida_agent_dir}...")
        cmd = ["npx", "frida-compile", ts_filename, "-o", js_filename]

        result = subprocess.run(
            cmd,
            cwd=self.frida_agent_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[FRIDAMANAGER] Compilation failed:\n{result.stderr}", file=sys.stderr)
            raise RuntimeError(f"[FRIDAMANAGER] Failed to compile Frida script: {result.stderr}")

        print(f"[FRIDAMANAGER] Compilation successful: {js_filename}")
        return os.path.join(self.frida_agent_dir, js_filename)

    def push_binary(self, force=False):
        """
        Pushes frida-server binary to destination on device if not present or if forced.
        """
        result = self.adb.shell(
            "test",
            "-f",
            self.frida_server_destpath
        )

        if result.returncode != 0 or force:
            print(f"[FRIDAMANAGER] Pushing frida-server to {self.frida_server_destpath}...")
            self.adb.push(self.frida_server_filepath, self.frida_server_destpath)
            print("[FRIDAMANAGER] frida-server pushed successfully")
        else:
            print("[FRIDAMANAGER] frida-server already exists on device")

    def run_server(self, timeout=TIMEOUT):
        """
        Ensures frida-server is pushed and running with root privileges on the Waydroid container.
        """
        self.push_binary()

        # Check if already running
        if not self.adb.process_running(FRIDA_SERVER_FILENAME, timeout=1):
            print("[FRIDAMANAGER] Starting frida-server via Waydroid container...")
            _ = self.container._sudo_popen(
                "shell",
                self.frida_server_destpath,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(1)

        # Check process status
        if not self.adb.process_running(FRIDA_SERVER_FILENAME, timeout=timeout):
            raise RuntimeError("[FRIDAMANAGER] frida-server did not run")

        # Check root privilege
        if not self.adb.is_process_root(FRIDA_SERVER_FILENAME):
            raise RuntimeError("[FRIDAMANAGER] frida-server is not running as root, exiting")

        print("[FRIDAMANAGER] frida-server is running as root")

    def get_usb_device(self, timeout=TIMEOUT):
        """
        Retrieves USB device reference via Frida.
        """
        self.device = frida.get_usb_device(timeout=timeout)
        if self.device is None:
            raise RuntimeError("[FRIDAMANAGER] Frida USB device not found")
        return self.device

    def attach(self, target, realm=REALM):
        """
        Attaches Frida session to specified target PID or package name.
        """
        if self.device is None:
            self.get_usb_device()

        assert self.device is not None

        if isinstance(target, str):
            pid = self.adb.pidof(target)
            if pid is None or pid == 0:
                raise RuntimeError(f"[FRIDAMANAGER] Cannot find PID for package {target}")
            target_pid = pid
        else:
            target_pid = target

        print(f"[FRIDAMANAGER] Attaching to PID {target_pid} (realm={realm})...")
        self.session = self.device.attach(target_pid, realm=realm)
        return self.session

    def load_script(self, agent_js_path=None):
        """
        Loads compiled Frida JS script into the active session.
        """
        if self.session is None:
            raise RuntimeError("[FRIDAMANAGER] Session not attached before loading script")

        assert self.session is not None

        if agent_js_path is None:
            agent_js_path = os.path.join(self.frida_agent_dir, self.agent_js_filename)

        with open(agent_js_path, "r") as f:
            script_code = f.read()

        self.script = self.session.create_script(script_code)
        self.script.load()
        self.api = self.script.exports_sync
        print("[FRIDAMANAGER] Script loaded successfully")
        return self.script

    def export_sync(self):
        """
        Returns synchronized RPC exports from the loaded Frida script.
        """
        return self.api

    def wait_for_rpc(self, timeout=TIMEOUT):
        """
        Waits until RPC exports (e.g. get_state) are ready.
        """
        if self.api is None:
            raise RuntimeError("[FRIDAMANAGER] Script exports not initialized")

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self.api.get_state()
                return
            except frida.core.RPCException:
                time.sleep(0.05)
        raise TimeoutError(
            f"[FRIDAMANAGER] RPC exports not ready after {timeout}s"
        )

    def detach(self):
        """
        Unloads script and detaches Frida session gracefully.
        """
        if self.script is not None:
            try:
                self.script.unload()
            except Exception:
                pass
            self.script = None

        if self.session is not None:
            try:
                print("[FRIDAMANAGER] Detaching Frida session...")
                self.session.detach()
            except Exception:
                pass
            self.session = None
        print("[FRIDAMANAGER] Session detached cleanly.")


def main():
    print("[FRIDAMANAGER TEST] Initializing FridaManager...")
    manager = FridaManager()

    print("[FRIDAMANAGER TEST] Testing script compilation...")
    compiled_path = manager.compile_script()
    print(f"[FRIDAMANAGER TEST] Compiled script path: {compiled_path}")
    assert os.path.exists(compiled_path), "Compiled JS file does not exist!"

    print("[FRIDAMANAGER TEST] Checking frida-server binary existence locally...")
    assert os.path.exists(manager.frida_server_filepath), f"Server binary missing at {manager.frida_server_filepath}"
    print(f"[FRIDAMANAGER TEST] Local frida-server binary verified at {manager.frida_server_filepath}")
    print("[FRIDAMANAGER TEST] All non-device unit tests passed successfully!")


if __name__ == "__main__":
    main()
