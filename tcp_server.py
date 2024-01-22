import json
import socket
from threading import Thread
from time import sleep

from communication import Communication, EventQueue, EventMessage
from configuration import Configuration
from my_logger import logger


class _Client(Communication):
    def __init__(self, conn, count, server):
        super().__init__(queue=server.queue, config=server.config)

        self.__tcp = server
        self.__conn = conn
        self.__number = count

        self.__disconnecting = True

    @property
    def e_id(self) -> str:
        return f"tcp_c{self.__number}"

    @property
    def connected(self) -> bool:
        return not self.__disconnecting

    def event_processing(self):
        for e in self._q.get(self.e_id):
            self.__send_json(json.dumps(e, default=lambda x: x.__dict__))
            logger.debug(f"_Client.event_processing.__send_json; {e.s_id} > {e.t_id}")

    def __send_json(self, json_data):
        if self.connected is False:
            return
        self.__conn.sendall(json_data.encode('utf-8'))

    def start(self):
        t_ = Thread(target=self.__receiver)
        t_.start()
        self.__disconnecting = False

        records = list()
        for k in self._a:
            records.append([self._a[k].e_id, self._a[k].a_type, self._a[k].a_no])
        e = EventMessage(t_id=self.e_id, s_id='', cmd='a_ls', active_timer=0, data=records)
        self.__send_json(json.dumps(e, default=lambda x: x.__dict__))

    def __receiver(self):
        while True:
            try:
                data = self.__conn.recv(self.__tcp.recv_size)
            except Exception as e:
                logger.warning(self._w_msg('__receiver', f"Exception; {e}"))
                break
            if not data:
                break
            receive_data = data.decode().strip()

            cmd_line = receive_data.split(' ')
            logger.debug(f"tcp server; {cmd_line}")
            match cmd_line[0]:
                case '/ls':
                    self._ls(cmd_line[1:])
                case '/lm':
                    self._lm(cmd_line[1:])
                case '/o':
                    self._order(cmd_line[1:])
                case '/m':
                    self._modify(cmd_line[1:])
                case '/c':
                    self._cancel(cmd_line[1:])
                case '/t':
                    self._timer_order(cmd_line[1:])
                case '/shutdown':
                    self._shutdown()
                case _:
                    e = EventMessage(t_id=self.e_id, s_id='', cmd='msg', active_timer=0,
                                     data=['not define cmd', ])
                    self.__send_json(json.dumps(e, default=lambda x: x.__dict__))
                    logger.warning(self._w_msg('__receiver', f"cmd not define; {cmd_line[0]}"))
        self.__disconnecting = True

    def send_msg(self, msg):
        e = EventMessage(t_id=self.e_id, s_id='', cmd='msg', active_timer=0,
                         data=[f"{msg}", ])
        self.__send_json(json.dumps(e, default=lambda x: x.__dict__))

    def stop(self):
        if self.connected is False:
            return
        e = EventMessage(t_id=self.e_id, s_id='', cmd='exit', active_timer=0, data=list())
        self.__send_json(json.dumps(e, default=lambda x: x.__dict__))
        logger.info(f"!!! disconnecting client {self.e_id} !!!")
        sleep(self.__tcp.timeout)

        self.__conn.close()
        self.__conn = None


class TcpServer:
    """
    기본적으로 telegram 의 동작과 같다. 다만 telegram 은 사용자 입력을 처리하지만
    tcp server 는 client 로 부터 입력 받는 정보를 처리한다.
    이때 입력 받는 정보는 telegram 과 같고 출력하는 정보는 json 으로 변환하여 client 에 전송한다.
    """
    def __init__(self, queue, config):
        self.__q = queue
        self.__c = config
        self.__a = None

        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__server.settimeout(self.timeout)  # timeout for listening
        self.__server.bind((self.address, self.port))
        self.__server.listen(self.limit_listen)

        self.__loop = True
        self.__t: Thread = Thread(target=self.__run)
        self.__t.start()

        self.__clients: [_Client] = list()
        self.__client_counter: int = 0

    @property
    def e_id(self) -> str:
        return self.__c.e_id_tcp_server

    @property
    def timeout(self) -> float:
        return self.__c.row['tcp_server']['timeout']

    @property
    def address(self) -> str:
        return self.__c.row['tcp_server']['addr']

    @property
    def port(self) -> int:
        return self.__c.row['tcp_server']['port']

    @property
    def limit_listen(self) -> int:
        return self.__c.row['tcp_server']['limit_listen']

    @property
    def recv_size(self) -> int:
        return self.__c.row['tcp_server']['recv_size']

    @property
    def config(self) -> Configuration:
        return self.__c

    @property
    def queue(self) -> EventQueue:
        return self.__q

    @property
    def accounts(self) -> dict:
        return self.__a

    def initial(self, parent):
        self.__a = parent.accounts

    def stop(self):
        self.__loop = False
        for c_ in self.__clients:
            if c_.connected:
                c_.stop()
        self.__t.join()

    def __run(self):
        while self.__loop:
            try:
                conn, addr = self.__server.accept()
            except socket.timeout:
                pass
            except Exception as e:
                logger.warning(f"{self.__class__.__name__}.__server.accept() >> {e}")
            else:
                c_ = _Client(conn=conn, count=self.__client_counter, server=self)
                c_.initial(self)
                c_.start()
                self.__client_counter += 1
                self.__clients.append(c_)
                logger.debug(f"Connected by: {c_.e_id}, ip info; {addr}")

            self.__client_event_processing()
            self.__event_processing()

    def __client_event_processing(self):
        try:
            self.__validate_client()
            for c_ in self.__clients:
                c_.event_processing()
        except Exception as e:
            logger.warning(f"{self.__class__.__name__}.__clients >> {e}")

    def __event_processing(self):
        for e in self.__q.get(self.e_id):
            match e.cmd:
                case 'exit':
                    for c_ in self.__clients:
                        self.__q.post(c_.e_id, 'exit', list())
                case 'ts_msg':
                    for c_ in self.__clients:
                        self.__q.post(c_.e_id, 'ts_msg', e.data, s_id=e.s_id)
                case _:
                    logger.warning(f"not match server cmd; {e.cmd}")

    def __validate_client(self):
        idx_ = list()
        for i, c_ in enumerate(self.__clients):
            if c_.connected is False:
                idx_.append(i)
        idx_.reverse()
        for i in idx_:
            logger.debug(f"remove client; {self.__clients[i].e_id}")
            del self.__clients[i]
