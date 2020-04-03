#rem
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
#endrem

#picaxe 28x2
'#no_data
'#no_table
#terminal 9600

'Eeprom preload
eeprom 95, ("So  xx.xß Tout xx.xßSr  xx.xß Tret xx.xßPWR xx.x% Tenv xx.xßAUTO      Thwc xx.xß")


'Hardware definitions
'================================



'Temperature sensors pins
{ symbol TPinRet  = C.0		'retour       [T1]
  symbol TPinOut  = A.3		'inlet        [T2]
  symbol TPinHW   = A.2		'Hot Water    [T3]
  symbol TPinEnv  = A.1		'Environment  [T4]
  symbol pinVpos  = a.0		'valve position feedback from potentiometer [T5]
}

 'serial comms
{ symbol Lcd = C.1
  symbol SSR = C.2
}
 'buttons
  symbol btnISet = pinB.4

 'limiter input
  symbol mtrLim = pinC.5
}

 'flow switch
{ symbol FlowSw = pinC.6		'active low: activated wen false
}

 'flow pump
{ symbol Pump = C.7
}
}

'Software definitions
'================================
{ 
 'LCD constants
{ symbol rows  = 4
  symbol cols  = 20
  symbol line1 = $80
  symbol line2 = $C0
  symbol line3 = $94
  symbol line4 = $D4
  symbol clr   = 1
  
  'placeholders
  symbol hSo   = $84
  symbol hSr   = $C4
  symbol hPwr  = $98
  symbol hTout = $8F
  symbol hTret = $CF
  symbol hTenv = $A3
  symbol hThwc = $E3
  symbol hMode = $D4
   
}

 'System Constants
{ symbol baud = T2400_8
  symbol TDisp = bit0
  symbol isElectrical = bit2
  symbol isHWC = bit3
  symbol isSettled = bit4
  symbol isNight = bit5
  symbol false = 0
  symbol true  = 1
 }
  
 'program variables
{ symbol bCount  = b55		'byte counter
  symbol tmp1    = b48		'green vars
  symbol tmp2    = b49
  symbol wtmp1   = w24
  symbol tmp3    = b50
  symbol tmp4    = b51
  symbol wtmp2   = w25
  symbol tmp5    = b52
  symbol tmp6    = b53
  symbol wtmp3   = w26
  symbol tTemp   = w26		'used in temperature aquisition
  symbol TempPin = b54		'used in temperature aquisition
  
  'control variables
  symbol TRetour = w2		'retour temperature
  symbol TOut    = w3		'inlet temperature
  symbol THW     = w4		'hot water temperature
  symbol TEnv    = w5		'Environment temperature
  symbol T5Val   = w6		'Reserved
  symbol BWn      = w22          '(23C-BWn=19C) 
  symbol HWSwitchOver = 3200     'HWC threshold was 3000

  
  'PID
  symbol SOut = w7		'Set output temperature
  symbol SRet = w8		'Set return temperature
  symbol Pwr  = w9		'Duty cycle for pwm
  symbol Err1 = w10
  symbol Err2 = w11
  symbol Lag  = b24		'TRetour lag, cycles
  symbol cLag = b25
  symbol Gain = w13
  symbol kP   = 40
  symbol kI   = 25
  symbol kH   = 3
  symbol BW   = 10		'0.1° Bandwidth
 
  'Buttons
  symbol buttons = b1		'buttons status return 
  symbol btnDn   = bit11
  symbol btnUp   = bit10
  symbol btnEsc  = bit9
  symbol btnSet  = bit8
  
  'Step Motor
  symbol mtrDir    = bit1	'motor direction, true negative, false positive
  symbol mtrStep   = b28	'number of steps
  symbol mtrIndex  = b29      'step index
  symbol valvePos  = w15	'valve position
  symbol valveGoal = w16	'valve goal
  
  symbol mtrOpen  = 0	      'open valve
  symbol mtrClose = 1		'close valve
  symbol valveFullOpen = 194  'upper valve limit, 8 bit adc
  symbol valveClosed = 64      'lower valve limit, 8 bit adc
		
  symbol startlt = w20         'time low temp on
  symbol stoplt = w21	    'time low temp off
		
  symbol temp_word = w17   '(b34 + b35)
  symbol temp_byte = b36
  symbol hours = b37
  symbol mins = b38
  symbol secs = b39
}
}


