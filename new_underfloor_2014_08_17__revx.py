from time import sleep
"""
=================================

Underfloor Heating Control

Shore Technologies

Adrian M.
April 2011

Last update 16 Aug 2011
REVISION HISTORY:

  12 Jun - updated valveControl to skip operation 

           if the limits are reached

         - updated control operation to full switch over
2013-06-29 and new pot and change limits valveFullclosed valveOpen
 




=================================
"""

#picaxe 28x2
##no_data
##no_table
#terminal 9600

#Eeprom preload
#eeprom 95, ("So  xx.x� Tout xx.x�Sr  xx.x� Tret xx.x�PWR xx.x% Tenv xx.x�AUTO      Thwc xx.x�")


#Hardware definitions
#================================



#Temperature sensors pins
TPinRet  = "C.0"		#retour       [T1]
TPinOut  = "A.3"		#inlet        [T2]
TPinHW   = "A.2"		#Hot Water    [T3]
TPinEnv  = "A.1"		#Environment  [T4]
pinVpos  = "a.0"		#valve position feedback from potentiometer [T5]


 #serial comms
Lcd = "C.1"
SSR = "C.2"

 #buttons
btnISet = "pinB.4"

 #limiter input
mtrLim = "pinC.5"


 #flow switch
FlowSw = "pinC.6"		#active low: activated wen false


 #flow pump
Pump = "C.7"



#Software definitions
#================================

 #LCD constants
rows  = 4
cols  = 20
line1 = "$80"
line2 = "$C0"
line3 = "$94"
line4 = "$D4"
clr   = 1
  
  #placeholders
hSo   = "$84"
hSr   = "$C4"
hPwr  = "$98"
hTout = "$8F"
hTret = "$CF"
hTenv = "$A3"
hThwc = "$E3"
hMode = "$D4"
   


#System Constants
baud = "T2400_8"
TDisp = "bit0"
isElectrical = "bit2"
isHWC = "bit3"
isSettled = "bit4"
isNight = "bit5"
false = 0
true  = 1

  
#program variables
bCount  = "b55"		#byte counter
tmp1    = "b48"		#green vars
tmp2    = "b49"
wtmp1   = "w24"
tmp3    = "b50"
tmp4    = "b51"
wtmp2   = "w25"
tmp5    = "b52"
tmp6    = "b53"
wtmp3   = "w26"
tTemp   = "w26"		#used in temperature aquisition
TempPin = "b54"		#used in temperature aquisition
  
  #control variables
TRetour = "w2"		#retour temperature
TOut    = "w3"		#inlet temperature
THW     = "w4"		#hot water temperature
TEnv    = "w5"		#Environment temperature
T5Val   = "w6"		#Reserved
BWn      = "w22"          #(23C-BWn=19C)
HWSwitchOver = 3200     #HWC threshold was 3000

  
  #PID
SOut = "w7"		#Set output temperature
SRet = "w8"		#Set return temperature
Pwr  = "w9"		#Duty cycle for pwm
Err1 = "w10"
Err2 = "w11"
Lag  = "b24"		#TRetour lag, cycles
cLag = "b25"
Gain = "w13"
kP   = 40
kI   = 25
kH   = 3
BW   = 10		#0.1� Bandwidth
 
  #Buttons
buttons = "b1"		#buttons status return
btnDn   = "bit11"
btnUp   = "bit10"
btnEsc  = "bit9"
btnSet  = "bit8"
  
  #Step Motor
mtrDir    = "bit1"	#motor direction, true negative, false positive
mtrStep   = "b28"	#number of steps
mtrIndex  = "b29"      #step index
valvePos  = "w15"	#valve position
valveGoal = "w16"	#valve goal
  
mtrOpen  = 0	      #open valve
mtrClose = 1		#close valve
valveFullOpen = 194  #upper valve limit, 8 bit adc
valveClosed = 64      #lower valve limit, 8 bit adc
		
startlt = "w20"         #time low temp on
stoplt = "w21"	    #time low temp off
		
temp_word = "w17"   #(b34 + b35)
temp_byte = "b36"
hours = "b37"
mins = "b38"
secs = "b39"


