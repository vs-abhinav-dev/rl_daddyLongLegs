APP = "com.setsnail.daddylonglegs"
import subprocess
# WAYDROID_BASE = ["/usr/bin/python3", "/usr/bin/waydroid"]
WAYDROID_BASE = ["waydroid"]
class Waydroid:
    def set_suspend_prop(self,boolean):
        if boolean:
            self._run("prop","set","persist.waydroid.suspend","true")
        else:
            self._run("prop","set","persist.waydroid.suspend","false")
            
    def _run(self , *args , **kwargs):
        return subprocess.run(WAYDROID_BASE + list(args) , **kwargs)

    def _popen(self,*args,**kwargs):
        return  subprocess.Popen(WAYDROID_BASE + list(args),**kwargs)

    def _sudo_popen(self,*args,**kwargs):
        ## check if sudo privileddge is there or not 
        subprocess.run(["sudo","-v"],check=True)
        return subprocess.Popen(["sudo"] + WAYDROID_BASE + list(args) , **kwargs)

    def start_session(self):
        log =  open("/tmp/waydroid-session.log","w")
        args = ["session","start"]
        kwargs = {"stdout":log , "stderr": subprocess.PIPE , "text":"True"}
        self._popen(*args,**kwargs)

    def get_session(self):
        result = self._run("status",capture_output = True, text=True)
        output = result.stdout
        status = {}

        for line in output.splitlines():
            if ":" not in line:
                continue

            key,value = line.split(":",1)
            status[key.strip()] = value.strip();

        return status 

    def run_command(self, *command,**kwargs): 
        return self._sudo_popen("shell",*command,**kwargs)

    def launch(self):
        self.start_session()

        while self.get_session()["Session"] != "RUNNING" :
            pass

        print(f"[Waydroid] session {self.get_session()["Session"]}")
        while self.get_session()["IP address"] == "UNKNOWN":
            pass
        self._HOST = self.get_session()["IP address"]
        self._PORT = 5555

        print(f"waydroid active at {self.HOST}:{self.PORT}")

        self.set_suspend_prop(False)

        self._run("show-full-ui")
    
    def stop(self):
        self._run("session","stop")

    @property
    def HOST(self):
        if self._HOST is None:
            return self.get_session()["Session"]
        return self._HOST

    @property
    def PORT(self):
        if self._HOST is None:
            return 5555
        return 5555


def main():
    waydroid = Waydroid()
    waydroid.launch()

if __name__ == "__main__" :
    main()
