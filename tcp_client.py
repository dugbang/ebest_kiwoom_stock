import json
import socket
from threading import Thread
from time import sleep

from my_logger import logger
from utils import EventMessage


class TcpClient:
    def __init__(self, config, receive_event=None):
        self.__c = config

        self.__t = None
        self.__client = None
        self.__connected = False
        self.__receive_event = receive_event

    @property
    def __timeout(self) -> float:
        return self.__c.row['tcp_server']['timeout']

    @property
    def __address(self) -> str:
        return self.__c.row['tcp_server']['addr']

    @property
    def __port(self) -> int:
        return self.__c.row['tcp_server']['port']

    @property
    def __recv_size(self) -> int:
        return self.__c.row['tcp_server']['recv_size']

    @property
    def connected(self) -> bool:
        return self.__connected

    def start(self) -> bool:
        try:
            self.__client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__client.connect((self.__address, self.__port))
        except Exception as e:
            logger.error('=' * 82)
            logger.error(f"  {self.__class__.__name__} >> {e}")
            logger.error('=' * 82)
            return False

        self.__t = Thread(target=self.__receiver)
        self.__t.start()
        self.__connected = True
        logger.info(f"{self.__class__.__name__} >> server connected")
        sleep(self.__timeout)
        return True

    def send_cmd(self, cmd_str):
        if self.__connected is False:
            return
        self.__client.sendall(bytes(f"{cmd_str}", 'utf-8'))

    def join(self):
        if self.__connected is False:
            return
        self.__t.join()

    def __receiver(self):
        while True:
            try:
                receive_data = self.__client.recv(self.__recv_size)
            except Exception as e:
                logger.warning(f"{self.__class__.__name__}.__receiver >> {e}")
                break
            if not receive_data:
                break

            data = json.loads(receive_data)
            e = EventMessage(**data)
            if self.__receive_event:
                self.__receive_event(e)
            if e.cmd == 'exit':
                logger.info(f"receive msg; exit!!")
                break

        logger.info(f"{self.__class__.__name__} >> server disconnected")
        if self.__connected is True:
            self.__client.close()
        self.__connected = False

    def stop(self):
        if self.__connected is False:
            return
        self.__connected = True
        self.__client.close()