def OnPowerUp():
  setfreq m8
  dirsB = "$0F"
  dirsC = "$86"
  adcsetup = "$0001"

  high Lcd
  high SSR
  
  SRet = 2300                # Set point  was 19.3
  Pwr  = 0
  Lag  = 120
  cLag = 0
  startlt  = 2100               # Time for low temperature on
  stoplt   = 500                # Time for low temperature off
  BWn  = 400	              # 23C-4C=19C 
	
  #Initialise SOut
      
  TDisp = false
  TempPin = TPinRet: TRead()
  TempPin = TPinOut: TRead()
   
  if TRetour >= SRet:
    SOut = SRet
  else:
    TempPin = TPinEnv: TRead ()
    SOut = SRet-TEnv/10*2+SRet
     
  #set main LCD screen 
#	TempOutput:(Time)
#{ if PV3 > startlt: (time on)
#    SolarPower = false
 # 
  
#  if PV3 > SSH: (time of)
##    SolarPower = true
#  
#
	
#	UpdateBandwidth: (high temp low temp setting)
#{
#  BW2L = SP2 - BW2 (low Temp setting)
#  BW2H = SP2  (high Temp setting)
#
  sleep(1000)
  MainScreen()
  
  #set pump
  high pump
  
  # close valve on startuUp
  valveGoal = valveClosed: valveControl()
  serout SSR, Baud, (0, 0)	#turn off SSRs
 
  # set function
  isElectrical = true
  isHWC = false
  isSettled = false
	
  #  Read Time 
  i2cslave %11010000, i2cslow, i2cbyte
  readi2c 0,(secs,mins,hours,b34,b35,b36)
  b34=b36
  temp_byte = secs %11110000 / 16 * 10
  secs = secs % 00001111 + temp_byte
  temp_byte = mins %11110000 / 16 * 10
  mins = mins % 00001111 + temp_byte
  temp_byte = hours % 11110000 / 16 * 10
  hours = hours % 00001111 + temp_byte
  temp_byte = b9 %11110000 / 16 * 10
  b9 = b9 %00001111 + temp_byte
  temp_byte = b8 %11110000 / 16 * 10
  b8 = b8 & %00001111 + temp_byte  
    

def main():
  
  TDisp = true
  TempPin = TPinRet: TRead()
  TempPin = TPinOut: TRead()
  TempPin = TPinEnv: TRead()
  TEmpPin = TPinHW:  TRead()
  
 
  if btnISet == true:
    isElectrical = isElectrical ^ 1
    isHWC = isHWC ^  1
  
  
  
  if TRetour >= SRet:
     isSettled = true
 

  #controls operation
  if flowSw == true:
  
    if isElectrical == true: 
    
      #update mode
      serout lcd, baud, (0, hMode, "ELECTRIC")

      #if in Electric mode the valve must be closed
      readadc a.0, valvePos
      if valvePos > valveClosed:
        valveGoal = valveClosed: mtrDir = mtrClose: valveControl()
            
    
      #check if enough hot water for change over
      if THW > HWSwitchOver and isSettled == true: 
        isElectrical = false    
        isHWC = true
        serout SSR, Baud, (0, 0)	#turn off SSRs
    else:
        elControl()
    
    if isHWC == true: 
    
      #update mode
      serout lcd, baud, (0, hMode, "HWC     ")
      #turn off SSRs
      serout SSR, Baud, (0, 0)

      #check if enough water for change over
      if THW < SOut:
        isElectrical = true
        isHWC = false
    else:
        hwcControl()
    
    #check if in other modes
    if isElectrical == false and isHWC == false:
      serout lcd, baud, (0, hMode, "OFF     ")
    elif isElectrical == true and isHWC == true:
      serout lcd, baud, (0, hMode, "RESETING")
      isElectrical = true
      isHWC = false
    
  else:
    # no flow established, display error message
    serout lcd, baud, (0, hMode, "FLOW ERR")

  #update display data
  DisplaySout()
  DisplaySret()
  DisplayPwr()
  
  #send log to PC
  SendDataLog()

