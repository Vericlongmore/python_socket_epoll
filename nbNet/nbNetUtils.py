#!/usr/bin/env python
# coding: utf-8

from daemon import Daemon
import socket
import select
import time
import pdb
import sys, os
import fcntl

#DEBUG = True
DEBUG = False

from inspect import currentframe

def get_linenumber():
    cf = currentframe()
    return str(cf.f_back.f_back.f_lineno)


def dbgPrint(msg):
    if DEBUG:
        print get_linenumber(), msg

def nonblocking(fd):
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

import signal,functools
class TimeoutError(Exception): pass
def timeout(seconds, error_message = 'Function call timed out'):
    def decorated(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return functools.wraps(func)(wrapper)
    return decorated

@timeout(5)
def connect_timeout(socket, host_port):
    return socket.connect(host_port)

def sendData_mh(sock_l, host_l, data, single_host_retry = 3):
    """
    saver_l = ["localhost:50001","127.0.0.1:50001"]
    sock_l = [some_socket]
    sendData_mh(sock_l,saver_l,"this is data to send")
    """
    done = False
    for host_port in host_l:
        if done:
            break
        host,port =host_port.split(':')
        port = int(port)
        print "iter", host, port
        print "sock_l", sock_l
        retry = 0
        while retry < single_host_retry:
            try:
                if sock_l[0] == None:
                    sock_l[0] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    print "connecting", host, port
                    #connect_timeout(sock_l[0], (host, port))
                    sock_l[0].settimeout(5)
                    sock_l[0].connect((host, port))
                d = data
                sock_l[0].sendall("%010d%s"%(len(d), d))
                print "%010d%s"%(len(d), d)
                count = sock_l[0].recv(10)
                if not count:
                    print 'count', count
                    raise Exception("recv error", "recv error")
                count = int(count)
                buf = sock_l[0].recv(count)
                print buf
                if buf[:2] == "OK":
                    retry = 0
                    done = True
                    return True
            except (Exception), msg:
                try:
                    print msg.errno
                except:
                    pass
                sock_l[0].close()
                sock_l[0] = None
                time.sleep(1)
                retry += 1

def sendData(sock_l, host, port, data):
    retry = 0 
    while retry < 3:
        try:
            if sock_l[0] == None:
                sock_l[0] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock_l[0].connect((host, port))
                print "connecting"
            d = data
            sock_l[0].sendall("%010d%s"%(len(d), d)) 
            print "%010d%s"%(len(d), d)
            count = sock_l[0].recv(10)
            if not count:
                raise Exception("recv error", "recv error")
            count = int(count)
            buf = sock_l[0].recv(count)
            print buf 
            if buf[:2] == "OK":
                retry = 0 
                break
        except:
            sock_l[0].close()
            sock_l[0] = None
            retry += 1



# initial status for state machine
class STATE:
    def __init__(self):
        self.state = "accept"
        self.have_read = 0
        self.need_read = 10
        self.have_write = 0
        self.need_write = 0
        self.buff_write = ""
        self.buff_read = ""
        # sock_obj is a object
        self.sock_obj = ""
        self.popen_pipe = 0
    
    def printState(self):
        if DEBUG:
            dbgPrint('\n - current state of fd: %d' % self.sock_obj.fileno())
            dbgPrint(" - - state: %s" % self.state)
            dbgPrint(" - - have_read: %s" % self.have_read)
            dbgPrint(" - - need_read: %s" % self.need_read)
            dbgPrint(" - - have_write: %s" % self.have_write)
            dbgPrint(" - - need_write: %s" % self.need_write)
            dbgPrint(" - - buff_write: %s" % self.buff_write)
            dbgPrint(" - - buff_read:  %s" % self.buff_read)
            dbgPrint(" - - sock_obj:   %s" % self.sock_obj)