OnPowerUp:
{ setfreq m8
  dirsB = $0F
  dirsC = $86
  adcsetup = $0001

  high Lcd
  high SSR
  
  SRet = 2300                ' Set point  was 19.3
  Pwr  = 0
  Lag  = 120
  cLag = 0
  startlt  = 2100               ' Time for low temperature on
  stoplt   = 500                ' Time for low temperature off
  BWn  = 400	              ' 23C-4C=19C 
	
  'Initialise SOut
      
  TDisp = false
  TempPin = TPinRet: gosub TRead
  TempPin = TPinOut: gosub TRead
   
  if TRetour >= SRet then
    SOut = SRet
  else
    TempPin = TPinEnv: gosub TRead
    SOut = SRet-TEnv/10*2+SRet
  endif
  
     
  'set main LCD screen 
'	TempOutput:(Time)
'{ if PV3 > startlt then (time on)
'    SolarPower = false
 ' endif
  
'  if PV3 > SSH then (time of)
''    SolarPower = true
'  endif
'return}
	
'	UpdateBandwidth: (high temp low temp setting)
'{
'  BW2L = SP2 - BW2 (low Temp setting)
'  BW2H = SP2  (high Temp setting)
'return}
  pause 1000
  gosub MainScreen
  
  'set pump
  high pump
  
  ' close valve on startuUp
  valveGoal = valveClosed: gosub valveControl
  serout SSR, Baud, (0, 0)	'turn off SSRs
 
  ' set function
  isElectrical = true
  isHWC = false
  isSettled = false
	
  '  Read Time 
  i2cslave %11010000, i2cslow, i2cbyte
  readi2c 0,(secs,mins,hours,b34,b35,b36)
  let b34=b36
  let temp_byte = secs & %11110000 / 16 * 10
  let secs = secs & %00001111 + temp_byte
  let temp_byte = mins & %11110000 / 16 * 10
  let mins = mins & %00001111 + temp_byte
  let temp_byte = hours & %11110000 / 16 * 10
  let hours = hours & %00001111 + temp_byte
  let temp_byte = b9 & %11110000 / 16 * 10
  let b9 = b9 & %00001111 + temp_byte
  let temp_byte = b8 & %11110000 / 16 * 10
  let b8 = b8 & %00001111 + temp_byte  
    }

main:
  
  TDisp = true
  TempPin = TPinRet: gosub TRead
  TempPin = TPinOut: gosub TRead
  TempPin = TPinEnv: gosub TRead
  TEmpPin = TPinHW:  gosub TRead
  
 
  if btnISet = true then
    isElectrical = isElectrical XOR 1
    isHWC = isHWC XOR 1
  endif 
  
  
  if TRetour >= SRet then
     isSettled = true
  endif

  'controls operation
  if flowSw = true then
  
    if isElectrical = true then 
    
      'update mode
      serout lcd, baud, (0, hMode, "ELECTRIC")

      'if in Electric mode the valve must be closed
      readadc a.0, valvePos
      if valvePos > valveClosed then
        valveGoal = valveClosed: mtrDir = mtrClose: gosub valveControl
      endif      
    
      'check if enough hot water for change over
      if THW > HWSwitchOver and isSettled = true then  
        isElectrical = false    
        isHWC = true
        serout SSR, Baud, (0, 0)	'turn off SSRs
      else
        gosub elControl
      endif
      
    endif
    
    if isHWC = true then 
    
      'update mode
      serout lcd, baud, (0, hMode, "HWC     ")
      'turn off SSRs
      serout SSR, Baud, (0, 0)

      'check if enough water for change over
      if THW < SOut then
        isElectrical = true
        isHWC = false
      else
        gosub hwcControl
      endif
      
    endif
    
    'check if in other modes
    if isElectrical = false and isHWC = false then
      serout lcd, baud, (0, hMode, "OFF     ")
    elseif isElectrical = true and isHWC = true then
      serout lcd, baud, (0, hMode, "RESETING")
      isElectrical = true
      isHWC = false
    endif
    
  else
    ' no flow established, display error message
    serout lcd, baud, (0, hMode, "FLOW ERR")
  endif

  'update display data
  gosub DisplaySout
  gosub DisplaySret
  gosub DisplayPwr
  
  'send log to PC
  gosub SendDataLog
