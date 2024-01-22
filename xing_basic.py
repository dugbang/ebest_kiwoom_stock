#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
xing 에서 제공하는 API COM 버전을 파이썬에서 동작하도록 작성

# def get_XASession(name)
#* 세션을 담당하는 객체
#* 주로 로그인과 계좌 정보 관한 정보를 확인할 때 사용
# def get_XAReal(name, fp_rd=None)
#* 데이터를 담당하는 객체
#* 실시간으로 데이터를 전송 받을 때 사용
#* AdviseRealData / UnadviseRealData 를 사용하여 기능을 등록/해제
# def get_XAQuery(name, fp_rd=None, fp_rm=None, cnt_per_sec=1):
#* 주문을 담당하는 객체
#* 하나의 문의를 보내면 그것에 대한 응답을 받을 때 사용

*참고자료*
# http://dolazy.com/xe/index.php?document_srl=1950206&mid=just_married
#* 첨부파일; 파이썬을 이용한 트레이딩 시스템.pdf
# http://weezzle.net/m/post/3288
"""
from threading import Thread
from time import sleep
from timeit import default_timer

import win32com.client

from pythoncom import PumpWaitingMessages

from my_logger import logger


def real_event_process(count=1000):
    for _ in range(count):
        PumpWaitingMessages()


class XASessionEvents(object):
    def __init__(self):
        self.__addr = ''
        self.__event = False
        self.__login_state = False

    def initial(self, addr):
        self.__addr = addr

    @property
    def login_state(self):
        return self.__login_state

    def OnLogin(self, szCode, szMsg):
        """
        서버와의 로그인이 끝나면 발생합니다.
        """
        if szCode == '0000':
            self.__login_state = True
            logger.info(f"login addr; {self.__addr}")
        else:
            self.__login_state = False
            logger.critical(f"{szCode}:{szMsg}")
        self.__event = True

    def OnLogout(self, *args):
        """
        사용하지않습니다
        """
        logger.info(f"OnLogout; {args}")
        self.__event = True

    def OnDisconnect(self, *args):
        """
        서버와의 연결이 끊어졌을때 발생합니다.
            인터넷망이 불안정하거나 기타 다른 이유로 연결이 끊길 때
            OS가 발생시키는 소켓 끊김 이벤트를 그대로 받아 고객 프로그램으로 전달하는 것입니다.

            참고로, 일반적으로 24시간 접속 유지를 해야 하는 경우
                1. t0167(서버시간 조회) TR을 주기적으로 조회하여 이전 시간과 비교하거나
                2. IJ_ (지수) TR 등을 이용하여 시간을 가져와서 비교하거나 하는 작업을 넣어
            접속 끊김을 확인하는 것도 한 방법입니다.
        """
        logger.critical(f"OnDisconnect; {args}")
        self.__event = True

    def wait_receive_message(self):
        while self.__event is False:
            sleep(0.01)  # 10 ms
            PumpWaitingMessages()


class XARealEvents(object):
    def __init__(self):
        self.__tr_name = ''
        self.__receive_real_data = None

        self.__event = False
        self.__exit_loop = False
        self.__t = None
        self.__started = False

    def initial(self, name, handler):
        self.__tr_name = name
        self.__receive_real_data = handler

    @property
    def tr_name(self):
        return self.__tr_name

    def stop(self):
        self.UnadviseRealData()
        self.__exit_loop = True

    def add_field(self, name, code):
        self.SetFieldData("InBlock", name, code)
        self.AdviseRealData()

    def remove(self, code):
        """
        note; 실행할 경우 가끔씩 APPCRASH(XingAPI.dll) 발생.
          Win7, DDR3 에서 발생, Win10, DDR4 에서는 발견안됨. >> 아무것도 하지 않는 것으로 처리.
        """
        # self.UnadviseRealDataWithKey(code)
        pass

    def start(self):
        if self.__started is True:
            return
        self.__started = True
        self.__exit_loop = False

        self.__t = Thread(target=self.__run)
        self.__t.start()

    def join(self):
        if self.__started is True:
            self.__t.join()

    def __run(self):
        while self.__exit_loop is False:
            self.__event = False
            self.__wait_receive_message()

    def __wait_receive_message(self):
        while self.__event is False:
            # fixed; PumpWaitingMessages()   # =>> main process 에서 호출하여야 함.
            if self.__exit_loop is True:
                break
            sleep(0.01)  # 10 ms

    def OnReceiveRealData(self, szTrCode):
        """
        서버로부터 데이터를 수신했을때의 이벤트
        problem; 스레드 이용시 호출되지 않음...ㅠ =>> real_event_process
        """
        if self.__receive_real_data is not None:
            self.__receive_real_data(self, szTrCode)
        self.__event = True


class XAQueryEvents3:
    def __init__(self):
        self.__tr_name: str = ''
        self.__interval = 1
        self.__period_limit = None

        self.__receive_data = None
        self.__receive_msg = None

        self.__event_msg = False
        self.__event_data = False
        self.__interval_time = default_timer()

    def initial(self, tr_name, receive_data, receive_msg, interval, period_limit):
        self.__tr_name = tr_name
        self.__receive_data = receive_data
        self.__receive_msg = receive_msg
        self.__interval = interval
        self.__period_limit = PeriodLimit(period_limit)

    @property
    def tr_name(self) -> str:
        return self.__tr_name

    def wait_receive_message(self):
        while self.__event_msg is False:
            PumpWaitingMessages()
            sleep(0.01)  # 10 ms

    def OnReceiveData(self, szTrCode):
        """ 서버로부터 데이터를 수신했을때의 이벤트
            Request 결과값이 성공일 때만 발생합니다
        """
        if self.__receive_data is not None:
            self.__receive_data(self, szTrCode)
        self.__event_data = True

    def OnReceiveMessage(self, bIsSystemError, szMessageCode, szMessage):
        """ 서버로부터 메시지를 수신했을때의 이벤트
            무조건 발생하며 Request 결과에 대한 성공 여부 정보를 수신
        """
        if self.__receive_msg is not None:
            self.__receive_msg(self, bIsSystemError, szMessageCode, szMessage)
        self.__event_msg = True

    def tRequest(self, bNext):
        """bNext : 다음조회일 경우는 TRUE True
                   그렇지 않으면 FALSE False
        """
        self.__event_msg = False
        self.__event_data = False
        while self.__interval_time > default_timer():
            PumpWaitingMessages()
            sleep(0.01)
        self.__period_limit.waiting(self.__tr_name)
        self.__interval_time = default_timer() + self.__interval
        return self.Request(bNext)


class PeriodLimit:
    def __init__(self, period_limit):
        self.__using = False if period_limit is None or len(period_limit) != 2 else True
        if self.__using is False:
            return
        self.__period = period_limit[0]
        self.__limit_len = period_limit[1]
        self.__time_list = list()

    def waiting(self, msg):
        if self.__using is False:
            return
        self.__time_list.append(default_timer())
        self.__time_list = [r for r in self.__time_list if r > default_timer() - self.__period]
        while len(self.__time_list) >= self.__limit_len:
            delay = self.__period - (default_timer() - self.__time_list[0])
            logger.critical(f"x" * 80)
            logger.critical(f"  [TR PERIOD LIMIT({msg})] {self.__class__.__name__}"
                            f" waiting; {delay:.1f} sec, {self.__period, self.__limit_len}")
            logger.critical(f"x" * 80)
            wait_time = delay + default_timer()
            while wait_time > default_timer():
                PumpWaitingMessages()
                sleep(0.01)
            self.__time_list = [r for r in self.__time_list if r > default_timer() - self.__period]


# ===============================================================================================
# ===============================================================================================
# ===============================================================================================


def XASession():
    return win32com.client.DispatchWithEvents("XA_Session.XASession", XASessionEvents)


def XAReal(tr_name, handler):
    com = win32com.client.DispatchWithEvents("XA_DataSet.XAReal", XARealEvents)
    com.initial(tr_name, handler)
    return com


def XAQuery3(tr_name, receive_data, receive_msg, interval, period_limit):
    com = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", XAQueryEvents3)
    com.initial(tr_name, receive_data, receive_msg, interval, period_limit)
    return com
