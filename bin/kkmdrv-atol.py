# -*- coding: utf8 -*-
import serial
import traceback
import time
import sys
import string
from struct import pack, unpack

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
U = chr(0x55)
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
def priceRed(money):
    """
    Приобразует float число в то, что можно передать в ККМ как кол-во каких либо денег
    Диапазон возможного значения цены и т д, где 1 = 1 коп. 
    0000000000..9999999999 (10 знаков)
    Пример: 
    Передаём число 1.11 (Допустим 1 руб 11 коп) функция вернёт строку = 0x00 0x00 0x00 0x0a 0x01`
    """
    moneylist = (int(money*100))
    chet = False
    if moneylist > 9999999999:
        raise RuntimeError("Число должно быть в диапазоне 0..9999999999")
    if moneylist < 100000000: 
        if moneylist < 1000000:
            if moneylist < 10000:
                if moneylist < 100:
                    result = chr(0x00) + chr(0x00) + chr(0x00) + chr(0x00)
                else:
                    result = chr(0x00) + chr(0x00) + chr(0x00)
            else: 
                result = chr(0x00) + chr(0x00)
        else:
            result = chr(0x00) 
    first = True
    chet = False
    simvol = 0
    for i in str(moneylist) :
        if chet: 
            simvol = int(i)*10
            chet = False
            continue
        elif moneylist > 99999999 or moneylist > 999999 or moneylist > 9999 or moneylist > 99 or moneylist > 1 and first: 
            simvol = int(i) + simvol
            result = result + chr(int(str(simvol), 16))
            first = False
            chet = True
            simvol = 0
            continue
        if moneylist > 999999999 or moneylist > 9999999 or moneylist > 99999 or moneylist > 999 or moneylist > 9 and first: 
            simvol = int(i)*10
            first = False
            chet = False
            continue
        if chet == False:
            simvol = int(i) + simvol
            chet = True
            result = result + chr(int(str(simvol), 16)) 
            simvol = 0
            continue
    print("result = "+  str(result) + "  Money = " + str(money) )
    return result

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
                        print("__clearAnswer = " + hexStr(a))
                        time.sleep(T7)
                        if a==ACK:
                                self.conn.write(EOT)
                                print("Clear answer ACK")
                                return 1
                        elif a==STX:
                                print("Clear answer STX")
                                time.sleep(T1)
                                while True:
                                    a = self.conn.read(1)
                                    print ( " __clearAnswer  a = " + hexStr(a))
                                    time.sleep(0.2)
                                    if a == ETX:
                                        time.sleep(0.2)
                                        a = self.conn.read(1)
                                        self.conn.write(ACK)
                                    if a == EOT:
                                        break 
  
                                self.conn.write(ACK)
                                if a == EOT:
                                    time.sleep(T1)
                                    return 1
                        else:
                                raise RuntimeError("Something wrong")
                n=0
                while n<MAX_TRIES and oneRound()!=1:
                        n+=1
                if n>=MAX_TRIES:
                        return 1
                return 0

        def __readAnswer(self):
                """Считать ответ ККМ"""

                a = self.conn.read(1)
                print("__readAnswer = " + hexStr(a))
                if a==ENQ:
                        self.conn.write(ACK)
                        time.sleep(T1)
                        a = self.conn.read(1)
                        if a==STX:
                         cmd      = self.conn.read(1)
                         print "cmd = " + cmd
                         if cmd == U:
                            errcode  = self.conn.read(1)
                            print "errcode = " + hexStr(errcode)

                            i = 0
                            data = []
                            while True:
                                data.insert(i, self.conn.read(1))
                                if data[i] == ETX:
                                    data[i] = None
                                    break 
                                i = i + 1
                            if data[1] != None:
                                print "data = ".join(str(value) for value in data)

                         crc = self.conn.read(1)
            
                         print "crc = " + hexStr(crc)
                         if data[1] == None:
                            mycrc = LRC(cmd+errcode+ETX)
                         else:
                            mycrc = LRC(cmd+errcode.join(str(value) for value in data)+ETX)
                         if int(ord(crc))!=int(mycrc):
                                    self.conn.write(NAK)
                                    raise RuntimeError("Wrong crc %i must be %i " % (mycrc,ord(crc)))
                         if self.conn.read(1) == EOT:
                            self.conn.write(ACK)
                         self.conn.flush()
                         time.sleep(T1)
                         if ord(errcode)!=0:
                                 raise kkmException(ord(errcode))
                         return {'cmd':cmd,'errcode':ord(errcode),'data':data}
                        else:
                                raise RuntimeError("a!=STX %s %s" % (hex(ord(a)),hex(ord(STX))))
                elif a==NAK:
                        return None
                else:
                        raise RuntimeError("a!=ENQ")



        def __sendCommand(self,cmd,params):
                """Стандартная обработка команды"""
                self.conn.write(ENQ)
                tires = 0
                def oneRound():

                    self.conn.flush()
                    print ( "__sendCommand =  " + str(cmd))
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
                    time.sleep(T1)

                tires = 1
                sendCMD = False
                while True:
                    a = self.conn.read(1)
                    if a == ACK and tires > 1 and sendCMD==False:
                        print ( " writeCMDself.conn.write(EOT)")
                        self.conn.write(EOT)
                        break
                    elif  a == ACK:
                        print ( " __sendCommand CMD = " + str(cmd))
                        oneRound()
                        tires = tires + 1
                    elif tires <= MAX_TRIES and sendCMD==False:
                        print ( " __sendCommand a = " + str(a))
                        oneRound()
                        tires = tires + 1
                    elif a == NAK: 
                        self.conn.write(ENQ)
                        tires = tires + 1
                        print ( " __sendCommand a = NAK")
                    else:
                        print "Превышено  максимальное кол-во попыток отправки команды"
                        return()
                        break

                    self.conn.flush()
                return OK


        def inMode(self,mode,):
            """Режим – устанавливаемый режим (двоично-десятичное число):
                1 - Режим регистрации.
                2 - Режим отчетов без гашения.
                3 - Режим отчетов с гашением.
                4 - Режим программирования.
                5 - Режим доступа к ФП.
                6 - Режим доступа к ЭКЛЗ.
            Пароль – 8 двоично-десятичных символов, пароль для входа в указанный режим
            (все пароли, кроме пароля доступа к ФП, программируются в таблице паролей
            ККТ, пароль доступа к ФП изменяется при проведении
            фискализации / перерегистрации).
            """
            self.__clearAnswer()
            self.__sendCommand(0x56,chr(0x01) + chr(0x00) + chr(0x00) + chr(0x00) + chr(0x01))
            a = self.__readAnswer()
            cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
            print("Cmd = " + cmd + " Errorcode = " + str(errcode) + " data = " + str(data[1]))

        def outMode(self):
            self.__clearAnswer()
            self.__sendCommand(0x48,'')
            a = self.__readAnswer()
            cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
            print("Cmd = " + cmd + " Errorcode = " + str(errcode) + " data = " + str(data[1]))
          

        def Beep(self):
                """Гудок"""
                self.__clearAnswer()
                self.__sendCommand(0x47,'')

        def cashIncome(self,count):
                """Внесение денег"""
                self.__clearAnswer()
                bin_summ = pack('l',float2100int(count)).ljust(5,chr(0x0))
                self.__sendCommand(0x49 + 0x0,bin_summ)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                print("Cmd = " + cmd + " Errorcode = " + str(errcode) + " data = " + str(data[1]))  
                """ПОНЯТЬ ДЛЯ ЧЕГО ЭТО И ЧТО ТУДА ПИСАТЬ"""
                #self.DOC_NUM    = unpack('i',data[0]+data[1]+chr(0x0)+chr(0x0))[0]

        def cashOutcome(self,count):
                """Выплата денег"""
                self.__clearAnswer()
                bin_summ = pack('l',float2100int(count)).ljust(5,chr(0x0))
                self.__sendCommand(0x4f + 0x00,bin_summ)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                print("Cmd = " + cmd + " Errorcode = " + str(errcode) + " data = " + str(data[1]))  
                """ПОНЯТЬ ДЛЯ ЧЕГО ЭТО И ЧТО ТУДА ПИСАТЬ"""
                #self.OP_CODE    = ord(data[0])
                #self.DOC_NUM    = unpack('i',data[1]+data[2]+chr(0x0)+chr(0x0))[0]

        def openCheck(self,flag,ctype):
            """Команда:     92H<Флаги (1)><Тип чека (1)> 
                     • Пароль оператора (4 байта)
                     • Флаги (1 бит): 0 – выполнить операцию, 
                                       1 – режим проверки операции
                                       3 – буферизировать документ (Если 3-й бит = 1, то после успешного выполнения команды ККТ переходит в режим 1.5.)

                     • Тип документа (1 байт): 1 – чек продажи,
                                               2 – чек возврата продажи,
                                               3 – чек аннулирования продажи, (В большинстве моделей поддерживаются только первые три типа чеков)
                                               4 – чек покупки,
                                               5 – чек возврата покупки,
                                               6 – чек аннулирования покупки. 
                                               Остальные значения зарезервированы и не используются.
            """
            self.__clearAnswer()
            if ctype not in range(0,4):
                   raise RuntimeError("Check type may be only 0,1,2,3 value")
            self.outMode()
            self.inMode(1)
            self.__clearAnswer()
            self.__sendCommand(0x92,chr(flag) + chr(ctype))
            a = self.__readAnswer()
            cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
            print("Cmd = " + cmd + " Errorcode = " + str(errcode) + " data = " + str(data[1]))  
            #self.OP_CODE    = ord(data[0])
            #self.outMode()
            return errcode



        def Sale(self,flags,count,price,department=0):
            """Продажа
                Команда:     52H<Флаги(1)><Цена(5)><Количество(5)><Секция(1)>. 
                     • Флаги (1 байт): 0-й (младший) бит: 0 – выполнить операцию, 1 – режим проверки операции (см стр. 53);
                                       1-й бит: 0 – проверять денежную наличность, 1 – не проверять (см.команду Аннулирование)
                     • Количество (5 байт) 0000000000..9999999999
                     • Цена (5 байт) 0000000000..9999999999
                     • Секция (1 байт) 0...30 Секция – двоично-десятичное число 00 .. 30 – секция, в которую осуществляется регистрация.
                                              Примечание 1: Если Секция = 0, то регистрация произведется в 1-ю секцию, но на чеке 
                                              и контрольной ленте не будут напечатаны номер и название секции. 

            """
            self.__clearAnswer()
            if count < 0 or count > 9999999999:
                   raise RuntimeError("Count myst be in range 0..9999999999")
            if price <0 or price > 9999999999:
                   raise RuntimeError("Price myst be in range 0..9999999999")
            if not department in range(0,16):
                   raise RuntimeError("Department myst be in range 1..16")


            bdep   = chr(department)
            self.__sendCommand(0x52,chr(0x00)  +  priceRed(9998)  + priceRed(100)  + chr(0x01))
            time.sleep(T1)
            a = self.__readAnswer()
        #            time.sleep(0.5)
            cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
            self.OP_CODE    = ord(data[0])
            return errcode


        def closeCheck(self,summa,text=u"",summa2=0,summa3=0,summa4=0,sale=0,taxes=[0,0,0,0][:]):
            """
                Команда:     4AH. Длина сообщения: 71 байт.
                     • Пароль оператора (4 байта)
                     • Сумма наличных (5 байт) 0000000000...9999999999
                     • Сумма типа оплаты 2 (5 байт) 0000000000...9999999999
                     • Сумма типа оплаты 3 (5 байт) 0000000000...9999999999
                     • Сумма типа оплаты 4 (5 байт) 0000000000...9999999999
                     • Скидка/Надбавка(в случае отрицательного значения) в % на чек от 0 до 99,99
                       % (2 байта со знаком) -9999...9999
                     • Налог 1 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 2 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 3 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 4 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Текст (40 байт)
                Ответ:       85H. Длина сообщения: 8 байт.
                     • Код ошибки (1 байт)
                     • Порядковый номер оператора (1 байт) 1...30
                     • Сдача (5 байт) 0000000000...9999999999
            """
            self.__clearAnswer()

            self.__sendCommand(0x4A,self.password+bsumma+bsumma2+bsumma3+bsumma4+bsale+btaxes+btext)
            time.sleep(0.5) # DOOM поставил а потом убрал
            a = self.__readAnswer()
            cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
            self.OP_CODE    = ord(data[0])
            #Сдачу я не считаю....
            #time.sleep(0.5) # Тут не успевает иногда
            return errcode


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
    kkm.openCheck(0,1)
    print("openCheck") 
    kkm.Beep()
    print("Beep") 
    kkm.Sale(0x00,1,100.00)
    print("sale") 

except Exception as e: 
    print(e)
    err= 1 
    traceback.print_exc(file=sys.stdout)
    #self.ser.close()//for renull
    print("not connect frk")