goto main
 

'Subroutines
'================================
hwcControl:
' hwcControl contains the PID algorithm for hwc heating
' USE
'   gosub hwcControl
' 
' IN arg: none
' OUTPUT: none
'
' NOTE: alters pwr for display purposes
{
  if TOut <= Sout then
    Err1 = SOut - TOut
    if Err1 > BW then
      Gain = Err1*kH/100
      valveGoal = Gain + valveGoal max valveFullOpen
      mtrDir = mtrOpen: gosub valveControl
    endif
  else
    Err1 = TOut - Sout
    if Err1 > BW then
      Gain = Err1*kH/100
      
      if valveGoal > gain then
        valveGoal = valveGoal - Gain
      else
        valveGoal = valveClosed
      endif 
      
      if valveGoal < valveClosed then 
        valveGoal = valveClosed
      end if
      
      mtrDir = mtrClose: gosub valveControl
    endif
  endif
  
  'calculates pwr as percentage of (valveFullOpen - valveClosed)
  wtmp1 = valveFullOpen - valveClosed
  if valvePos => valveClosed then
    pwr = valvePos - valveClosed * 100 / wtmp1 * 10
  else
    pwr = 0
  endif  
  
  gosub PID2
return}


elControl:
' elControl contains the PID algorithm for electrical heating
'
' USE
'  gosub elControl
' 
' IN arg: none
' OUTPUT: pwr
{
  'PID1 control
  '==============================
  'Proportional
  if TOut <= Sout then
    Err1 = SOut - TOut
    if Err1 > BW then
      Gain = Err1*kP/100
      Pwr  = Gain + Pwr max 1000
    endif
  else
    Err1 = TOut - Sout
    if Err1 > BW then
      Gain = Err1*kP/100
      if Pwr > Gain then
        Pwr = Pwr - Gain
      else
        Pwr = 0
      endif
    endif
  endif
  gosub PID2
  serout SSR, Baud, (b19, b18)

return}


PID2:
' PID2 controls the Set Value of the output
'
' USE 
'   gosub PID2
'
' IN arg: none
' OUTPUT: SOut


{  'PID2 control
  '==============================
  inc cLag
  if TRetour <= SRet then
    Err2 = SRet - TRetour
    if Lag = cLag then
      Gain = kI*Err2/10
      SOut = SOut + Gain max 8000
      cLag = 0
    endif
  else
    Err2 = TRetour - SRet
    if Lag = cLag then
      Gain = kI*Err2/10
      Sout = Sout - Gain
      if SOut < SRet then 
        Sout = SRet
      endif
      cLag = 0
    endif
  endif
return}

