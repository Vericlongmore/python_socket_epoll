#!/usr/bin/env python
# coding: utf-8

from daemon import Daemon
import socket
import select
import time

html = """HTTP/1.1 200\r\nContent-Type: text/html\r\nContent-Length: 14\r\n\r\n<h1>Hello</h1>"""

# 状态机
class _STATE:
    def __init__(self):
        self.state = "accept"
        self.have_read = 0
        self.need_read = 10
        self.have_write = 0
        self.need_write = 0
        self.buff_read = ""
        self.buff_write = ""
        self.sock = 0

class nbNet:
    def __init__(self, addr, port,logic):
        self.conn_state = {}
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_sock.bind((addr, port))
        self.listen_sock.listen(10)
        self.setFd(self.listen_sock)
        self.epoll_sock = select.epoll()
        self.epoll_sock.register(self.listen_sock.fileno(), select.EPOLLIN)
        self.logic = logic
        self.sm = {
            "accept": self.accept,
            "read": self.read,
            "write": self.write,
            "process": self.process,
            "closing": self.close,
        }

    def setFd(self, sock):
        """
        为sock创建一个状态机，
        :param sock:
        :return:
        """
        tmp_state = _STATE()
        tmp_state.sock = sock
        self.conn_state[sock.fileno()] = tmp_state


    def accept(self, fd):
        sock_state = self.conn_state[fd]
        sock = sock_state.sock
        conn, addr = sock.accept()
        conn.setblocking(0)                                             # 将这个socket设置为非阻塞
        self.epoll_sock.register(conn.fileno(), select.EPOLLIN)
        self.setFd(conn)
        self.conn_state[conn.fileno()].state = "read"

    def close(self, fd):
        sock = self.conn_state[fd].sock
        sock.close()
        self.epoll_sock.unregister(fd)
        self.conn_state.pop(fd)

    def read(self, fd):
        try:
            sock_state = self.conn_state[fd]
            conn = sock_state.sock
            if sock_state.need_read <= 0:
                sock_state.state = 'closing'
                self.state_machine(fd)
            one_read = conn.recv(sock_state.need_read)
            print "one_read", one_read, "need", sock_state.need_read
            if len(one_read) == 0:
                return
            # 处理接收的数据
            sock_state.buff_read += one_read               # 将收到的数据存入buff
            sock_state.have_read += len(one_read)          # 修改已经接收一的字节数
            sock_state.need_read -= len(one_read)          # 修改还需要接收的字节数

            # 处理协议头
            if sock_state.have_read == 10:
                # 开始处理主体部部
                sock_state.need_read += int(sock_state.buff_read)     # 修改需要接收的主体字节数
                sock_state.buff_read = ''                  # 清空缓存
                self.state_machine(fd)
            elif sock_state.need_read == 0:
                # 当前全部接收完毕，改变状态，去招待具体的动作
                sock_state.state = "process"
                self.state_machine(fd)
        except socket.error, msg:
            sock_state.state = 'closing'
            print(msg)
            self.state_machine(fd)

    def write(self, fd):
        sock_state = self.conn_state[fd]
        conn = sock_state.sock
        last_have_send = sock_state.have_write
        try:
            # 发磅返回给客户端的数据
            have_send = conn.send(sock_state.buff_write[last_have_send:])   # 取出要发送的数据
            sock_state.have_write += have_send
            sock_state.need_write -= have_send
            if sock_state.need_write == 0 and sock_state.have_write != 0:
                # 数据发送完毕，初始化状态
                self.setFd(conn)
                self.conn_state[fd].state = "read"
                self.epoll_sock.modify(fd, select.EPOLLIN)
        except socket.error, msg:
            sock_state.state = "closing"
            print(msg)
            self.state_machine(fd)

    def process(self, fd):
        sock_state = self.conn_state[fd]
        # 招待具体的招待方法
        response = self.logic(sock_state.buff_read)
        sock_state.buff_write = "%010d%s" % (len(response), response)
        sock_state.need_write = len(sock_state.buff_write)
        # 设置改为写的状态
        sock_state.state = "write"
        # 改变监听事件为写
        self.epoll_sock.modify(fd, select.EPOLLOUT)
        self.state_machine(fd)

    def run(self):
        while True:
            epoll_list = self.epoll_sock.poll()
            for fd , events in epoll_list:
                sock_state = self.conn_state[fd]
                if select.EPOLLHUP & events:
                    print "EPOLLHUP"
                    sock_state.state = "closing"
                elif select.EPOLLERR & events:
                    print 'EPOLLERR'
                    sock_state.state = "closing"
                self.state_machine(fd)

    def state_machine(self, fd):
        time.sleep(1)
        print self.conn_state[fd].state
        sock_state = self.conn_state[fd]
        self.sm[sock_state.state](fd)


if __name__ == "__main__":
    def logic(in_data):
        return in_data[::-1]
    reverseD = nbNet("0.0.0.0", 9124, logic)
    reverseD.run()
