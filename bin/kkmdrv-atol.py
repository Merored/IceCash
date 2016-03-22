# -*- coding: utf8 -*-
import serial
import traceback
import time
import sys
import string


MAX_TRIES = 5
T1 = 0.5
T2 = 2
T3 = 0.5
T4 = 0.5
T5 = 10
T6 = 0.5 
T7 = 0.5
T8 = 1


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

def hexStr(s):
    """Преобразуем в 16-е значения"""
    result = []
    for c in s: result.append(hex(ord(c)))
    return string.join(result,' ')

def float2100int(f,digits=2):
        mask = "%."+str(digits)+'f'
        s    = mask % f
        return int(s.replace('.',''))

def LRC(buff):
    """Подсчет CRC"""
    result = 0
    for c in buff:
        result = result ^ ord(c)
    print( "LRC",result)
    return result

DEFAULT_ADM_PASSWORD = bufStr(0x00,0x1e) #Пароль админа по умолчанию = 30
DEFAULT_PASSWORD     = bufStr(0x00,0x00)  #Пароль кассира по умолчанию = 0


class kkmException(Exception):
        def __init__(self, value):
                self.value = value
                self.s = { 0x88: "Смена превысила 24 часа (Закройте смену с гашением) (ошибка 0x88)",\
                           0x8C: "Неверный пароль (ошибка 0x8C)",\
                           0x7A: "Данная модель ККТ не может выполнить команду (ошибка 0x7A)",\
                           0x9B: "Чек открыт – операция невозможна (ошибка 0x9B)",\
                           0x9A: "Чек закрыт – операция невозможна (ошибка 0x9A)",\
                           0x9C: "Смена открыта, операция невозможна (ошибка 0x9C)",\
                           0x8F: "Обнуленная касса (повторное гашение невозможно) (ошибка 0x8F)",
                        }[value]
        def __str__(self):
            return self.s

        def __unicode__(self):
            return unicode(str(self.s),'utf8')


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


        def __clearAnswer(self):
                """Сбросить ответ если он болтается в ККМ"""
                def oneRound():
                        self.conn.flush()
                        self.conn.write(ENQ)
                        a = self.conn.read(1)
                        time.sleep(T7)
                        if a==ACK:
                                return 1
                        elif a==STX:
                                a = self.conn.read(1)
                                time.sleep(T1)
                                if a==STX:
                                       time.sleep(T5)
                                       self.conn.write(EOT)
                                time.sleep(T1)
                                self.conn.write(EOT)
                                time.sleep(T1)
                                return 2
                        else:
                                raise RuntimeError("Something wrong")
                n=0
                while n<MAX_TRIES and oneRound()!=1:
                        n+=1
                if n>=MAX_TRIES:
                        return 1
                return 0


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
                self.__clearAnswer()
                self.__sendCommand(0x47,'')


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
    err= 1 
    traceback.print_exc(file=sys.stdout)
    #self.ser.close()//for renull
    print("not connect frk")


