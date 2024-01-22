from abc import abstractmethod
from threading import Thread
from time import sleep
from timeit import default_timer

from telegram import Bot
from telegram.error import RetryAfter, TimedOut, NetworkError
from telegram.ext import Updater, CommandHandler

from my_logger import logger
from utils import EventMessage


class EventQueue:
    def __init__(self):
        self.__queue = list()

    def post(self, t_id: str, cmd: str, data: list, delay: float = 0, s_id: str = ''):
        self.__queue.append(EventMessage(t_id=t_id, s_id=s_id, cmd=cmd,
                                         active_timer=default_timer() + delay, data=data))

    def get(self, t_id: str) -> list:
        base_timer = default_timer()
        ret = [r for r in self.__queue if r.t_id == t_id and r.active_timer <= base_timer]
        self.__queue = [r for r in self.__queue if r.t_id != t_id or r.active_timer > base_timer]
        return ret

    def is_empty(self, t_id: str) -> bool:
        return len([r for r in self.__queue if r.t_id == t_id]) == 0

    def dbg_output(self):
        for r in self.__queue:
            logger.debug(f"{r}")


class Communication:

    def __init__(self, queue, config):
        self._c = config
        self._q = queue
        self._a = None

        self._break: bool = False
        self._conn = None

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def send_msg(self, msg):
        pass

    @abstractmethod
    def event_processing(self):
        pass

    @property
    @abstractmethod
    def e_id(self) -> str:
        pass

    def _w_msg(self, f: str, p: str) -> str:
        return f"{self.__class__.__name__}.{f} > {p}"

    def initial(self, parent):
        self._a = parent.accounts

    def _order(self, cmd_line: list):
        """
        /o a_id m/a/i sell code qty money/price
        """
        a_id = ''
        data = list()
        try:
            for i, arg in enumerate(cmd_line):
                match i:
                    case 0:
                        try:
                            a_id = f"{int(arg):02d}"
                        except ValueError:
                            a_id = arg
                        if a_id not in self._a:
                            raise Exception(f"account id not register; {a_id}")
                        data.append(a_id)
                    case 1:
                        if arg not in ('m', 'a', 'i'):
                            raise Exception(self._w_msg('_order', f"order [m/a/i] error; {arg}"))
                        data.append(arg)
                    case 2:
                        if arg not in ('sell', 'buy'):
                            raise Exception(self._w_msg('_order', f"order [sell/buy] error; {arg}"))
                        data.append(arg)
                    case _:
                        data.append(arg)
        except (ValueError, Exception) as e:
            self.send_msg(self._w_msg('_order', f"Exception; {e}"))
            logger.warning(self._w_msg('_order', f"Exception; {e}"))
            return

        logger.debug(f"queue msg; {a_id, 'order', data}")
        self._send_cmd(a_id, 'order', data, s_id=self.e_id)

    def _modify(self, cmd_line: list):
        """
        /m a_id code qty price order_no
        """
        a_id = ''
        data = list()
        try:
            for i, arg in enumerate(cmd_line):
                match i:
                    case 0:
                        try:
                            a_id = f"{int(arg):02d}"
                        except ValueError:
                            a_id = arg
                        if a_id not in self._a:
                            raise Exception(f"account id not register; {a_id}")
                        data.append(a_id)
                    case _:
                        data.append(arg)
        except (ValueError, Exception) as e:
            self.send_msg(self._w_msg('_modify', f"Exception; {e}"))
            logger.warning(self._w_msg('_modify', f"Exception; {e}"))
            return

        logger.debug(f"queue msg; {a_id, 'modify', data}")
        self._send_cmd(a_id, 'modify', data, s_id=self.e_id)

    def _cancel(self, cmd_line: list):
        """
        /c a_id code qty order_no
        """
        a_id = ''
        data = list()
        try:
            for i, arg in enumerate(cmd_line):
                match i:
                    case 0:
                        try:
                            a_id = f"{int(arg):02d}"
                        except ValueError:
                            a_id = arg
                        if a_id not in self._a:
                            raise Exception(f"account id not register; {a_id}")
                        data.append(a_id)
                    case _:
                        data.append(arg)
        except (ValueError, Exception) as e:
            self.send_msg(self._w_msg('_cancel', f"Exception; {e}"))
            logger.warning(self._w_msg('_cancel', f"Exception; {e}"))
            return

        logger.debug(f"queue msg; {a_id, 'cancel', data}")
        self._send_cmd(a_id, 'cancel', data, s_id=self.e_id)

    def _timer_order(self, cmd_line: list):
        """
        /t 1145 a_id m/a/i sell code qty money/price
        """
        a_id = ''
        data = list()
        try:
            for i, arg in enumerate(cmd_line):
                match i:
                    case 0:
                        try:
                            data.append(f"{int(arg):04d}")
                        except ValueError:
                            raise Exception(self._w_msg('_timer_order', f"error time setting; {arg}"))
                    case 1:
                        try:
                            a_id = f"{int(arg):02d}"
                        except ValueError:
                            a_id = arg
                        if a_id not in self._a:
                            raise Exception(f"account id not register; {a_id}")
                        data.append(a_id)
                    case 2:
                        if arg not in ('m', 'a', 'i'):
                            raise Exception(self._w_msg('_order', f"order [m/a/i] error; {arg}"))
                        data.append(arg)
                    case 3:
                        if arg not in ('sell', 'buy'):
                            raise Exception(self._w_msg('_order', f"order [sell/buy] error; {arg}"))
                        data.append(arg)
                    case _:
                        data.append(arg)
        except (ValueError, Exception) as e:
            self.send_msg(self._w_msg('_timer_order', f"Exception; {e}"))
            logger.warning(self._w_msg('_timer_order', f"Exception; {e}"))
            return

        logger.debug(f"queue msg; {a_id, 'timer', data}")
        self._send_cmd(a_id, 'timer', data, s_id=self.e_id)

    def _lm(self, cmd_line: list):
        """
        /lm acc_id ; 미체결 리스트 반환
        """
        if not cmd_line:
            self.send_msg(f"using; /lm acc_id")
            return
        try:
            a_id = f"{int(cmd_line[0]):02d}"
        except ValueError:
            a_id = cmd_line[0]
        if a_id not in self._a:
            self.send_msg(self._w_msg('_lm', f"error id; {a_id}"))
            logger.warning(self._w_msg('_lm', f"error id; {a_id}"))
            return

        logger.debug(f"queue msg; {a_id, 'lm'}")
        self._send_cmd(a_id, 'lm', list(), s_id=self.e_id)

    def _ls(self, cmd_line: list):
        """
        /ls [acc_id] ; 접속된 a_id or a_id 의 보유종목 리스트
        """
        if not cmd_line:
            self.send_msg(f"register acc id; {', '.join(self._a.keys())}")
            return

        data = list()
        try:
            for arg in cmd_line:
                try:
                    a_id = f"{int(arg):02d}"
                except ValueError:
                    a_id = arg
                if a_id not in self._a:
                    raise Exception(f"account id not register; {a_id}")
                data.append(a_id)
        except (ValueError, Exception) as e:
            self.send_msg(self._w_msg('_timer_order', f"Exception; {e}"))
            logger.warning(self._w_msg('_timer_order', f"Exception; {e}"))
            return

        for i, a_id in enumerate(data):
            self._send_cmd(a_id, 'ls', list(), delay=i * self._cmd_delay, s_id=self.e_id)

    @property
    def _cmd_delay(self) -> float:
        return self._c.row['telegram']['cmd_delay']

    def _help(self):
        msg_ = f"/o a_id [m/a/i] [sell/buy] code qty money/price\n" \
               f"/m a_id [sell/buy] code qty price org_ord_no\n" \
               f"/c a_id [sell/buy] code qty org_ord_no\n" \
               f"/ls [a_id]\n" \
               f"/lm a_id\n" \
               f"/shutdown"
        self.send_msg(f"{msg_}")

    def _shutdown(self):
        self._send_cmd(self._c.e_id_main, 'shutdown', list(), s_id=self.e_id)
        self._break = True

    @property
    def is_break(self) -> bool:
        return self._break

    def _send_cmd(self, t_id: str, cmd: str, data: list, delay: float = 0, s_id: str = ''):
        self._q.post(t_id, cmd, data, delay, s_id)


