import configparser
from pathlib import Path
import sys
from configparser import ConfigParser
from datetime import datetime
from arc4 import ARC4


class JAMSBot:
    def __init__(self, config_file: Path = None, file_logging: bool = False, init: bool = True):
        self.is_success = False
        self.__context_manager = False
        self.warnings = 0
        self.file_logging = file_logging
        if init:
            self.__config = self.__open_config(config_file)
            if self.file_logging:
                self.log_file = Path('process.logs')
                with open(self.log_file, mode='w+', encoding='utf-8') as f:
                    f.write(f'{self.__date_to_log()}\t:: START ::\n')
            print(f'{self.__date_to_log()}\t:: START ::')

    def __open_config(self, file: Path):
        if not file.exists():
            self.failed(f'Nie istnieje plik: {file}!')
        self.__config = ConfigParser(comment_prefixes=';')
        # self.__config.read(file)
        with open(file, mode='r', encoding='utf-8') as f_obj:
            self.__config.read_file(f_obj)
            return self.__config

    def get_sections(self) -> list[str]:
        return self.__config.sections()

    def list_section_vars(self, section: str) -> list[str]:
        return self.__config.options(section)

    def get_text_var(self, section: str, var: str) -> str:
        try:
            return self.__config.get(section, var)
        except configparser.NoOptionError:
            self.failed(f'Nie odnaleziono parametru: "{var}" w sekcji: {section}')
        except configparser.NoSectionError:
            self.failed(f'Nie odnaleziono sekcji {section}')

    def get_int_var(self, section: str, var: str) -> int:
        try:
            return self.__config.getint(section, var)
        except configparser.NoOptionError:
            self.failed(f'Nie odnaleziono parametru: "{var}" w sekcji: {section}')
        except configparser.NoSectionError:
            self.failed(f'Nie odnaleziono sekcji {section}')

    def get_bool_var(self, section: str, var: str) -> bool:
        try:
            return self.__config.getboolean(section, var)
        except configparser.NoOptionError:
            self.failed(f'Nie odnaleziono parametru: "{var}" w sekcji: {section}')
        except configparser.NoSectionError:
            self.failed(f'Nie odnaleziono sekcji {section}')

    def set_var_value(self, section: str, var: str, value: str) -> None:
        return self.__config.set(section, var, value)

    def get_creds(self, section_name: str):
        self.debug(f'Pobieram dane użytkownika z sekcji: {section_name}')
        try:
            _login = self.__config.get(section_name, 'user')
        except configparser.NoOptionError:
            self.failed(f'Nie odnaleziono parametru: "user" w sekcji: {section_name}')
        except configparser.NoSectionError:
            self.failed(f'Nie odnaleziono sekcji {section_name}')
        try:
            _hexpwd = self.__config.get(section_name, 'pwd')
        except configparser.NoOptionError:
            self.failed(f'Nie odnaleziono parametru: "pwd" w sekcji: {section_name}')
        except configparser.NoSectionError:
            self.failed(f'Nie odnaleziono sekcji {section_name}')
        try:
            _key = self.__config.get(section_name, 'token')
        except configparser.NoOptionError:
            self.failed(f'Nie odnaleziono parametru: "token" w sekcji: {section_name}')
        except configparser.NoSectionError:
            self.failed(f'Nie odnaleziono sekcji {section_name}')
        try:
            _g_key = self.__config.get('MAIN', 'GLOBAL')
        except configparser.NoOptionError:
            self.failed(f'Nie odnaleziono parametru: "GLOBAL" w sekcji: MAIN')
        _ = ARC4(_g_key.encode('utf-8')).decrypt(bytes.fromhex(_key))
        _enc_key = ''
        i = 0
        while i < len(_):
            _enc_key += chr(_[i])
            i += 1
        _b_pwd = ARC4(_enc_key.encode('utf-8')).decrypt(bytes.fromhex(_hexpwd))
        i = 0
        _pwd = ''
        while i < len(_b_pwd):
            _pwd += chr(_b_pwd[i])
            i += 1
        return _login, _pwd

    def __date_to_log(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def info(self, msg):
        if self.file_logging:
            with open(self.log_file, mode='a', encoding='utf-8') as f:
                f.write(f'{self.__date_to_log()}\t:: INFO ::\t{msg}\n')
        print(f'{self.__date_to_log()}\t:: INFO ::\t{msg}')

    def debug(self, msg):
        if self.file_logging:
            with open(self.log_file, mode='a', encoding='utf-8') as f:
                f.write(f'{self.__date_to_log()}\t:: DEBUG ::\t{msg}\n')
        print(f'{self.__date_to_log()}\t:: DEBUG ::\t{msg}')

    def warning(self, msg):
        self.warnings += 1
        if self.file_logging:
            with open(self.log_file, mode='a', encoding='utf-8') as f:
                f.write(f'{self.__date_to_log()}\t:: WARNING ::\t{msg}\n')
        print(f'{self.__date_to_log()}\t:: WARNING ::\t{msg}')

    def failed(self, msg, end: bool = True):
        self.is_success = False
        if self.file_logging:
            with open(self.log_file, mode='a', encoding='utf-8') as f:
                f.write(f'{self.__date_to_log()}\t:: FAILED ::\t{msg}\n')
        print(f'{self.__date_to_log()}\t:: FAILED ::\t{msg}')
        if end:
            if self.__context_manager:
                self.__exit__(None, None, None)
            sys.exit(1)

    def success(self, msg, end: bool = True):
        self.is_success = True
        if self.file_logging:
            with open(self.log_file, mode='a', encoding='utf-8') as f:
                f.write(f'{self.__date_to_log()}\t:: SUCCESS ::\t{msg}\n')
        print(f'{self.__date_to_log()}\t:: SUCCESS ::\t{msg}')
        if end:
            if self.__context_manager:
                self.__exit__(None, None, None)
            sys.exit(0)

    def __enter__(self):
        self.__context_manager = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type or exc_val:
            if exc_type != SystemExit:
                self.debug(f'Błąd wychwycony przez Context_Manager: Typ: {exc_type}, treść: {exc_val}')
                self.failed('Robot napotkał błąd, którego nie potrafił obsłużyć!', True)
        if self.is_success:
            sys.exit(0)
        else:
            sys.exit(1)
