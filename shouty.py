from contextlib import contextmanager
from enum import IntEnum
import atexit
import ctypes.util
from ctypes import CDLL, c_int, c_char_p, c_void_p, c_size_t


class ShoutErr(IntEnum):
    SUCCESS = 0
    INSANE = -1
    NOCONNECT = -2
    NOLOGIN = -3
    SOCKET = -4
    MALLOC = -5
    METADATA = -6
    CONNECTED = -7
    UNCONNECTED = -8
    UNSUPPORTED = -9
    BUSY = 10
    NOTLS = 11
    TLSBADCERT = -12
    RETRY = -13


class Format(IntEnum):
    OGG = 0
    MP3 = 1
    WEBM = 2
    WEBMAUDIO = 3


class Protocol(IntEnum):
    HTTP = 0
    XAUDIOCAST = 1
    ICY = 2
    ROARAUDIO = 3


so_file = ctypes.util.find_library('shout')

if not so_file:
    raise Exception('Library shout not found')

lib = CDLL(so_file)
lib.shout_init()
atexit.register(lib.shout_shutdown)


def check_error_code(f):
    def decorated(*args, **kwargs):
        err = f(*args, **kwargs)

        if err != ShoutErr.SUCCESS:
            raise Exception('Failed {}, error: {}'
                            .format(f.__name__, ShoutErr(err).name))
    return decorated


class Connection:
    def __init__(self, **kwargs):

        lib.shout_new.restype = c_void_p
        self.obj = lib.shout_new()
        if not self.obj:
            raise Exception('Memory error')

        self.set_params(**kwargs)

        lib.shout_open.argtypes = [c_void_p]
        lib.shout_send.argtypes = [c_void_p, c_char_p, c_size_t]
        lib.shout_sync.argtypes = [c_void_p]
        lib.shout_close.argtypes = [c_void_p]
        lib.shout_free.argtypes = [c_void_p]

    def set_params(self,
                   host='localhost', port=8000,
                   user='source', password='',
                   protocol=Protocol.HTTP,
                   format=Format.OGG,
                   mount='/shouty',
                   dumpfile=None, agent=None,
                   public=0,
                   name=None, url=None, genre=None, description=None):

        self.set_int(lib.shout_set_port, port)
        self.set_str(lib.shout_set_host, host)

        self.set_str(lib.shout_set_user, user)
        self.set_str(lib.shout_set_password, password)

        self.set_int(lib.shout_set_protocol, protocol)
        self.set_int(lib.shout_set_format, format)
        self.set_str(lib.shout_set_mount, mount)

        self.set_optional_str(lib.shout_set_dumpfile, dumpfile)
        self.set_optional_str(lib.shout_set_agent, agent)

        self.set_int(lib.shout_set_public, public)

        self.set_optional_str(lib.shout_set_name, name)
        self.set_optional_str(lib.shout_set_url, url)
        self.set_optional_str(lib.shout_set_genre, genre)
        self.set_optional_str(lib.shout_set_description, description)

        # TODO: audio_info

    @check_error_code
    def set_str(self, f, s):
        f.argtypes = [c_void_p, c_char_p]
        return f(self.obj, s.encode('ascii'))

    @check_error_code
    def set_int(self, f, n):
        f.argtypes = [c_void_p, c_int]
        return f(self.obj, n)

    def set_optional_str(self, f, s):
        if s:
            self.set_str(f, s)

    @check_error_code
    def open(self):
        return lib.shout_open(self.obj)

    @check_error_code
    def send(self, chunk):
        return lib.shout_send(self.obj, chunk, len(chunk))

    @check_error_code
    def sync(self):
        return lib.shout_sync(self.obj)

    @check_error_code
    def close(self):
        return lib.shout_close(self.obj)

    def send_file(self, file_name):
        print(file_name)
        with open(file_name, 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break

                self.send(chunk)
                self.sync()

    def free(self):
        lib.shout_free(self.obj)


@contextmanager
def connect(**kwargs):
    cn = Connection(**kwargs)
    cn.open()
    yield cn
    cn.close()
    cn.free()