main()
 

#Subroutines
#================================
def hwcControl():
# hwcControl contains the PID algorithm for hwc heating
# USE
#   hwcControl()
# 
# IN arg: none
# OUTPUT: none
#
# NOTE: alters pwr for display purposes
  if TOut <= Sout:
    Err1 = SOut - TOut
    if Err1 >:
      Gain = Err1*kH/100
      valveGoal = Gain + valveGoal max valveFullOpen
      mtrDir = mtrOpen: valveControl()
  else:
    Err1 = TOut - Sout
    if Err1 > BW:
      Gain = Err1*kH/100
      
      if valveGoal > Gain:
        valveGoal = valveGoal - Gain
      else:
        valveGoal = valveClosed 
      if valveGoal < valveClosed: 
        valveGoal = valveClosed
      mtrDir = mtrClose: valveControl()
  
  #calculates pwr as percentage of (valveFullOpen - valveClosed)
  wtmp1 = valveFullOpen - valveClosed
  if valvePos >= valveClosed:
    pwr = valvePos - valveClosed * 100 / wtmp1 * 10
  else:
    pwr = 0
  PID2()


def elControl():
# elControl contains the PID algorithm for electrical heating
#
# USE
#  elControl()
# 
# IN arg: none
# OUTPUT: pwr
  #PID1 control
  #==============================
  #Proportional
  if TOut <= Sout:
    Err1 = SOut - TOut
    if Err1 > BW:
      Gain = Err1*kP/100
      Pwr  = Gain + Pwr max 1000
  else:
    Err1 = TOut - Sout
    if Err1 > BW:
      Gain = Err1*kP/100
      if Pwr > Gain:
        Pwr = Pwr - Gain
      else:
        Pwr = 0
      
    
  
  PID2()
  serout SSR, Baud, (b19, b18)


def PID2():
# PID2 controls the Set Value of the output
#
# USE 
#   PID2()
#
# IN arg: none
# OUTPUT: SOut


  #PID2 control
  #==============================
  inc cLag
  if TRetour <= SRet:
    Err2 = SRet - TRetour
    if Lag = cLag:
      Gain = kI*Err2/10
      SOut = SOut + Gain max 8000
      cLag = 0
    
  else:
    Err2 = TRetour - SRet
    if Lag = cLag:
      Gain = kI*Err2/10
      Sout = Sout - Gain
      if SOut < SRet: 
        Sout = SRet
      
      cLag = 0
    

