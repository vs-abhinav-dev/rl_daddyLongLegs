"""
Starts running the compiled frida js file in the waydroid container
also exposes methods to run
"""

PACKAGE_NAME = "com.setsnail.daddylonglegs"
AGENT_PATH = "frida_rpc_conn.js"      # compiled output of agent.ts (npx frida-compile agent.ts -o agent.js)
REALM = "emulated"           # same flag you've been passing as --realm=emulated
TIMEOUT = 5

import time
from .waydroidManager import APP, Waydroid
from .adbServer import Adb
from .fridaManager import FridaManager

class ProcessNotFound(Exception):
    pass


class GameClient:
    def __init__(self, package_name = PACKAGE_NAME, agent = AGENT_PATH , realm = REALM , timeout = TIMEOUT):

        ## Initialize device container 
        self.initialize_container()

        ## Initialize the adb server 
        self.initialize_adb_server()

        ## connect the device container to adb server
        print(f"[GAMECLIENT] Connecting waydroid to adb")
        self.adb.connect_device(self.container.HOST,self.container.PORT,capture_output=True)
        print(f"[GAMECLIENT] Connected waydroid to adb")

        ## Initialize FridaManager for compilation and server lifecycle
        self.frida_mgr = FridaManager(adb=self.adb, container=self.container)
        self.frida_mgr.compile_script()
        self.frida_mgr.run_server(timeout=timeout)

        ## Check if the game apk is installed or not
        if not self.adb.package_installed(APP):
            print("[GAMECLIENT] installing apk")
            self.adb.install_split_app("../assets/daddylonglegs.apk","../assets/split_config.arm64_v8a.apk")

        ## wait for the container to initialize 
        self.adb.wait_until_ready()

        ## run the game 
        activity_path = "/com.unity3d.player.UnityPlayerActivity"
        print(f"[GAMECLIENT] Launching the app {package_name}")
        _ = self.adb.launch_app(APP+activity_path,capture_output=True)

        if not self.adb.process_running(PACKAGE_NAME, timeout=TIMEOUT):
            raise RuntimeError(f"[GAMECLIENT] process {PACKAGE_NAME} timed out:{TIMEOUT}")

        print(f"[GAMECLIENT] App {package_name} launched sucessfully")

        ## Game runs alright ig 
        self.package_name = package_name
        self.agent = agent
        self.realm = realm
        self.timeout = timeout

        self.device = self.frida_mgr.get_usb_device()
        if self.device is None:
            print("[GAMECLIENT] device is none")

        if not self.connect():
            raise BrokenPipeError("[GAMECLIENT] cannot connect check logs")
        return 

    def initialize_container(self):
        ## Initialize Waydroid container
        container = Waydroid()
        container.launch()
        self.container = container
        self.device_IP = container.HOST
        self.device_PORT = container.PORT

    def initialize_adb_server(self):
        adb = Adb()
        print(f"[GAMECLIENT] Starting Adb Server")
        adb.start_server(capture_output=True)
        self.adb = adb

    def connect(self):
        # Attach with the pid 
        pid = self.adb.pidof(PACKAGE_NAME) 

        if pid is None:
            print(f"[GAMECLIENT] cannot find pid of package_name {PACKAGE_NAME}")
            # TODO restart the game
            return False

        print(f"[GAMECLIENT] pid of game is: {pid}")

        if pid == 0 :
            return False

        self.session = self.frida_mgr.attach(pid, realm=self.realm)
        self.script = self.frida_mgr.load_script()
        self.api = self.frida_mgr.export_sync()

        # wait for RPC
        self._wait_for_rpc()
        self.last_frame = -1
        return True

    def _wait_for_rpc(self) -> None:
        self.frida_mgr.wait_for_rpc(timeout=self.timeout)

    def state(self):
        """
        Get all the observed state
        """
        return self.api.get_state()

    def tap(self):
        """
        Taps on the game
        """
        return self.api.tap()

    def reset(self):
        """
        Reset the character to initial state
        """
        return self.api.restart()

    def distance(self):
        """
        get the current distance the character is in
        """
        return self.api.getCurrDistance()

    def highscore(self):
        return self.api.getHighscore()

    # TODO: a way to reset the highscore

    def test(self, action=0):
        if action:
            self.api.tap()

        while True:
            state = self.state()
            frame = state.get("frame")
            if frame and self.last_frame != frame:
                self.last_frame = frame
                return frame

    def step_frame(self, action=0, timeout=2.0):
        """
        Executes action (1 = tap, 0 = wait) and waits for the next physics frame tick (FixedUpdate).
        Returns the updated state dictionary.
        """
        if action == 1:
            self.tap()

        start_time = time.time()
        initial_frame = self.last_frame

        while time.time() - start_time < timeout:
            st = self.state()
            if not st:
                time.sleep(0.005)
                continue

            frame = st.get("frame", -1)
            if frame != -1 and frame != initial_frame:
                self.last_frame = frame
                return st
            time.sleep(0.002)

        # Timeout reached, return current state or fallback
        return self.state()

    def close(self):
        """Clean up Frida session gracefully."""
        if hasattr(self, "frida_mgr") and self.frida_mgr:
            self.frida_mgr.detach()
            self.adb.kill_server()
            self.container.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    gameClient = None
    try:
        gameClient = GameClient()
        while True:
            print(f"frames: {gameClient.test()}")
    except KeyboardInterrupt:
        print("\n[GAMECLIENT] Interrupted by user (Ctrl+C). Shutting down...")
    finally:
        if gameClient:
            gameClient.close()
        print("[GAMECLIENT] Exit complete.")


if __name__ == "__main__":
    main()
