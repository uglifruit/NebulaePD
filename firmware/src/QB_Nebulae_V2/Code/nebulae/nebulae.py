# Main Nebulae Source File
import sys
import os
from subprocess import Popen
import ctcsound
import controlhandler as ch
import conductor
import ui
import fileloader
import time
import logger
import neb_globals
import ufmigrate
import bootguard
import nebopts
import scengine

cfg_path = "/home/alarm/QB_Nebulae_V2/Code/config/"

debug = False
debug_controls = False
initial_startup = True

# uf2: where every failure lands (owner's choice, 2026-11-10)
SAFE_BANK = 'factory'
SAFE_INSTR = 'a_granularlooper'

class Nebulae(object):

    def __init__(self):
        if neb_globals.remount_fs is False:
            print("Nebulae is operating in \"Read/Write\" mode.")
            print("Filesystem will not be remounted during operation.")
            os.system("/home/alarm/QB_Nebulae_V2/Code/scripts/mountfs.sh rw")
        print "Nebulae Initializing"
        # uf1: on the first start after a firmware update, carry calibration/settings over from the old tree
        self.rw()
        for line in ufmigrate.migrate():
            print "uf1 migrate: " + line
        # uf2: boot-loop guard, see bootguard.py
        guard_fallback = bootguard.on_app_start()
        self.ro()
        self.instr_cfg = cfg_path + "bootinstr.txt"
        self.orc_handle = conductor.Conductor() # Initialize Audio File Tables and Csound Score/Orchestra
        #self.currentInstr = "a_granularlooper"
        self.c = None
        self.pt = None
        self.ui = None
        self.c_handle = None
        self.led_process = None
        self.sc = None
        self.start_failed = None
        self.started_at = time.time()
        self.healthy = False
        self.log = logger.NebLogger()
        # Check the config file for last instr
        if os.path.isfile(self.instr_cfg) and os.path.getsize(self.instr_cfg) > 0:
            # Get bank/instr from factory
            with open(self.instr_cfg, 'rb') as f:
                print "Reading bootinstr.txt"
                for line in f:
                    templist = line.strip().split(',')
                    if templist[0] == 'bank':
                        self.new_bank = templist[1]
                    elif templist[0] == 'instr':
                        self.new_instr = templist[1]
        else:
            self.new_bank = SAFE_BANK
            self.new_instr = SAFE_INSTR
        self.currentInstr = self.new_instr
        # Check if file exists, else reset to default instr
        factory_path = "/home/alarm/QB_Nebulae_V2/Code/instr/"
        user_path = "/home/alarm/instr/"
        pd_path = "/home/alarm/pd/"
        if self.new_bank == 'factory':
            path = factory_path + self.new_instr + '.instr'
        elif self.new_bank == 'user':
            path = user_path + self.new_instr + '.instr'
        elif self.new_bank == 'puredata':
            path = pd_path + self.new_instr + '.pd'
        elif self.new_bank == 'supercollider':
            path = scengine.PATCH_DIR + self.new_instr + '.scd'
        else:
            print "bank not recocgnized."
            print self.new_bank
            path = 'factory'
        if os.path.isfile(path) == False:
            # set to default instr
            self.new_bank = SAFE_BANK
            self.new_instr = SAFE_INSTR
        if guard_fallback:
            self.note("boot guard: %d starts in a row without an instrument running %d s (last: %s/%s); loading %s"
                      % (bootguard.LIMIT, bootguard.HEALTHY_S, self.new_bank, self.new_instr, SAFE_INSTR))
            self.new_bank = SAFE_BANK
            self.new_instr = SAFE_INSTR
        self.first_run = True
        self.last_debug_print = time.time()

    # uf2 -------------------------------------------------------------------------------------------------------
    def rw(self):
        if neb_globals.remount_fs is True:
            os.system("sh /home/alarm/QB_Nebulae_V2/Code/scripts/mountfs.sh rw")

    def ro(self):
        if neb_globals.remount_fs is True:
            os.system("sh /home/alarm/QB_Nebulae_V2/Code/scripts/mountfs.sh ro")

    def note(self, msg, report=None):
        """Print, and add a line to the stick's neb_log.txt (plus `report` as neb_error.txt, if given)."""
        print "uf2: " + msg
        try:
            self.log.mount_usb()
            if os.path.isdir("/mnt/memory") and self.log.usb_status:
                with open("/mnt/memory/neb_log.txt", "a") as f:
                    f.write("uf2: " + msg + "\n")
                if report is not None:
                    with open("/mnt/memory/neb_error.txt", "w") as f:
                        f.write(msg + "\n" + report)
            self.log.unmount_usb()
        except Exception:
            pass

    def instr_started(self):
        self.started_at = time.time()
        self.healthy = False

    def check_healthy(self):
        # an instrument that has run HEALTHY_S seconds clears the boot guard
        if not self.healthy and time.time() - self.started_at >= bootguard.HEALTHY_S:
            self.healthy = True
            self.rw()
            bootguard.mark_healthy()
            self.ro()

    def fall_back(self, reason, report=None):
        """Load the safe instrument next. False (stop, as stock) if the safe instrument itself failed."""
        failed = "%s/%s" % (self.new_bank, self.currentInstr)
        if self.new_bank == SAFE_BANK and self.currentInstr == SAFE_INSTR:
            self.note("%s failed (%s); it is the safe instrument, stopping" % (failed, reason), report)
            return False
        self.note("%s failed (%s); loading %s" % (failed, reason, SAFE_INSTR), report)
        self.new_bank = SAFE_BANK
        self.new_instr = SAFE_INSTR
        self.writeBootInstr()
        return True
    # -----------------------------------------------------------------------------------------------------------

    def start(self, instr, instr_bank):
        print "Nebulae Starting"
        if self.currentInstr != self.new_instr:
            reset_settings_flag = True
        else:
            reset_settings_flag = False
        self.currentInstr = instr
        self.start_failed = None
        if self.c is None:
            self.c = ctcsound.Csound()
        self.log.spill_basic_info()
        floader = fileloader.FileLoader()
        floader.reload()
        self.orc_handle.generate_orc(instr, instr_bank)
        configData = self.orc_handle.getConfigDict()
        self.c.setOption("-iadc:hw:0,0")
        self.c.setOption("-odac:hw:0,0")  # Set option for Csound
        if configData.has_key("-B"):
            self.c.setOption("-B"+str(configData.get("-B")[0]))
        else:
            self.c.setOption("-B512") # Liberal Buffer

        if configData.has_key("-b"):
            self.c.setOption("-b"+str(configData.get("-b")[0]))
        self.c.setOption("--realtime")
        self.c.setOption("-+rtaudio=alsa") # Set option for Csound
        if debug is True:
            self.c.setOption("-m7")
        else:
            self.c.setOption("-m0")  # Set option for Csound
            self.c.setOption("-d")
        # uf2: stock ignored a failed compile and ran on silently (or crashed)
        if self.c.compileOrc(self.orc_handle.curOrc) != 0:     # Compile Orchestra from String
            self.start_failed = "the Csound orchestra did not compile"
            return
        self.c.readScore(self.orc_handle.curSco)     # Read in Score generated from notes
        self.c.start() # Start Csound
        self.c_handle = ch.ControlHandler(self.c, self.orc_handle.numFiles(), configData, self.new_instr, bank=self.new_bank, initial_startup=initial_startup) # Create handler for all csound comm.
        self.loadUI()
        self.pt = ctcsound.CsoundPerformanceThread(self.c.csound()) # Create CsoundPerformanceThread
        self.c_handle.setCsoundPerformanceThread(self.pt)
        self.pt.play() # Begin Performing the Score in the perforamnce thread
        self.c_handle.updateAll() # Update all values to ensure their at their initial state.
        if reset_settings_flag == True:
            print("Changing Instr File -- Resetting Secondary Settings")
            self.c_handle.restoreAltToDefault()
        self.instr_started()

    def run(self):
        new_instr = None
        request = False
        if self.start_failed is not None:
            self.c.cleanup()
            self.c.reset()
            return self.fall_back(self.start_failed)
        if self.first_run == False:
            self.c_handle.restoreAltToDefault()
        while (self.pt.status() == 0): # Run a loop to poll for messages, and handle the UI.
            self.ui.update()
            self.c_handle.updateAll()
            self.check_healthy()
            if debug_controls == True:
                if time.time() - self.last_debug_print > 0.25:
                    self.last_debug_print = time.time()
                    self.c_handle.printAllControls()
            request = self.ui.getReloadRequest()
            if request == True:
                self.cleanup()
        if request == True:
            self.first_run = False
            print "Received Reload Request from UI"
            print "index of new instr is: " + str(self.c_handle.instr_sel_idx)
            self.new_instr = self.ui.getNewInstr()
            print "new instr: " + self.new_instr
            self.new_bank = self.c_handle.getInstrSelBank()
            print "new bank: " + self.new_bank
            self.c.cleanup()
            self.ui.reload_flag = False # Clear Reload Flag
            print "Reloading " + self.new_instr + " from " + self.new_bank
            # Store bank/instr to config
            self.writeBootInstr()
            # uf1: return to the main loop, which starts the next instrument (stock recursed here)
            if self.new_bank not in ("puredata", "supercollider"):
                self.c.reset()
            return True
        else:
            print "Run Loop Ending."
            self.cleanup()
            # uf2: Csound stopped by itself (an error at performance time). Stock then exited and the module went
            # silent until a power cycle.
            self.c.cleanup()
            self.c.reset()
            return self.fall_back("Csound stopped")

    def cleanup(self):
        print "Cleaning Up"
        self.pt.stop()
        self.pt.join()

    def writeBootInstr(self):
        try:
            if neb_globals.remount_fs is True:
                os.system("sh /home/alarm/QB_Nebulae_V2/Code/scripts/mountfs.sh rw")
            with open(self.instr_cfg, 'w') as f:
                bankstr = 'bank,'+self.new_bank
                instrstr = 'instr,'+self.new_instr
                f.write(bankstr + '\n')
                f.write(instrstr + '\n')
                for line in f:
                    templist = line.strip().split(',')
                    if templist[0] == 'bank':
                        self.new_bank = templist[1]
                    elif templist[0] == 'instr':
                        self.new_instr = templist[1]
            if neb_globals.remount_fs is True:
                os.system("sh /home/alarm/QB_Nebulae_V2/Code/scripts/mountfs.sh ro")
        except:
            "Could not write config file."

    def start_puredata(self, patch):
        self.log.spill_basic_info()
        if self.c is not None:
            self.c.cleanup()
            self.c = None
        self.c_handle = None
        self.currentInstr = patch
        self.newInstr = patch
        floader = fileloader.FileLoader()
        floader.reload()
        self.orc_handle.refreshFileHandler()
        fullPath = "/home/alarm/pd/" + patch + ".pd"
        #cmd = "pd -rt -nogui -verbose -audiobuf 5".split()
        if debug == False:
            cmd = "pd -rt -callback -nogui -audiobuf 5".split()
        else:
            cmd = "pd -rt -callback -nogui -verbose -audiobuf 5".split()
        cmd.append(fullPath)
        self.pt = Popen(cmd)
        print 'sleeping'
        time.sleep(2)
        self.c_handle = ch.ControlHandler(None, self.orc_handle.numFiles(), None, self.new_instr, bank="puredata", initial_startup=initial_startup)
        # uf1: every Pd patch starts with the alt layer at its defaults (input gain included), as Csound instruments
        # do on a change. Pd mode never saves alt values, so the stored ones were left over from a Csound instrument.
        print("Pd patch load -- Resetting Secondary Settings")
        self.c_handle.restoreAltToDefault()
        self.c_handle.setCsoundPerformanceThread(None)
        self.c_handle.enterPureDataMode()
        self.loadUI()
        self.instr_started()


    def run_puredata(self):
        new_instr = None
        request = False
        died = False
        self.c_handle.enterPureDataMode()
        while(request != True):
            self.c_handle.updateAll()
            if debug_controls == True:
                self.c_handle.printAllControls()
            self.ui.update()
            request = self.ui.getReloadRequest()
            # uf2: Pd gone (crashed, or the patch failed to load): stock stayed silent with the controls running
            if not request and self.pt.poll() is not None:
                died = True
                break
            self.check_healthy()
        if request == True:
            print "Received Reload Request from UI"
            print "index of new instr is: " + str(self.c_handle.instr_sel_idx)
            self.new_instr = self.ui.getNewInstr()
            self.new_bank = self.c_handle.getInstrSelBank()
            self.ui.reload_flag = False # Clear Reload Flag
            print "Reloading " + self.new_instr + " from " + self.new_bank
            self.cleanup_puredata()
            # Store bank/instr to config
            self.writeBootInstr()
            # uf1: return to the main loop, which starts the next instrument (stock recursed here)
            return True
        else:
            print "Run Loop Ending."
            self.cleanup_puredata()
            return self.fall_back("Pd exited with code %s" % self.pt.poll())

    def cleanup_puredata(self):
        # uf1: wait (up to 2 s) for Pd to exit, so the next engine finds the audio device free
        self.pt.terminate()
        deadline = time.time() + 2.0
        while self.pt.poll() is None and time.time() < deadline:
            time.sleep(0.02)
        if self.pt.poll() is None:
            self.pt.kill()
            self.pt.wait()

    # uf2: SuperCollider (scengine.py). Controls go out as OSC through the Pd control mode (scsender.py).
    def start_supercollider(self, patch):
        self.log.spill_basic_info()
        if self.c is not None:
            self.c.cleanup()
            self.c = None
        self.c_handle = None
        self.currentInstr = patch
        self.newInstr = patch
        floader = fileloader.FileLoader()
        floader.reload()
        self.orc_handle.refreshFileHandler()
        self.sc = scengine.ScEngine(scengine.PATCH_DIR + patch + ".scd",
                                    int(nebopts.get("sc_period")), int(nebopts.get("sc_nperiods")))
        print "SuperCollider: " + self.sc.start()
        self.c_handle = ch.ControlHandler(None, self.orc_handle.numFiles(), None, self.new_instr, bank="supercollider", initial_startup=initial_startup)
        print("SC patch load -- Resetting Secondary Settings")
        self.c_handle.restoreAltToDefault()
        self.c_handle.setCsoundPerformanceThread(None)
        self.c_handle.enterPureDataMode()
        self.loadUI()
        self.instr_started()

    def run_supercollider(self):
        request = False
        state = self.sc.poll()
        self.c_handle.enterPureDataMode()
        while request != True and state != "failed":
            self.c_handle.updateAll()
            if debug_controls == True:
                self.c_handle.printAllControls()
            self.ui.update()
            request = self.ui.getReloadRequest()
            state = self.sc.poll()
            if state == "ready":
                self.check_healthy()
        if request == True:
            print "Received Reload Request from UI"
            self.new_instr = self.ui.getNewInstr()
            self.new_bank = self.c_handle.getInstrSelBank()
            self.ui.reload_flag = False # Clear Reload Flag
            print "Reloading " + self.new_instr + " from " + self.new_bank
            self.sc.stop()
            self.writeBootInstr()
            return True
        self.sc.stop()
        return self.fall_back(self.sc.reason, self.sc.report())

    def loadUI(self):
        print "Killing LED program"
        cmd = "sudo pkill -1 -f /home/alarm/QB_Nebulae_V2/Code/nebulae/bootleds.py"
        os.system(cmd)
        if self.ui is None:
            self.ui = ui.UserInterface(self.c_handle) # Create User Interface
        else:
            self.ui.controlhandler = self.c_handle
            self.ui.clearAllLEDs()
        self.c_handle.setInstrSelBank(self.new_bank)
        self.ui.setCurrentInstr(self.new_instr)

    def launch_bootled(self):
        cmd = "sudo pkill -1 -f /home/alarm/QB_Nebulae_V2/Code/nebulae/bootleds.py"
        os.system(cmd)
        print "Launching LED program"
        fullCmd = "python2 /home/alarm/QB_Nebulae_V2/Code/nebulae/bootleds.py loading"
        self.led_process = Popen(fullCmd, shell=True)
        print 'led process created: ' + str(self.led_process)


### NEBULAE ###
app = Nebulae()

# uf1: one flat loop; run()/run_puredata()/run_supercollider() return True when another instrument is to be loaded
while True:
    if app.new_bank == "puredata":
        app.start_puredata(app.new_instr)
        initial_startup = False
        switching = app.run_puredata()
    elif app.new_bank == "supercollider":
        app.start_supercollider(app.new_instr)
        initial_startup = False
        switching = app.run_supercollider()
    else:
        app.start(app.new_instr, app.new_bank)
        initial_startup = False
        switching = app.run()
    if not switching:
        break
print "Goodbye!"
sys.exit()
