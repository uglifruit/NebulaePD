import RPi.GPIO as GPIO
import encoder as libEnc
import shiftregister as libSR
import leddriver as libDriver
import switch as libSwitch
import filehandler
import instrpager
import nebopts
import threading
import time
import random

sr_pin_next = 7
sr_pin_source_gate = 6
sr_pin_source = 5
sr_pin_freeze = 4
sr_pin_record = 3
sr_pin_reset = 0

        
class UserInterface(object):
    def __init__(self, controlhandler):
        self.controlhandler = controlhandler
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        self.currentInstr = None
        self.ledState = 1
        self.ledDriver = libDriver.LedDriver()
        self.pitch_click = libSwitch.Switch(22) # Pitch Encoder Click GPIO
        self.speed_click = libSwitch.Switch(26) # Speed Encoder Click GPIO
        # Set up Rotary Encoders
        self.encoder_pitch = libEnc.Encoder.Worker(17, 27)
        self.encoder_pitch.start() # Start Interrupt in a separate thread.
        self.encoder_speed = libEnc.Encoder.Worker(6, 13)
        self.encoder_speed.start() # Start Interrupt in a separate thread.
        self.pitch_delay = 0
        self.speed_delay = 0
        self.pitch_inc_dir = 0
        self.speed_inc_dir = 0
        self.encoder_delay_time = 500
        self.now = int(round(time.time() * 1000))
        self.pitch_blink_anim_flag = False
        self.pitch_blink_timer = self.now
        # Below are just the Blue on all RGB LEDs
        # Deltas for Encoders
        self.delta_p = 0
        self.delta_s = 0
        # Real Control Values (later share this with ControlHandler class
        self.speed_amount = self.controlhandler.getStaticVal("speed")
        self.alt_speed_amount = 23 # input level
        self.pitch_amount = self.controlhandler.getStaticVal("pitch")
        self.mode = "normal"

        self.pager = instrpager.InstrPager() # uf1 paged selector
        self.page_steps = int(nebopts.get("sel_page_steps")) # Pitch encoder steps per page
        self.page_counter = 0
        self.prev_mode = None
        self.refreshFileHandlers()
        cur_bank = self.controlhandler.getInstrSelBank()
        self.bank_shift_counter = 0
        cnt = self.handleForBank(cur_bank).numFiles()
        self.controlhandler.setInstrSelNumFiles(cnt)
        self.reload_flag = False # Flag to reload the whole program. 
        self.alt_file_bright = 0.0
        self.alt_file_cnt = 0.0
        self.blink_counter = 0
        self.prev_blink = False
        self.blink = False
        self.time_pressed_pitch = self.now
        self.ignore_next_pitch_click = False
        self.ignore_next_speed_click = False
        self.clearAllLEDs()
        self.restoreDefaultsFlag = False

    def update(self):
        self.now = int(round(time.time() * 1000))
        if self.reload_flag == False:
            self.ledDriver.update()
        self.pitch_click.update() 
        self.speed_click.update() 
        self.delta_p = self.encoder_pitch.get_steps()
        self.delta_s = self.encoder_speed.get_steps()
        self.mode = self.controlhandler.mode()
        if self.mode == "instr selector" and self.prev_mode != "instr selector":
            self.enterInstrSel()
        self.prev_mode = self.mode

        if self.mode == "secondary controls":
            if self.restoreDefaultsFlag == True:
                self.animateRestoration()
            elif self.controlhandler.getEditFunctionFlag("reset"):
                self.animateEditFunction("reset")
            else:
                #self.set_button_led("freeze", self.controlhandler.getAltValue("freeze_alt"))
                #self.set_button_led("source", self.controlhandler.getAltValue("source_alt"))
                #self.set_button_led("record", self.controlhandler.getAltValue("record_alt"))
                #self.set_button_led("reset", self.controlhandler.getAltValue("reset_alt"))
                self.set_button_led("freeze", self.controlhandler.getAltLEDValue("freeze_alt"))
                self.set_button_led("source", self.controlhandler.getAltLEDValue("source_alt"))
                self.set_button_led("record", self.controlhandler.getAltLEDValue("record_alt"))
                self.set_button_led("reset", self.controlhandler.getAltLEDValue("reset_alt"))
                if self.currentInstr == "a_granularlooper":
                    next_mode = self.controlhandler.getAltValue("file_alt")
                    self.setAltNextLed(next_mode)
                else:
                    self.set_button_led("next", self.controlhandler.getAltLEDValue("file_alt"))
        elif self.mode == "instr selector":
            self.handleInstrSelButtons()
            self.displayInstrSel()
        else: # Includes Normal Behavior
            #self.set_button_led("freeze", self.controlhandler.getValue("freeze"))
            #self.set_button_led("source", self.controlhandler.getValue("source"))
            #self.set_button_led("record", self.controlhandler.getValue("record"))
            #next_state = self.controlhandler.shiftReg.state(sr_pin_next)
            #next_gate_state = not GPIO.input(23)
            #if next_state == 1 or next_gate_state == 1:
            #    self.set_button_led("next", 1)
            #else:
            #    self.set_button_led("next", 0)
            self.set_button_led("freeze", self.controlhandler.getLEDValue("freeze"))
            self.set_button_led("source", self.controlhandler.getLEDValue("source"))
            self.set_button_led("record", self.controlhandler.getLEDValue("record"))
            self.set_button_led("next", self.controlhandler.getLEDValue("file"))
            if self.controlhandler.getEditFunctionFlag("reset") == True:
                self.animateEditFunction("reset")
            elif self.controlhandler.getEditFunctionFlag("record") == True:
                self.animateEditFunction("record")
            elif self.controlhandler.getEditFunctionFlag("source") == True:
                self.animateEditFunction("source")
                tempidx = self.handleForBank(self.controlhandler.currentBank).getIndex(self.controlhandler.currentInstr)
                if tempidx is not None: # uf1: the file may be gone (stock then crashed in getNewInstr)
                    self.controlhandler.setInstrSelIdx(tempidx)
                    self.controlhandler.setInstrSelBank(self.controlhandler.currentBank)
                    self.reload_flag = True
            elif self.controlhandler.writing_buffer == True:
                self.animateBufferWrite()
            elif self.controlhandler.buffer_failure == True:
                self.animateBufferFailure()
                #self.animateEditFunction("freeze")
            else:
                if self.currentInstr == "a_granularlooper":
                    if self.controlhandler.size_status_comm.getState() == 0:
                        #self.set_button_led("reset", self.controlhandler.getEndOfLoopState())
                        if self.controlhandler.eol_comm.getState() > 0:
                            self.set_button_led("reset", 1.0)
                        else:
                            self.set_button_led("reset", 0.0)
                    else:
                        self.set_button_led("reset", 1.0)
                else:
                    state = self.controlhandler.getLEDValue("reset")
                    if state == True or state == 1:
                        self.set_button_led("reset", 1.0)
                    else:
                        self.set_button_led("reset", 0.0)

        self.update_speed(self.mode)
        self.update_pitch(self.mode)
    
    def clearAllLEDs(self):
        self.set_rgb("pitch_pos", 4095, 4095, 4095, 0.0)
        self.set_rgb("pitch_neg", 4095, 4095, 4095, 0.0)
        self.set_rgb("speed_pos", 4095, 4095, 4095, 0.0)
        self.set_rgb("speed_neg", 4095, 4095, 4095, 0.0)
        self.set_button_led("reset", 0.0)
        self.set_button_led("record", 0.0)
        self.set_button_led("freeze", 0.0)
        self.set_button_led("source", 0.0)
        self.set_button_led("next", 0.0)

    # uf1 paged selector ---------------------------------------------------------------------------------------
    def refreshFileHandlers(self):
        # Rebuilt each time the selector opens, so files added to or removed from the stick show up (stock built
        # these once at power-on). Pd files starting with "_" are helper abstractions and are not listed.
        user_dir = "/home/alarm/instr/"
        factory_dir = "/home/alarm/QB_Nebulae_V2/Code/instr/"
        pd_dir = "/home/alarm/pd/"
        sc_dir = "/home/alarm/sc/"
        self.factoryinstr_fhandle = filehandler.FileHandler(factory_dir, [".instr"])
        self.userinstr_fhandle = filehandler.FileHandler(user_dir, [".instr"])
        self.puredata_fhandle = filehandler.FileHandler(pd_dir, [".pd"], hide_prefix="_")
        # uf2: SuperCollider patches; "_" files are helpers a patch can load, not listed
        self.supercollider_fhandle = filehandler.FileHandler(sc_dir, [".scd"], hide_prefix="_")

    def handleForBank(self, bank):
        if bank == "user":
            return self.userinstr_fhandle
        elif bank == "puredata":
            return self.puredata_fhandle
        elif bank == "supercollider":
            return self.supercollider_fhandle
        return self.factoryinstr_fhandle

    def enterInstrSel(self):
        self.refreshFileHandlers()
        self.controlhandler.popInstrSelSlot() # drop a press left over from before the selector opened
        self.selectBank(self.controlhandler.getInstrSelBank())

    def selectBank(self, bank):
        # Show `bank` on the page of the running instrument if it lives there, else on page 1.
        f_handle = self.handleForBank(bank)
        self.controlhandler.setInstrSelBank(bank)
        self.controlhandler.setInstrSelNumFiles(f_handle.numFiles())
        self.pager.setCount(f_handle.numFiles())
        self.pager.showIndex(self.currentIndexInBank(bank))
        self.page_counter = 0

    def currentIndexInBank(self, bank):
        if bank != self.controlhandler.currentBank:
            return None
        return self.handleForBank(bank).getIndex(self.currentInstr)

    def handleInstrSelButtons(self):
        # uf1: a button loads the instrument in its slot of the page at once; an empty slot does nothing
        slot = self.controlhandler.popInstrSelSlot()
        if slot is None:
            return
        idx = self.pager.slotIndex(slot)
        if idx is None:
            return
        self.controlhandler.setInstrSelIdx(idx)
        self.controlhandler.setInstrSelOffset(self.pager.offset())
        if self.getNewInstr() is not None:
            print "Button " + str(slot + 1) + " pressed in Instr Sel: loading"
            self.reload_flag = True

    def leaveInstrSel(self):
        # back to the running instrument without loading anything (Pitch or Speed click). uf2: by its bank (Pd and
        # SuperCollider both use the Pd control mode); stock looked the name up among the Pd files.
        if self.controlhandler.currentBank in ("puredata", "supercollider"):
            self.controlhandler.enterPureDataMode()
        else:
            self.controlhandler.enterNormalMode()

    def displayInstrSel(self):
        values = self.pager.leds(self.currentIndexInBank(self.controlhandler.getInstrSelBank()))
        self.set_button_led("record", values[0])
        self.set_button_led("next", values[1])
        self.set_button_led("source", values[2])
        self.set_button_led("reset", values[3])
        self.set_button_led("freeze", values[4])

    def animateEditFunction(self, name):
        ## TODO: The abstraction could actually do this animation for any of the four buttons (file, source, reset, freeze)
        if self.controlhandler.getEditFunctionFlag(name) == True:
            if self.blink_counter < 5:
                self.prev_blink = self.blink
                self.blink = (self.now & 100) < 50
                if self.blink == False and self.prev_blink == True:
                    self.blink_counter += 1
                if self.blink == True:
                    self.set_button_led(name, 1) 
                else:
                    self.set_button_led(name, 0)
            else:
                self.controlhandler.clearEditFunctionFlag(name)
                self.blink_counter = 0
                self.set_button_led(name, 0)
        else:
            self.prev_blink = self.blink
            self.blink = False

    def animateBufferWrite(self):
        self.prev_blink = self.blink
        self.blink = (self.now & 500) < 250
        if self.blink == True:
            self.set_button_led("freeze", 1) 
            self.set_button_led("record", 1) 
        else:
            self.set_button_led("freeze", 0) 
            self.set_button_led("record", 0) 

    def animateBufferFailure(self):
        self.prev_blink = self.blink
        if (self.controlhandler.buffer_failure == True):
            if self.blink_counter < 10:
                self.blink = (self.now & 250) < 125
                if self.blink == True:
                    if self.prev_blink == False:
                        self.blink_counter += 1
                    self.set_button_led("record", 1) 
                    self.set_button_led("next", 1) 
                    self.set_button_led("source", 1) 
                    self.set_button_led("reset", 1)
                    self.set_button_led("freeze", 1) 
                else:
                    self.set_button_led("record", 0) 
                    self.set_button_led("next", 0) 
                    self.set_button_led("source", 0) 
                    self.set_button_led("reset", 0)
                    self.set_button_led("freeze", 0) 
            else:
                self.controlhandler.buffer_failure = False
                self.blink_counter = 0
                self.set_button_led("record", 0) 
                self.set_button_led("next", 0) 
                self.set_button_led("source", 0) 
                self.set_button_led("reset", 0)
                self.set_button_led("freeze", 0) 
        else:
            self.blink = False
                
    def animateRestoration(self):
        ## TODO: The abstraction could actually do this animation for any of the four buttons (file, source, reset, freeze)
        if self.blink_counter < 4:
            self.prev_blink = self.blink
            self.blink = (self.now & 100) < 50
            if self.blink == False and self.prev_blink == True:
                self.blink_counter += 1
            for name in ["reset", "record", "next", "source", "freeze"]:
                if self.blink == True:
                    self.set_button_led(name, 1) 
                else:
                    self.set_button_led(name, 0)
        else:
            #self.controlhandler.clearEditFunctionFlag(name)
            self.restoreDefaultsFlag = False
            self.blink_counter = 0
            for name in ["reset", "record", "file", "source", "freeze"]:
                self.set_button_led(name, 0)

    def pressed_pitch(self):
        return self.pitch_click.state()

    def pressed_speed(self):
        return self.speed_click.state()
        

    def clicked_pitch(self):
        if self.pitch_click.fallingEdge():
            if self.ignore_next_pitch_click == False:
                return 1
            else:
                self.ignore_next_pitch_click = False
                return 0
        else:
            return 0

    def clicked_speed(self):
        if self.speed_click.fallingEdge():
            if self.ignore_next_speed_click == False:
                return 1
            else:
                self.ignore_next_speed_click = False
                return 0
        else:
            return 0

    def get_delta(self, name):
        if name == "speed":
            return self.delta_s
        elif name == "pitch":
            return self.delta_p
        else:
            return None

    def set_speed_amount(self):
        self.speed_amount = self.controlhandler.getStaticVal("speed")
        inc = self.get_delta("speed")
        if self.speed_click.state() == True:
            inc = 0
        if self.speed_delay == -1:
            if inc > 0:
                if self.speed_inc_dir == 1:
                    self.speed_amount += 0.001 * inc * inc * inc
                    self.speed_inc_dir = 1
                else:
                    self.speed_inc_dir = 1
            elif inc < 0:
                if self.speed_inc_dir == -1:
                    self.speed_amount -= 0.001 * (-1 * inc) * (-1 * inc) * (-1 * inc)
                    self.speed_inc_dir = -1
                else:
                    self.speed_inc_dir = -1
        else:
            if self.now > self.speed_delay:
                self.speed_delay = -1
        if self.speed_amount > 1.0:
            self.speed_amount = 1.0
        elif self.speed_amount < 0.0:
            self.speed_amount = 0.0
        if self.clicked_speed() == 1:
            self.speed_delay = self.now + self.encoder_delay_time
            if (self.speed_amount > 0.62 and self.speed_amount < 0.63):
                self.speed_amount = .375
            else:
                self.speed_amount = .625
        self.controlhandler.setValue("speed", self.speed_amount)

    def set_alt_speed_amount(self):
        self.alt_speed_amount = self.controlhandler.getAltValue("speed_alt")
        inc = self.get_delta("speed")
        if inc > 0:
            self.alt_speed_amount += 1
        elif inc < 0:
            self.alt_speed_amount -= 1
        if self.alt_speed_amount > 32:
            self.alt_speed_amount = 32
        elif self.alt_speed_amount < 0:
            #self.alt_speed_amount = 0.0
            self.alt_speed_amount = 0
        if self.clicked_speed() == 1:
            #self.alt_speed_amount = 0.710 # 23/32 = 0dB input gain
            self.alt_speed_amount = 23
        self.controlhandler.setAltValue("speed_alt", self.alt_speed_amount)
    
    # Returns duple of neg_brightness, pos_brightness
    def set_speed_leds(self, mode):
        if mode == "normal" or mode == "puredata":
            pink = libDriver.Color(3037, 200, 3825)
            white = libDriver.Color(4095,4095,4095)
            red = libDriver.Color(4095, 0, 0) #octave 0 / record
            orange = libDriver.Color(4095, 1100, 0) #octave 1 (1V)
            yellow = libDriver.Color(4095, 3395, 0) #octave 2 (2V)
            blue = libDriver.Color(0,0,4095) #octave 3 (3V original pitch)
            green = libDriver.Color(0, 4095, 0) # octave 4 (4V)
            purple = libDriver.Color(511, 0, 4095) # octave 5 (5V)
            colororder = [ white, orange, yellow, blue, green, purple]
            speed_amt = self.controlhandler.channeldict["speed"].curVal
            translated_speed = speed_amt * 8.0 - 4.0
            factors = [0.125, 0.25, 0.5, 1.0, 2.0, 4.0]
            color_pos = white
            color_neg = white
            #speed_pos_bright = (speed_amt - 0.5) * 2.0
            #speed_neg_bright = ((1.0 - speed_amt) - 0.5) * 2.0
            if translated_speed > 0:
                speed_pos_bright = 1.0
                speed_neg_bright = 0.0
            else:
                speed_pos_bright = 0.0
                speed_neg_bright = 1.0
            speed_pos_bright *= 0.33
            speed_neg_bright *= 0.33
            blink = (self.now & 150) > 75
            highest_factor = 0
            abs_speed = abs(translated_speed)
            if abs_speed < factors[0]:
                highest_factor = 0
            elif abs_speed < factors[1]:
                highest_factor = 1
            elif abs_speed < factors[2]:
                highest_factor = 2
            elif abs_speed < factors[3]:
                highest_factor = 3
            elif abs_speed < factors[4]:
                highest_factor = 4
            elif abs_speed < factors[5]:
                highest_factor = 5

            if highest_factor < 1: 
                scalar = (abs_speed / factors[0])
                newcolor = colororder[0]
                color_pos = newcolor
                color_neg = newcolor
                if translated_speed < 0:
                    speed_neg_bright = scalar * 0.33
                else:
                    speed_pos_bright = scalar * 0.33
            else:
                scalarRange = factors[highest_factor] / 2.0
                scalar = (abs_speed - factors[highest_factor - 1]) / scalarRange
                newcolor = self.blendColor(colororder[highest_factor-1], colororder[highest_factor], scalar)
                color_pos = newcolor
                color_neg = newcolor
            for idx, factor in enumerate(factors): 
                if (abs(translated_speed) > factor - 0.0075) and abs(translated_speed) < factor + 0.0075:  
                    if translated_speed > 0:
                        color_pos = colororder[idx]
                        speed_pos_bright = 1.0
                    else:
                        color_neg = colororder[idx]
                        speed_neg_bright = 1.0
            if translated_speed == 0:
                speed_pos_bright = 0
                speed_neg_bright = 0
            if speed_pos_bright < 0:
                speed_pos_bright = 0
            if speed_neg_bright < 0:
                speed_neg_bright = 0
            if self.currentInstr == "a_granularlooper":
                if self.controlhandler.channeldict["record"].curVal == 1:
                    color_neg = red
                    color_pos = red
                    speed_neg_bright = 1.0
                    speed_pos_bright = 1.0
            self.set_rgb("speed_neg", color_neg.red(), color_neg.green(),color_neg.blue(), speed_neg_bright)
            self.set_rgb("speed_pos", color_pos.red(), color_pos.green(),color_pos.blue(), speed_pos_bright)
        elif mode == "secondary controls":
            speed_ticks  = self.controlhandler.getAltValue("speed_alt")
            speed_amt = speed_ticks / 32.0
            speed_pos_bright = (speed_amt - 0.5) * 2.0
            speed_neg_bright = ((1.0 - speed_amt) - 0.5) * 2.0
            if speed_pos_bright < 0:
                speed_pos_bright = 0
            if speed_neg_bright < 0:
                speed_neg_bright = 0
            if speed_ticks == 23:
                tempc = libDriver.Color(0, 4095, 0)
            else:
                tempc = libDriver.Color(3037, 200, 3825)
            self.set_rgb("speed_neg", tempc.red(), tempc.green(), tempc.blue(), speed_neg_bright) 
            self.set_rgb("speed_pos", tempc.red(), tempc.green(), tempc.blue(), speed_pos_bright)
        elif mode == "instr selector":
            tempc = libDriver.Color(0, 4095, 0)
            if self.controlhandler.getInstrSelBank() == "factory":
                self.set_rgb("speed_neg", tempc.red(), tempc.green(), tempc.blue(), 1.0)
                self.set_rgb("speed_pos", tempc.red(), tempc.green(), tempc.blue(), 1.0)
            elif self.controlhandler.getInstrSelBank() == "user":
                self.set_rgb("speed_neg", tempc.red(), tempc.green(), tempc.blue(), 1.0)
                self.set_rgb("speed_pos", tempc.red(), tempc.green(), tempc.blue(), 0.0)
            elif self.controlhandler.getInstrSelBank() == "puredata":
                self.set_rgb("speed_neg", tempc.red(), tempc.green(), tempc.blue(), 0.0)
                self.set_rgb("speed_pos", tempc.red(), tempc.green(), tempc.blue(), 1.0)
            elif self.controlhandler.getInstrSelBank() == "supercollider":
                # uf2: one step past Pd, the right light in blue
                blue = libDriver.Color(0, 0, 4095)
                self.set_rgb("speed_neg", blue.red(), blue.green(), blue.blue(), 0.0)
                self.set_rgb("speed_pos", blue.red(), blue.green(), blue.blue(), 1.0)
        else:
            pass
    
    def update_speed(self, mode):
        if mode == "normal" or mode == "puredata":
            if self.speed_click.risingEdge() == True:
                self.time_pressed_speed = self.now
            if self.speed_click.state() == True and self.now - self.time_pressed_speed > 1500:
                self.ignore_next_speed_click = True
                self.controlhandler.enterInstrSelMode()
            self.set_speed_amount()
        elif mode == "puredata":
            if self.speed_click.risingEdge() == True:
                self.time_pressed_speed = self.now
            if self.speed_click.state() == True and self.now - self.time_pressed_speed > 1500:
                self.ignore_next_speed_click = True
                self.controlhandler.enterInstrSelMode()
            self.set_speed_amount()
        elif mode == "secondary controls":
            self.set_alt_speed_amount()
        elif mode == "instr selector":
            # Set Bank
            cur_bank = self.controlhandler.getInstrSelBank()
            inc = self.get_delta("speed")
            thresh = 8
            self.bank_shift_counter += inc
            if self.bank_shift_counter > thresh:
                self.bank_shift_counter = thresh
            elif self.bank_shift_counter < -1 * thresh:
                self.bank_shift_counter = -1 * thresh

            #print "bank shift counter: " + str(self.bank_shift_counter)
                

            if cur_bank == "user" and self.bank_shift_counter >= thresh:
                self.bank_shift_counter = 0
                self.selectBank("factory")
            elif cur_bank == "puredata" and self.bank_shift_counter <= -1 * thresh:
                self.bank_shift_counter = 0
                self.selectBank("factory")
            elif cur_bank == "puredata" and self.bank_shift_counter >= thresh:
                self.bank_shift_counter = 0
                self.selectBank("supercollider")
            elif cur_bank == "supercollider" and self.bank_shift_counter <= -1 * thresh:
                self.bank_shift_counter = 0
                self.selectBank("puredata")
            elif cur_bank == "factory":
                if self.bank_shift_counter >= thresh:
                    self.bank_shift_counter = 0
                    self.selectBank("puredata")
                elif self.bank_shift_counter <=  -1 * thresh:
                    self.bank_shift_counter = 0
                    self.selectBank("user")

            if self.clicked_speed() == 1:
                print "Clicked Speed from Instr Sel: leaving without loading"
                self.leaveInstrSel()
        else:
            pass
        self.set_speed_leds(mode)

    def set_pitch_amount(self):
        self.pitch_amount = self.controlhandler.getStaticVal("pitch")
        inc = self.get_delta("pitch")
        inc_size = 0.001
        if self.pitch_click.state() == True:
            #inc = 0
            inc_size = 0.2
        if self.pitch_delay == -1:
            if inc > 0:
                if self.pitch_inc_dir == 1:
                    if inc_size == 0.2:
                        self.ignore_next_pitch_click = True
                        self.pitch_delay = self.now + 125
                    self.pitch_amount += inc_size * inc * inc * inc
                    self.pitch_inc_dir = 1
                else:
                    self.pitch_inc_dir = 1
            elif inc < 0:
                if self.pitch_inc_dir == -1:
                    if inc_size == 0.2:
                        self.ignore_next_pitch_click = True
                        self.pitch_delay = self.now + 125
                    self.pitch_amount -= inc_size * (-1 * inc) * (-1 * inc) * (-1 * inc)
                    self.pitch_inc_dir = -1
                else:
                    self.pitch_inc_dir = -1
        else:
            if self.now > self.pitch_delay:
                self.pitch_delay = -1
        if self.pitch_amount > 1.0:
            self.pitch_amount = 1.0
        elif self.pitch_amount < 0:
            self.pitch_amount = 0.0
        if self.clicked_pitch() == 1:
            self.pitch_delay = self.now + self.encoder_delay_time
            self.pitch_amount = 0.60
        self.controlhandler.setValue("pitch", self.pitch_amount)

    def set_alt_pitch_amount(self):
        self.alt_pitch_amount = self.controlhandler.getAltStaticVal("pitch_alt")
        inc = self.get_delta("pitch")
        if inc > 0:
            self.alt_pitch_amount += 0.002 * inc
        elif inc < 0:
            self.alt_pitch_amount -= 0.002 * (-1 * inc)
        if self.pitch_click.state() == True:
            inc = 0
        if self.pitch_delay == -1:
            if inc > 0:
                if self.pitch_inc_dir == 1:
                    self.alt_pitch_amount += 0.001 * inc * inc * inc
                    self.pitch_inc_dir = 1
                else:
                    self.pitch_inc_dir = 1
            elif inc < 0:
                if self.pitch_inc_dir == -1:
                    self.alt_pitch_amount -= 0.001 * (-1 * inc) * (-1 * inc) * (-1 * inc)
                    self.pitch_inc_dir = -1
                else:
                    self.pitch_inc_dir = -1
        else:
            if self.now > self.pitch_delay:
                self.pitch_delay = -1
        if self.alt_pitch_amount > 1.0:
            self.pitch_blink_anim_flag = True
            self.pitch_blink_timer = self.now
            self.alt_pitch_amount = 1.0
        elif self.alt_pitch_amount < 0:
            self.pitch_blink_anim_flag = True
            self.pitch_blink_timer = self.now
            self.alt_pitch_amount = 0.0
        self.controlhandler.setAltValue("pitch_alt", self.alt_pitch_amount)

    def set_pitch_leds(self, mode):
        # Pitch input 0-1.0 neg | 1.0-4.0 pos
        pink = libDriver.Color(3037, 200, 3825)
        white = libDriver.Color(4095,4095,4095)
        red = libDriver.Color(4095, 0, 0) #octave 0 / record
        orange = libDriver.Color(4095, 1100, 0) #octave 1 (1V)
        yellow = libDriver.Color(4095, 3395, 0) #octave 2 (2V)
        blue = libDriver.Color(0,0,4095) #octave 3 (3V original pitch)
        green = libDriver.Color(0, 4095, 0) # octave 4 (4V)
        purple = libDriver.Color(511, 0, 4095) # octave 5 (5V)
        colororder = [ white, orange, yellow, blue, green, purple]
        octaves = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        if mode == "normal" or mode == "puredata":
            original_pitch = 0.6
            tolerance = 0.001
            pitch_amt = round(self.controlhandler.getValue("pitch"), 4) # I don't like that I have to do this
            sector_total = pitch_amt / 0.2
            sector_int = int(sector_total)
            sector_brightness = sector_total - sector_int
            if pitch_amt > original_pitch + tolerance:
                # handle blending up ward
                if pitch_amt > octaves[5]:
                    scalar = (pitch_amt - octaves[5]) * 5.00   
                    pos_color = self.blendColor(colororder[5], colororder[0], scalar)
                elif pitch_amt > octaves[4]:
                    ## Blend green to purple
                    scalar = (pitch_amt - octaves[4]) * 5.00
                    pos_color = self.blendColor(colororder[4], colororder[5], scalar)
                else:
                    scalar = (pitch_amt - octaves[3]) * 5.00
                    pos_color = self.blendColor(colororder[3], colororder[4], scalar)
                neg_color = white
                #pitch_pos_bright = sector_brightness * 0.33
                pitch_pos_bright = 0.33
                pitch_neg_bright = 0.0
            elif pitch_amt < original_pitch - tolerance:
                if pitch_amt < octaves[1]:
                    scalar = (pitch_amt - octaves[0]) * 5.0
                    neg_color = self.blendColor(colororder[0], colororder[1], scalar)
                elif pitch_amt < octaves[2]:
                    scalar = (pitch_amt - octaves[1]) * 5.0
                    neg_color = self.blendColor(colororder[1], colororder[2], scalar)
                elif pitch_amt < octaves[3]:
                    scalar = (pitch_amt - octaves[2]) * 5.0
                    neg_color = self.blendColor(colororder[2], colororder[3], scalar)
                pos_color = white
                pitch_pos_bright = 0.0
                pitch_neg_bright = 0.33
            octaves = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
            for idx, octave in enumerate(octaves):
                if pitch_amt >= octave - tolerance and pitch_amt <= octave + tolerance:
                    if octave < 0.6:
                        pitch_neg_bright = 1.0
                        neg_color = colororder[idx]
                    elif octave > 0.6:
                        pitch_pos_bright = 1.0
                        pos_color = colororder[idx]
                    else:
                        pitch_pos_bright = 1.0
                        pitch_neg_bright = 1.0
                        pos_color = colororder[idx]
                        neg_color = colororder[idx]
            self.set_rgb("pitch_neg", neg_color.red(), neg_color.green(),neg_color.blue(), pitch_neg_bright)
            self.set_rgb("pitch_pos", pos_color.red(), pos_color.green(),pos_color.blue(), pitch_pos_bright)
        elif mode == "secondary controls":
            tempc = purple
            amt = round(self.controlhandler.getAltValue("pitch_alt"), 3)

            pos_bright = (amt - 0.5) * 2.0
            neg_bright = ((1.0 - amt) - 0.5) * 2.0
            if pos_bright < 0.0:
                pos_bright = 0.0
            elif pos_bright > 1.0:
                pos_bright = 1.0
            if neg_bright < 0.0:
                neg_bright = 0.0
            elif neg_bright > 1.0:
                neg_bright = 1.0
            blink = (self.now & 150) > 75
            if amt < 0.001 and self.pitch_blink_anim_flag == True:
                if blink == True:
                    neg_bright = 1.0 
                else:
                    neg_bright = 0.0
                    if self.now - self.pitch_blink_timer > 450:
                        self.pitch_blink_anim_flag = False
            if amt > 0.99 and self.pitch_blink_anim_flag == True:
                if blink == True:
                    pos_bright = 1.0 
                else:
                    pos_bright = 0.0
                    if self.now - self.pitch_blink_timer > 450:
                        self.pitch_blink_anim_flag = False
            self.set_rgb("pitch_neg", tempc.red(), tempc.green(), tempc.blue(), neg_bright)
            self.set_rgb("pitch_pos", tempc.red(), tempc.green(), tempc.blue(), pos_bright)
        elif mode == "instr selector":
            # uf1: page colour, in the octave order (1-5 white, 6-10 orange, 11-15 yellow, 16-20 blue, 21-25 green)
            tempc = colororder[self.pager.page % 5]
            self.set_rgb("pitch_neg", tempc.red(), tempc.green(), tempc.blue(), 1.0)
            self.set_rgb("pitch_pos", tempc.red(), tempc.green(), tempc.blue(), 1.0)
        else:
            pass
            

    def update_pitch(self, mode):
        if mode == "normal" or mode == "puredata":
            if self.pitch_click.risingEdge() == True:
                self.time_pressed_pitch = self.now
            self.set_pitch_amount()
        elif mode == "secondary controls":
            self.set_alt_pitch_amount()
            if self.pitch_click.risingEdge() == True:
                self.restoreDefaultsFlag = True
                self.controlhandler.restoreAltToDefault()
        elif mode == "instr selector":
            # uf1: Pitch turns choose the page, page_steps encoder steps per page (neb_options.txt sel_page_steps)
            self.page_counter += self.get_delta("pitch")
            while self.page_counter >= self.page_steps:
                self.page_counter -= self.page_steps
                self.pager.turn(1)
            while self.page_counter <= -self.page_steps:
                self.page_counter += self.page_steps
                self.pager.turn(-1)
        else:
            pass
                
        if mode == "instr selector":
            if self.clicked_pitch():
                self.leaveInstrSel()
        self.set_pitch_leds(mode)

    def set_rgb(self, name, r, g, b, bright=1.0):
        self.ledDriver.set_rgb(name, r, g, b, bright)       

    def set_button_led(self, name, bright):
        self.ledDriver.set_button_led(name, bright)

    def cleanup(self):
        self.encoder_pitch.stop()
        self.encoder_speed.stop()
        self.ledDriver.cleanup()
        GPIO.cleanup()

    def getReloadRequest(self):
        return self.reload_flag

    def setAltNextLed(self, mode):
        fade_inc = 0.009
        if mode == 0:
            self.alt_file_bright += fade_inc
            if self.alt_file_bright > 1.0:
                self.alt_file_bright = 0.0
        elif mode == 1:
            self.alt_file_bright -= fade_inc
            if self.alt_file_bright < 0.0:
                self.alt_file_bright = 1.0
        elif mode == 2:
            self.alt_file_cnt += fade_inc
            if self.alt_file_cnt > 0.2:
                self.alt_file_cnt = 0.0
                self.alt_file_bright = random.random()
        self.set_button_led("next", self.alt_file_bright)

    def getNewInstr(self):
        idx = self.controlhandler.getInstrSelIdx()
        instr = None
        f_handle = self.handleForBank(self.controlhandler.getInstrSelBank())
        if idx < f_handle.numFiles():
            instr = f_handle.getFilename(idx)
        return instr

    def setCurrentInstr(self, instr):
        self.currentInstr = instr
        self.controlhandler.setCurrentInstr(instr)
        # uf1: look in the bank it was loaded from first (stock took the first bank with a matching name), and store
        # the absolute index with its page offset (stock stored idx % 5 with offset idx / 5, so files 6+ went wrong).
        names = ["factory", "user", "puredata", "supercollider"]
        cur = self.controlhandler.getInstrSelBank()
        if cur in names:
            names.remove(cur)
            names.insert(0, cur)
        for bankname in names:
            tempidx = self.handleForBank(bankname).getIndex(instr)
            if tempidx is not None:
                self.controlhandler.setInstrSelIdx(tempidx)
                self.controlhandler.setInstrSelOffset((tempidx // instrpager.PAGE_SIZE) * instrpager.PAGE_SIZE)
                self.controlhandler.setInstrSelBank(bankname)
                break

    def blendColor(self, color_a, color_b, amount):
        newred = (color_a.red() * (1.0 - amount)) + (color_b.red() * amount)
        newgreen = (color_a.green() * (1.0 - amount)) + (color_b.green() * amount)
        newblue = (color_a.blue() * (1.0 - amount)) + (color_b.blue() * amount)
        return libDriver.Color(newred, newgreen, newblue) # defaults to white.
