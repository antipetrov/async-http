#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import threading
from Queue import Queue
import urllib
import os
from optparse import OptionParser

import mimetypes

from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime


DOCUMENT_ROOT = './document_root'


def http_current_date():
    now = datetime.now()
    stamp = mktime(now.timetuple())
    return format_date_time(stamp) #--> Wed, 22 Oct 2008 10:52:40 GMT

def handle_client_queue(client_queue, worker_num):

    while True:
        client_socket, client_addr = client_queue.get()

        request = b''
        EOL1 = b'\n\n'
        EOL2 = b'\n\r\n'
        while EOL1 not in request and EOL2 not in request:
            request += client_socket.recv(1024)

        print 'Worker {} Received:\n{}'.format(worker_num, request)


        method, uri, headers, body = parse_request(request)
        response = process_request(method, uri, headers, body)

        bytes_sent=client_socket.send(response)
        print 'Sent {} bytes'.format(bytes_sent)

        client_socket.close()
        client_queue.task_done()


def parse_request(request):
    (head, body) = request.split('\r\n\r\n', 1) # empty line
    head_lines = head.split('\r\n')

    #line 1
    line_parts = head_lines[0].split(' ')
    method = line_parts[0]
    # todo: распарсить %XX
    uri = ''.join([line_parts[p] for p in range(1, len(line_parts)-1)])
    http_ver = line_parts.pop()

    # next lines - headers
    headers = {head_lines[h].split(': ')[0]:head_lines[h].split(': ')[1] for h in range(1, len(head_lines))}

    return method, uri, headers, body


def process_request(method, uri, headers, body):
    """
    Returns response
    """

    if method == 'HEAD':
        rstatus = 200
        rheaders = {}
        rbody = ''
        return rstatus, rheaders, rbody
    elif method == 'GET':
        return process_get(uri, headers, body)

def process_get(uri, headers, body):
    
    # get file
    file_path = '{}{}'.format(DOCUMENT_ROOT, uri)

    if file_path == '\\':
        pass
        # get index

    try:
        file = open(file_path)
    except IOError:
        return create_response(404)

    body = ''.join(file.readlines())
    file_type, file_encoding = mimetypes.guess_type(file_path)

    return create_response(200, body, file_type)


def process_head(uri, headers, body):
    return create_response(200, '<h1>some text</h2>', 'text/html')    


def create_response(status, body='', content_type=''):
    status_text = {
        200: 'OK', 
        405: 'Method not allowed', 
        404: 'Not Found'
        }
    
    header = []
    header.append('HTTP/1.1 {} {}'.format(status, status_text.get(status, '')))
    
    if status == 200:
        header.append('Date: {}'.format(http_current_date()))
        header.append('Server: LikeShareRetweetServer 1.0.0.0.1')
        header.append('Content-Length: {}'.format(len(body)))
        header.append('Content-Type: {}'.format(content_type))
        header.append('Connection: close')
        
    return '{}\r\n\r\n{}\r\n\r\n'.format('\n'.join(header), body)


    

def main():
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8099)
    op.add_option("-w", "--workers", action="store", type=int, default=1)
    (opts, args) = op.parse_args()

    bind_ip = '0.0.0.0'

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((bind_ip, opts.port))
    server.listen(5)  # max backlog of connections

    worker_threads = []
    client_queue = Queue()

    for w in range(0,opts.workers):
        print('Spawn worker {}'.format(w))
        worker_thread = threading.Thread(target=handle_client_queue, args=((client_queue,w,)))
        worker_thread.daemon = True
        worker_thread.start()
        worker_threads.append(worker_thread)

    print 'Listening on {}:{}'.format(bind_ip, opts.port)

    try:
        while True:
            client_sock, address = server.accept()
            client_queue.put((client_sock, address))
    except KeyboardInterrupt as e:
        print("\nserver stopped")
        exit()



if __name__ == "__main__":
    main()