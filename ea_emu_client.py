from idaapi import *
import socket
from pickle import loads, dumps
from threading import Thread
from os import system
from time import sleep
from api_funcs import *
from ea_UI import Emulate_UI
from PySide import QtGui
from ea_utils import get_bits, root_dir

# Importing Unicorn Emulator directly into the IDAPython environment causes instability in IDA (random crashes ect.)
# As a result, Unicorn emulator is decoupled from IDA and runs as a seperate process communicating with IDA using a local socket (port 28745)
# The following client code runs within IDAPython and ships emulation requests to ea_emu_server which is a pure Python process

class Hook(DBG_Hooks):

    def __init__(self):
        DBG_Hooks.__init__(self)

    def dbg_bpt(self, tid, ea):
        send()
        return 0

    def dbg_step_into(self):
        send()
        return 0

    def dbg_step_until_ret(self):
        send()
        return 0

    def dbg_step_over(self):
        send()
        return 0


def send(addr=None, code=None):

    if not addr:
        addr = get_rg("RIP")
        code = dbg_read_memory(addr & 0xfffffffffffff000, 0x1000)

    flags = None
    bp = bpt_t()

    if get_bpt(addr,bp):
        flags = bp.flags
        bp.flags = 2
        update_bpt(bp)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(dumps(("emu", (addr,code, get_bits()))))
    error = False

    while True:
        data = s.recv(BUFFER_SIZE)
        if not data: break
        func, args = loads(data)
        if func == "result":
            break
        if func == "error":
            print "error: " + str(args)
            error = True
            break

        s.send(dumps(globals()[func](*args)))

    s.close()

    if flags:
        bp.flags = flags
        update_bpt(bp)

    if not error:
        for c, v in args.items():
            v = [i for i in v if i[0] not in ("rip", "eip")]
            if v:
                comment = GetCommentEx(c, 0)
                annotation = " ".join(a + "=" + hex(b).replace("L", "") for a, b in v)
                if comment and "e:" in comment:
                    comment = comment[:comment.find("e:")].strip(" ")
                MakeComm(c, (comment if comment else "").ljust(10) + " e: " + annotation)


def ea_emulate():

    global form
    global a
    global server_running

    print "JIASFJISFA"

    if not server_running:
        # Launch emulation server as a seperate process (see top for details why)
        # Python subprocess module is broken in IDA so the os.system function is used instead
        # (This requires a new Thread because the os.system function blocks by default)
        Thread(target=system, args=("python \"%sea_emu_server.py\"" % root_dir,)).start()
        server_running = True

    a = QtGui.QFrame()
    form = Emulate_UI()
    form.setupUi(a)
    if hooked:
        form.checkBox.click()

    form.checkBox.stateChanged.connect(toggle_hooking)
    form.pushButton.clicked.connect(lambda : a.close())
    form.pushButton_2.clicked.connect(send)

    a.show()


def toggle_hooking(state):

    global h
    global hooked

    if state:
        if not hooked:
            h = Hook()
            h.hook()
            hooked = True
    else:
        h.unhook()
        hooks = False

TCP_IP = '127.0.0.1';
TCP_PORT = 28745;
BUFFER_SIZE = 0x4000;
comments = []

file_name = None
h = None
hooked = False
form = None
a = None
server_running = False


