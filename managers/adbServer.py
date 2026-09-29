import subprocess
import time


TIMEOUT = 5
ADB_BASE = ["adb"]
ADB_SUDO_BASE = ["sudo" , "adb"]

class Adb:
    def _run(self,*args,**kwargs):
        return subprocess.run(ADB_BASE+list(args),**kwargs)

    def _sudo_run(self,*args,**kwargs):
        return subprocess.run(ADB_SUDO_BASE+list(args),**kwargs)

    def _popen(self,*args,**kwargs):
        return subprocess.Popen(ADB_BASE + list(args) , **kwargs)

    def _sudo_popen(self,*args,**kwargs):
        return subprocess.Popen(ADB_SUDO_BASE + list(args) , **kwargs)

    def start_server(self,**kwargs):
        return self._run("start-server",**kwargs)

    def kill_server(self):
        return self._run("kill-server")

    def connect_device(self,device_IP,device_port,**kwargs):
        return self._run("connect", f"{device_IP}:{device_port}" , **kwargs )

    def wait_until_ready(self,timeout=60):
        print("[ADB] waiting for device...")
        self._run("wait-for-device")
        print("[ADB] Device ready")

        print("[ADB] waiting for android to boot...")
        start = time.monotonic()

        while time.monotonic() - start < timeout:
            result = self._run(
                    "shell",
                    "getprop",
                    "sys.boot_completed",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                    )
            
            if result.stdout.strip() == "1":
                print("[ADB] android boot complete")
                return
            time.sleep(1)

        raise TimeoutError(f"Android failed to boot within timeout:{timeout}.")


    def push(self, binary_filepath, dest_filepath,**kwargs):
        # handle empty filepaths TODO
        return self._run("push",binary_filepath,dest_filepath,**kwargs)

    def pidof(self,process_name):
        if not process_name :
            raise ValueError("process_name cant be empty")
            
        res = self.shell("pidof",process_name,capture_output=True);

        if res.returncode != 0:
            return None

        return int(res.stdout.strip())


    
    def process_running(self,process_name,timeout=5):
        if process_name is None:
            raise AttributeError("[ADB] Process Name cannot be empty")

        start = time.monotonic()
        
        while time.monotonic() - start < timeout:
            result = self.shell("pidof",process_name,capture_output=True);
            if result.returncode == 0:
                return True
        
        return False

        
    def is_process_root(self,process_name):
        if process_name is None:
            return False

        result = self.shell("ps","-A",capture_output=True,text=True)
        for line in result.stdout.splitlines():
            cols = line.split()
            if cols and cols[-1] == process_name:
                return (cols[0]=="root")
        return False

    def shell(self, *command, **kwargs):
        result = self._run("shell", *command, **kwargs)
        return result

    def install_split_app(self,base_apk_filepath,split_apk_filepath,**kwargs):
        result = self._run(
                "install-multiple",
                base_apk_filepath,
                split_apk_filepath,
                **kwargs)
        return result
    
    def package_installed(self,package_name,**kwargs):
        result = self.shell("pm", "list", "packages", capture_output=True, text=True, **kwargs)
        output = result.stdout

        for line in output.splitlines():
            _,name = line.split(":",1)  

            if name == package_name:
                return True

        return False

    def launch_app(self, app,**kwargs):
        return self.shell("am","start","-n",app,**kwargs)

def main():
    ## testing thats it
    adb_instance = Adb()
    adb_instance.start_server()
    # adb_instance.connect_device("192.168.240.112","5555")
    print(adb_instance.shell(
        "test",
        "-f",
        "/data/local/tmp/frida-server"
        ).returncode)
    print(adb_instance.package_installed("com.setsnail.daddylonglegs"))
    print(adb_instance.process_running("frida-server"))
    print(adb_instance.is_process_root("frida-server"))
    print(adb_instance.pidof("com.setsnail.daddylonglegs"))
    

if __name__ == "__main__" :
    main()       
