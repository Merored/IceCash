# -*- coding: utf8 -*-
import serial
import traceback
import time
import sys
import string

const_error=1
const_cmd={'sale':11,'return':13,'X':60,'Z':61,'close_check':55,'cancel_check':56,}
MAX_TRIES = 10
MIN_TIMEOUT = 0.05
OS_CP = 'cp866'
PORT = '/dev/ttyS0' #'COM1'
ENQ = chr(0x05)
STX = chr(0x02)
ACK = chr(0x06)
NAK = chr(0x15)
ETX = chr(0x03)
EOT = chr(0x04)
password = 0000
OK = 0

def bufStr(*b):

    """Преобразует буфер 16-х значений в строку"""
    result = []
    for x in b: result.append(chr(x))
    return string.join(result,'')

def LRC(buff):
    """Подсчет CRC"""
    result = 0
    for c in buff:
        result = result ^ ord(c)
    print( "LRC",result)
    return result

def hexStr(s):
    """Преобразуем в 16-е значения"""
    result = []
    for c in s: result.append(hex(ord(c)))
    return string.join(result,' ')

DEFAULT_ADM_PASSWORD = bufStr(0x1e,0x0,0x0,0x0) #Пароль админа по умолчанию = 30
DEFAULT_PASSWORD     = bufStr(0x00,0x00)  #Пароль кассира по умолчанию = 0

class KKM:
        def __init__(self,conn, password):
                self.conn     = conn
                self.password = 0000
                if self.__checkState()!=ACK:
                        buffer=''
                        while self.conn.inWaiting():
                                buffer += self.conn.read()
                        self.conn.write(ENQ)
                        time.sleep(0.3)
                        if self.conn.read(1)!=ACK:
                                raise RuntimeError("ACK expected")
        def __checkState(self):
            """Проверить на готовность"""
            self.conn.write(ENQ)
            repl = self.conn.read(1)
            if not self.conn.isOpen():
                    raise RuntimeError("Serial port closed unexpectly")
            if repl==NAK:
                    return NAK
            if repl==ACK:
                    return ACK
                    raise RuntimeError("Unknown answer")



        def __sendCommand(self,cmd,params):
                """Стандартная обработка команды"""
                self.conn.flush()
                data   = DEFAULT_PASSWORD + chr(cmd) 

            
                try:
                    data = data + chr(params)
                except:
                    data = data + params
                data = data + ETX
                #print "length="+str(len(params))
                crc = LRC(data)
                self.conn.write(STX+data+chr(crc))
                #dbg(hexStr(STX+content+crc))
                time.sleep(0.5)
                self.conn.read()
                self.conn.flush()
                self.conn.write(EOT)
                return OK

          

        def Beep(self):
                """Гудок"""
                self.__sendCommand(0x47,''  )


try:
    ser = serial.Serial(0, 9600,\
                        parity=serial.PARITY_NONE,\
                        stopbits=serial.STOPBITS_ONE,\
                        timeout=0.7,\
                        writeTimeout=0.7)
except:
    print("error") 



try:
    kkm = KKM(ser,bufStr(0x0,0x0,0x0,0x0))
    err = 0
    print("connect frk") 
    kkm.Beep()
    print("Beep") 
except Exception as e: 
    print(e)
    err=const_error
    traceback.print_exc(file=sys.stdout)
    #self.ser.close()//for renull
    print("not connect frk")


