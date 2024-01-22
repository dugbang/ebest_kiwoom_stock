import csv
import json
import logging.config
from datetime import date
from os import path, mkdir, remove, listdir

import yaml

import my_logger


class ConfigDir:
    ROOT: str = 'kiwoom'

    @staticmethod
    def validate(root: str = 'kiwoom'):
        if path.exists(f"{root}") is False:
            raise Exception(f"not exist; {root}")
        ConfigDir.ROOT = root
        for d in ('logs', 'cfg'):
            ConfigDir.make_dir(f"{d}")
        ConfigDir.__set_logger_output()

    @staticmethod
    def get_path(name: str) -> str:
        return f"{ConfigDir.ROOT}/{name}"

    @staticmethod
    def get_account_files(demo=True, sub='account', ext_t='.yaml') -> list:
        file = 'demo.' if demo is True else 'account_'
        result = list()
        for filename in listdir(f"{ConfigDir.ROOT}/{sub}"):
            if filename[0] == '~':
                continue
            ext = path.splitext(filename)[-1]
            if ext == ext_t:
                if filename.find(file) != -1:
                    result.append(filename)
        return result

    @staticmethod
    def backup(filename: str, backup_dir: str = "backup"):
        from shutil import copy

        ConfigDir.__make_dir_using_today(backup_dir)
        copy(f"{ConfigDir.ROOT}/{filename}",
             f"{ConfigDir.ROOT}/{backup_dir}/{date.today().strftime('%Y/%m')}/{date.today().strftime('%Y%m%d')}.{filename}")

    @staticmethod
    def __make_dir_using_today(base_dir: str = 'backup'):
        year = date.today().strftime('%Y')
        if path.isdir(f"{ConfigDir.ROOT}/{base_dir}/{year}") is False:
            mkdir(f"{ConfigDir.ROOT}/{base_dir}/{year}")
        if path.isdir(f"{ConfigDir.ROOT}/{base_dir}/{date.today().strftime('%Y/%m')}") is False:
            mkdir(f"{ConfigDir.ROOT}/{base_dir}/{date.today().strftime('%Y/%m')}")

    @staticmethod
    def load_json(filename, sub='cfg', encoding='UTF-8') -> dict:
        with open(f"{ConfigDir.ROOT}/{sub}/{filename}", 'rt', encoding=encoding) as f:
            result = json.load(f)
        return result

    @staticmethod
    def load_yaml(filename, sub='cfg', encoding='utf-8'):
        with open(f"{ConfigDir.ROOT}/{sub}/{filename}", 'r', encoding=encoding) as f:
            result = yaml.load(f, Loader=yaml.FullLoader)
        return result

    @staticmethod
    def save_json(filename, json_, sub='cfg', encoding='UTF-8'):
        with open(f"{ConfigDir.ROOT}/{sub}/{filename}", 'wt', encoding=encoding) as f:
            json.dump(json_, f, ensure_ascii=False, indent=4)

    @staticmethod
    def load_csv(filename, sub='cfg', encoding='utf-8', delimiter=','):
        with open(f"{ConfigDir.ROOT}/{sub}/{filename}", 'r', encoding=encoding, newline='') as f:
            result = list(csv.reader(f, skipinitialspace=True, delimiter=delimiter))
        return result

    @staticmethod
    def save_csv(filename, records, sub='cfg', encoding='UTF-8', delimiter=','):
        with open(f"{ConfigDir.ROOT}/{sub}/{filename}", 'w', encoding=encoding, newline='') as f:
            wr = csv.writer(f, delimiter=delimiter)
            for r in records:
                wr.writerow(r)

    @staticmethod
    def exist(name: str) -> bool:
        return True if path.exists(f"{ConfigDir.ROOT}/{name}") else False

    @staticmethod
    def make_file(name: str):
        with open(f"{ConfigDir.ROOT}/{name}", 'wb') as f:
            pass

    @staticmethod
    def make_dir(name: str):
        try:
            mkdir(f"{ConfigDir.ROOT}/{name}")
        except (PermissionError, FileExistsError, FileNotFoundError):
            pass

    @staticmethod
    def remove(name: str):
        try:
            remove(f"{ConfigDir.ROOT}/{name}")
        except (PermissionError, FileExistsError, FileNotFoundError):
            pass

    @staticmethod
    def __set_logger_output():
        with open(f"logging.json", 'rt', encoding='UTF-8') as f:
            result = json.load(f)

        result['handlers']['file']['filename'] = f"{ConfigDir.ROOT}/logs/log.log"
        logging.config.dictConfig(result)

        my_logger.logger = logging.getLogger('file')
        # logger.setLevel(logging.CRITICAL)
        # logger.setLevel(logging.ERROR)
        # logger.setLevel(logging.WARNING)
        # logger.setLevel(logging.INFO)
        my_logger.logger.setLevel(logging.DEBUG)