TRead:
' Returns the t° at the specified pin and display results 
'
' USE 
'   TempPin = xx: [TDisp = True|False:] gosub TRead
'
' IN arg: TempPin
' OUTPUT: Corresponding value of TempPin [b4..b13]
' 
' NOTE: if TDisp is set then the resulting value is displayed
{
  readtemp12 TempPin, tTemp
  tmp1 = tTemp >> 4
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
  
  if TDisp = true then
    tmp2 = tmp2/10
    serout Lcd, Baud, (0, tmp3)
    if tmp1 <10 then
      serout Lcd, Baud, (" ")
    endif
    serout Lcd, Baud, (#tmp1, ".", #tmp2)
  endif
 return}
  
 
MainScreen:
' Updates main screen backround
'
' USE
'   gosub MainScreen
'
' IN arg: none
' OUTPUT: none
{ serout Lcd, Baud, (0, clr)
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
 return}
 
DisplaySout:
' Updates the Sout value on main screen
'
' USE
'   gosub DisplaySout
' 
' IN arg: none
' OUTPUT: none

{ tmp1 = SOut /100
  tmp2 = SOut//100 / 10
  serout Lcd, Baud, (0, hSo, #tmp1, ".", #tmp2)
 return}
 
DisplaySret:
' Updates the Sret value on main screen
'
' USE
'   gosub DisplaySret
' 
' IN arg: none
' OUTPUT: none

{ tmp1 = SRet /100
  tmp2 = Sret//100 / 10
  serout Lcd, Baud, (0, hSr, #tmp1, ".", #tmp2)
 return}
 
DisplayPwr:
' Updates the Pwr value on main screen
'
' USE
'   gosub DisplaySout
' 
' IN arg: none
' OUTPUT: none
{
  tmp1 = Pwr /10
  tmp2 = Pwr//10
  select Pwr
    case < 100
      serout Lcd, Baud, (0, hPwr, " ", #tmp1, ".", #tmp2)
    case 101 to 999
      serout Lcd, Baud, (0, hPwr, #tmp1, ".", #tmp2)
    else
      serout Lcd, Baud, (0, hPwr, #tmp1, " ")
  endselect
 return}
 

SendDataLog:
' Sends Data to serial out port for logging
'
' USE
'   gosub SendDataLog
'
' IN arg: none
' OUTPUT: none
{ 
  sertxd (#w23, ",", #SRet, ",", #THW, ",", #Tout, ",", #TRetour,",",#valvePos,",",#valveGoal,",",#Sout, cr, lf)
  inc w23
 return}


getButtons:
' getButtons returns the statuts of buttons
'
' USE
'  gosub getButtons
'
' IN arg: none
' OUTPUT: buttons
{
  'wait for button to be pressed
  do 
    buttons = pinsB >> 4
  loop until buttons > 0
 
  'software debounce
  pause 100
    
  'wait for release
  do
    tmp1 = pinsB >> 4
  loop until tmp1 = 0

return}

valveControl:
' controls the valve opening
' USE
'   mtrStep = xx: mtrDir = x]: gosub valveControl
'
' IN arg: mtrStep, the number of steps to be done
'         mtrDir, the direction (mtrOpen or mtrClose)
' OUTPUT: valvePos, the position of the valve, 0 closed, 200 full open
'
' NOTE: if the valve reaches lower limit or calculated upper limit
' it will not operate. mtrDir may be set before this call.
{
   readadc a.0, valvePos
   
   if valveGoal < valveClosed then 
     if valvePos <= valveClosed then
       goto skipControl
     else
       valveGoal = valveClosed
     endif
   end if
  
   tmp2 = mtrIndex//4
 '  sertxd (" Steps pos: ", #tmp2, cr, lf, cr,lf)
   
  do until valveGoal = valvePos
   'test only, remove when in use!
    'serout lcd, baud, (0, line1, " Valve pos: ", #valvePos, "    ")
    'serout lcd, baud, (0, line3, "     Steps: ", #mtrIndex, "     ")


    'establish motor direction
    if valvePos < valveGoal then
      mtrDir = mtrOpen
    else
      mtrDir = mtrClose
    endif
    
    'sertxd (" Valve pos: ", #valvePos, ", goal: ", #ValveGoal, cr, lf)
 '   sertxd (" Steps: ", #tmp2, cr, lf, cr,lf)
    'pause 250
    
    'pause 50
        if mtrDir = mtrOpen then
    'pause 50    
      inc mtrIndex      
    else
      dec mtrIndex   
    endif

    'move motor
    lookup tmp2, (%1100, %0110, %0011, %1001), pinsB
    pause 20
    tmp2 = mtrIndex//4
    
    readadc a.0, valvePos
  loop 
  
skipControl:
  pinsB = 0
return}