class Telegram(Communication):
    def __init__(self, queue, config):
        super().__init__(queue=queue, config=config)
        if not self.enable:
            logger.warning(f"****************************")
            logger.warning(f"  !!! Telegram Disable !!!  ")
            logger.warning(f"****************************")
            return

        self.__t = Thread(target=self.__run)
        self.__loop = False
        try:
            self._conn = self._c.telegram_info()
        except Exception as e:
            logger.warning(f"{e}")
            return

        self.__bot = Bot(self._conn['token'])
        self.__updater = Updater(token=self._conn['token'], use_context=True)
        self.__dispatcher = self.__updater.dispatcher

    @property
    def e_id(self) -> str:
        return self._c.e_id_telegram

    @property
    def timeout(self) -> float:
        return self._c.row['telegram']['timeout']

    @property
    def enable(self) -> bool:
        return self._c.row['telegram']['enable'] == 1

    def __thread_start(self):
        if self.__t is None:
            return
        self.__loop = True
        self.__t.start()

    def __thread_stop(self):
        if self.__t is None:
            return
        self.__loop = False
        self.__t.join()

    def __run(self):
        logger.info(f"{self.__class__.__name__} thread start...")
        while self.__loop:
            try:
                self.__updater.start_polling(timeout=self.timeout)
            except (RetryAfter, TimedOut, NetworkError) as ex:
                logger.critical(self._w_msg('__run', f"{ex}"))

            self.event_processing()

            sleep(self._c.loop_sleep)
        logger.info(f"{self.__class__.__name__} thread stop...")

    def __shutdown(self, _, _context):
        self._shutdown()

    def __test_match(self, _, _context):
        self._send_cmd(self._c.e_id_main, 'test.match', list(), s_id=self.e_id)

    def __test_store(self, _, _context):
        self._send_cmd(self._c.e_id_main, 'test.store', list(), s_id=self.e_id)

    def __help(self, _, _context):
        self._help()

    def __quit(self, _, _context):
        self._break = True
        if self.__class__.__name__ == 'Telegram':
            self.send_msg('테스트용 메시지 처리를 종료합니다.')
        else:
            self.send_msg('!!! exit program !!!')

    def __ls(self, _, context):
        self._ls(context.args)

    def __lm(self, _, context):
        self._lm(context.args)

    def __order(self, _, context):
        self._order(context.args)

    def __modify(self, _, context):
        self._modify(context.args)

    def __cancel(self, _, context):
        self._cancel(context.args)

    def __timer_order(self, _, context):
        self._timer_order(context.args)

    def init_handler(self):
        if self._conn is None:
            return
        self.__updater.start_polling(timeout=self.timeout, drop_pending_updates=True)

        # target id; account
        self.__dispatcher.add_handler(CommandHandler('o', self.__order))
        self.__dispatcher.add_handler(CommandHandler('m', self.__modify))
        self.__dispatcher.add_handler(CommandHandler('c', self.__cancel))
        self.__dispatcher.add_handler(CommandHandler('t', self.__timer_order))

        self.__dispatcher.add_handler(CommandHandler('lm', self.__lm))
        self.__dispatcher.add_handler(CommandHandler('ls', self.__ls))

        self.__dispatcher.add_handler(CommandHandler('h', self.__help))
        self.__dispatcher.add_handler(CommandHandler('help', self.__help))

        self.__dispatcher.add_handler(CommandHandler('shutdown', self.__shutdown))

        # note; test 에서만 사용 ====================================================
        self.__dispatcher.add_handler(CommandHandler('test_store', self.__test_store))
        self.__dispatcher.add_handler(CommandHandler('test_m', self.__test_match))
        self.__dispatcher.add_handler(CommandHandler('quit', self.__quit))

        self.__thread_start()

    def polling(self, timeout: float = 0.1):
        if self._conn is None:
            return
        try:
            self.__updater.start_polling(timeout=timeout)
        except (RetryAfter, TimedOut, NetworkError) as ex:
            logger.critical(self._w_msg('polling', f"Exception; {ex}"))

    def stop(self):
        if self._conn is None:
            return
        self.__thread_stop()
        self.__updater.stop()
        self._conn = None

    def send_msg(self, msg):
        if self._conn is None:
            return
        self.__send_msg(msg)

    def __send_msg(self, msg=''):
        try:
            self.__bot.sendMessage(chat_id=self._conn['id'], text=msg)
        except (RetryAfter, TimedOut, NetworkError) as ex:
            logger.critical(self._w_msg('__send_msg', f"Exception; {ex}, msg; {msg}"))
            sleep(self.timeout)

    def event_processing(self):
        for e in self._q.get(self.e_id):
            match e.cmd:
                case 'msg':
                    self.send_msg(e.data[0])
                case 'ts_msg':
                    pass
                case 'r_lm':
                    logger.debug(f"return lm cmd")
                    msg_ = f"{e.data[0]}, a_id; {e.data[1]}, a_type; {e.data[2]}, len; {e.data[3]}"
                    self.send_msg(f"{msg_}")
                    logger.debug(f"{msg_}")
                    for r in e.data[4:]:
                        self.send_msg(f"{r}")
                        logger.debug(f"{r}")
                case 'r_ls':
                    self.__event_return_ls(e)
                case _:
                    logger.warning(self._w_msg('_event_processing',
                                               f"not match cmd; {e.cmd}"))

    def __event_return_ls(self, e):
        logger.debug(f"return ls cmd")
        msg_ = f"{e.data[0]}, a_id; {e.data[1]}, a_type; {e.data[2]}, len; {e.data[3]}"
        self.send_msg(f"{msg_}")
        logger.debug(f"{msg_}")
        for r in e.data[4:]:
            self.send_msg(f"{r}")
            logger.debug(f"{r}")

