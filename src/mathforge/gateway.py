"""Explicit local, bounded-lifetime gateway; does not launch a legacy controller."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import re
import threading
from urllib.parse import unquote, urlsplit

from .source_audit import BoundaryError, SourceAuditQueue


def server(queue, token, port=0):
    if len(token) < 32:
        raise ValueError('gateway token must contain at least 32 characters')
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='admitted-audit')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Never log headers, credentials or private request context.

        def send(self, status, value, *, binary=False):
            raw=value if binary else json.dumps(value,ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/octet-stream' if binary else 'application/json')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(raw)

        def dispatch(self):
            if not hmac.compare_digest(self.headers.get('Authorization',''), 'Bearer '+token):
                raise BoundaryError(401,'authenticated engine request required')
            if self.headers.get('Origin') or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise BoundaryError(403,'engine gateway does not accept browser-origin requests')
            host=urlsplit('http://'+self.headers.get('Host','')).hostname
            if host not in {'127.0.0.1','localhost','::1'}:
                raise BoundaryError(403,'loopback host required')
            parts=urlsplit(self.path)
            if parts.query or parts.fragment:
                raise BoundaryError(400,'unexpected URL parameters')
            path=parts.path.removeprefix('/v2')
            if self.command=='POST' and path=='/research-tasks':
                if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type','').split(';')[0]!='application/json':
                    raise BoundaryError(415,'bounded JSON with Content-Length required')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=65536:raise BoundaryError(413,'request must be at most64 KiB')
                request=json.loads(self.rfile.read(length))
                result=queue.enqueue(request,self.headers.get('Idempotency-Key',''))
                self.send(201,result)
                # Duplicate requests return their existing ID. Atomic queue transition
                # prevents a second worker even when two post handlers race.
                if result['status']=='queued':pool.submit(queue.run,result['engine_task_id'])
                return
            match=re.fullmatch(r'/research-tasks/by-key/([A-Za-z0-9-]{16,100})',path)
            if self.command=='GET' and match:
                return self.send(200,queue.result(queue.row(key=match[1])['id']))
            match=re.fullmatch(r'/research-tasks/(mf-audit-[a-f0-9]{32})(?:/(cancel|artifacts/([^/]+)))?',path)
            if match:
                if self.command=='GET' and not match[2]:return self.send(200,queue.result(match[1]))
                if self.command=='POST' and match[2]=='cancel':return self.send(200,queue.cancel(match[1]))
                if self.command=='GET' and match[3]:return self.send(200,queue.artifact(match[1],unquote(match[3])),binary=True)
            raise BoundaryError(404,'unknown engine route')

        def handle_request(self):
            self.connection.settimeout(5)
            try:self.dispatch()
            except BoundaryError as error:self.send(error.status,{'error':str(error)})
            except (ValueError,KeyError,TypeError):self.send(400,{'error':'invalid engine request'})
            except OSError:self.send(503,{'error':'engine journal unavailable; reconcile original key'})

        do_GET=handle_request
        do_POST=handle_request
    http=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    http.daemon_threads=True
    http.audit_pool=pool
    return http


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--journal',required=True)
    parser.add_argument('--port',type=int,default=9444)
    parser.add_argument('--mode',choices=['CONTRACT_TEST','REAL_RUN'],default='CONTRACT_TEST')
    parser.add_argument('--history-root',type=Path,help='read-only historical replay registry; mandatory for REAL_RUN')
    parser.add_argument('--serve-seconds',type=int,default=180)
    parser.add_argument('--recover',help='operator reconciliation marks interrupted; never replays')
    args=parser.parse_args()
    if not 1<=args.serve_seconds<=600:raise ValueError('bounded gateway lifetime required')
    queue=SourceAuditQueue(args.root,args.journal,os.environ.get('MATHFORGE_RECEIPT_SECRET',''),mode=args.mode,legacy_root=args.history_root)
    if args.recover:
        print(json.dumps(queue.recover(args.recover)));return
    http=server(queue,os.environ.get('MATHFORGE_GATEWAY_TOKEN',''),args.port)
    timer=threading.Timer(args.serve_seconds,http.shutdown);timer.daemon=True;timer.start()
    print(json.dumps({'gateway':'ready','port':http.server_port,'execution_mode':args.mode,'max_tasks':1}),flush=True)
    try:http.serve_forever(poll_interval=.05)
    finally:
        timer.cancel();http.server_close();http.audit_pool.shutdown(wait=True,cancel_futures=True)


if __name__=='__main__':main()