def TRead():
# Returns the t� at the specified pin and display results 
#
# USE 
#   TempPin = xx: [TDisp = True|False:] TRead()
#
# IN arg: TempPin
# OUTPUT: Corresponding value of TempPin [b4..b13]
# 
# NOTE: if TDisp is set then the resulting value is displayed
  readtemp12 TempPin, tTemp
  tmp1 = tTemp + 4
  tmp2 = tTemp & $00F *625/100
  tTemp = tmp1 * 100 + tmp2
  
  select TempPin
    case TPinRet
      bptr = 4
      tmp3 = hTret
    case TPinOut
      bptr = 6
      tmp3 = hTout
    case TPinHW
      bptr = 8
      tmp3 = hThwc
    case TPinEnv
      bptr = 10
      tmp3 = hTenv
  endselect
  
  @bptrinc = tmp5
  @bptr    = tmp6
  
  if TDisp = true:
    tmp2 = tmp2/10
    serout Lcd, Baud, (0, tmp3)
    if tmp1 <10:
      serout Lcd, Baud, (" ")
    
    serout Lcd, Baud, (#tmp1, ".", #tmp2)
  
 
  
 
def MainScreen():
# Updates main screen backround
#
# USE
#   MainScreen()
#
# IN arg: none
# OUTPUT: none
  serout Lcd, Baud, (0, clr)
  serout Lcd, Baud, (0, line1)
  for bCount = 95 to 114
    read bCount, tmp1
    serout Lcd, Baud, (tmp1)
  next
  serout Lcd, Baud, (0, line2)
  for bCount = 115 to 134
    read bCount, tmp1
    serout Lcd, Baud, (tmp1)
  next
  serout Lcd, Baud, (0, line3)
  for bCount = 135 to 154
    read bCount, tmp1
    serout Lcd, Baud, (tmp1)
  next
  serout Lcd, Baud, (0, line4)
  for bCount = 155 to 174
    read bCount, tmp1
    serout Lcd, Baud, (tmp1)
  next 
 
 
def DisplaySout():
# Updates the Sout value on main screen
#
# USE
#   DisplaySout()
# 
# IN arg: none
# OUTPUT: none

  tmp1 = SOut /100
  tmp2 = SOut//100 / 10
  serout Lcd, Baud, (0, hSo, #tmp1, ".", #tmp2)
 
 
def DisplaySret():
# Updates the Sret value on main screen
#
# USE
#   DisplaySret()
# 
# IN arg: none
# OUTPUT: none

  tmp1 = SRet /100
  tmp2 = SRet //100 / 10
  serout Lcd, Baud, (0, hSr, #tmp1, ".", #tmp2)
 
 
def DisplayPwr():
# Updates the Pwr value on main screen
#
# USE
#   DisplaySout()
# 
# IN arg: none
# OUTPUT: none

  tmp1 = Pwr /10
  tmp2 = Pwr//10
  if Pwr < 100:
      serout Lcd, Baud, (0, hPwr, " ", tmp1, ".", tmp2)
  elif 101 <= Pwr <= 999:
      serout Lcd, Baud, (0, hPwr, tmp1, ".", tmp2)
  else:
      serout Lcd, Baud, (0, hPwr, tmp1, " ")
 
 

def SendDataLog():
# Sends Data to serial out port for logging
#
# USE
#   SendDataLog()
#
# IN arg: none
# OUTPUT: none
 
  sertxd (w23, ",", SRet, ",", THW, ",", Tout, ",", TRetour,",",valvePos,",",valveGoal,",",Sout, cr, lf)
  inc w23
 


def getButtons():
# getButtons returns the statuts of buttons
#
# USE
#  getButtons()
#
# IN arg: none
# OUTPUT: buttons

  #wait for button to be pressed
  while buttons>0: 
    buttons = pinsB + 4
 
  #software debounce
  sleep(100)
    
  #wait for release
  while tmp1==0:
    tmp1 = pinsB + 4



def valveControl():
# controls the valve opening
# USE
#   mtrStep = xx: mtrDir = x]: valveControl()
#
# IN arg: mtrStep, the number of steps to be done
#         mtrDir, the direction (mtrOpen or mtrClose)
# OUTPUT: valvePos, the position of the valve, 0 closed, 200 full open
#
# NOTE: if the valve reaches lower limit or calculated upper limit
# it will not operate. mtrDir may be set before this call.

   readadc a.0, valvePos
   
   if valveGoal < valveClosed: 
     if valvePos <= valveClosed:
       skipControl()
     else:
       valveGoal = valveClosed
     

  
   tmp2 = mtrIndex//4
 #  sertxd (" Steps pos: ", #tmp2, cr, lf, cr,lf)
   
  do until valveGoal = valvePos
   #test only, remove when in use!
    #serout lcd, baud, (0, line1, " Valve pos: ", #valvePos, "    ")
    #serout lcd, baud, (0, line3, "     Steps: ", #mtrIndex, "     ")


    #establish motor direction
    if valvePos < valveGoal:
      mtrDir = mtrOpen
    else:
      mtrDir = mtrClose
    
    
    #sertxd (" Valve pos: ", #valvePos, ", goal: ", #ValveGoal, cr, lf)
 #   sertxd (" Steps: ", #tmp2, cr, lf, cr,lf)
    #pause 250
    
    #pause 50
    if mtrDir == mtrOpen:
    #pause 50    
      inc mtrIndex      
    else:
      dec mtrIndex   
    

    #move motor
    lookup tmp2, (%1100, %0110, %0011, %1001), pinsB
    pause 20
    tmp2 = mtrIndex//4
    
    readadc a.0, valvePos
  loop 
  
def skipControl():
  pinsB = 0


