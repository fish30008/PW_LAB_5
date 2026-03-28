import argparse
import sys
import urllib.parse
import socket
import ssl
import time
from bs4 import BeautifulSoup
import json


class HTTPClient:
    _cache = {}

    def _cache_get(self, url):
        if url in self._cache:
            body, headers, ts = self._cache[url]
            if time.time() - ts < 300:
                return body, headers
        return None

    def _cache_set(self, url, body, headers):
        self._cache[url] = (body, headers, time.time())


client = HTTPClient()

def parse_args():
    parser = argparse.ArgumentParser(description="HTTP client with search", add_help=False)
    parser.add_argument('-u', '--url', help='make HTTP request to URL')
    parser.add_argument('-s', '--search', help='search term')
    parser.add_argument('-h', '--help', action='store_true', help='show help')
    args = parser.parse_args()

    if args.help or (not args.url and not args.search):
        parser.print_help()
        sys.exit(0)

    if args.url and args.search:
        print("Error: -u and -s cannot be used together.", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    return args


def _parse_url(url):
    if '://' not in url:
        url = 'http://' + url

    parsed = urllib.parse.urlparse(url)
    scheme = (parsed.scheme or 'http').lower()
    if scheme not in ('http', 'https'):
        raise ValueError(f"Unsupported URL scheme: {scheme}")

    host = parsed.hostname
    if not host:
        raise ValueError('URL must include a hostname')

    port = parsed.port or (443 if scheme == 'https' else 80)
    path = parsed.path or '/'
    if parsed.query:
        path += '?' + parsed.query
    return scheme, host, port, path

def _connect(host, port, scheme):
    sock = socket.create_connection((host, port), timeout=10)
    if scheme == 'https':
        context = ssl.create_default_context()
        sock = context.wrap_socket(sock, server_hostname=host)
    return sock

def _send_request(sock, method, path, headers):
    request = f"{method} {path} HTTP/1.1\r\n"
    for k, v in headers.items():
        request += f"{k}: {v}\r\n"
    request += "\r\n"
    sock.sendall(request.encode())


def _recv_exact(sock, n, buffer):
    while len(buffer) < n:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer += chunk
    return buffer[:n], buffer[n:]

def _read_response(sock):

    data = b''
    while b'\r\n\r\n' not in data:
        data += sock.recv(4096)
    header_data, body_data = data.split(b'\r\n\r\n', 1)

    lines = header_data.split(b'\r\n')
    status_line = lines[0].decode()
    status_code = int(status_line.split()[1])

    headers = {}
    for line in lines[1:]:
        if b':' not in line:
            continue
        key, value = line.split(b':', 1)
        headers[key.decode().strip().lower()] = value.decode().strip()

    if 'content-length' in headers:
        content_length = int(headers['content-length'])
        while len(body_data) < content_length:
            body_data += sock.recv(4096)
    elif 'transfer-encoding' in headers and headers['transfer-encoding'].lower() == 'chunked':
        body_data = _read_chunked_body(sock, body_data)
    else:
        
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            body_data += chunk

    return status_code, headers, body_data


def _read_chunked_body(sock, initial_data):
    data = b''
    buffer = initial_data
    while True:
        while b'\r\n' not in buffer:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buffer += chunk

        if b'\r\n' not in buffer:
            break

        chunk_size_line, buffer = buffer.split(b'\r\n', 1)
        chunk_size = int(chunk_size_line.split(b';', 1)[0], 16)

        if chunk_size == 0:
            _, buffer = _recv_exact(sock, 2, buffer)
            break

        chunk_data, buffer = _recv_exact(sock, chunk_size, buffer)
        data += chunk_data
        _, buffer = _recv_exact(sock, 2, buffer)

    return data

def request(url, method='GET', headers=None):
    if headers is None:
        headers = {}

    # Content‑negotiation: просим JSON и HTML
    if 'Accept' not in headers:
        headers['Accept'] = 'text/html,application/json,text/plain;q=0.9,*/*;q=0.8'

    
    if method == 'GET':
        cached = client._cache_get(url)
        if cached:
            return 200, cached[1], cached[0]  

    redirects = 0
    current_url = url
    while redirects < 5:
        scheme, host, port, path = _parse_url(current_url)
        sock = _connect(host, port, scheme)
        req_headers = {
            'Host': host,
            'User-Agent': 'go2web/1.0',
            'Connection': 'close',
            **headers
        }

        _send_request(sock, method, path, req_headers)
        status, resp_headers, body = _read_response(sock)
        sock.close()

        if status in (301, 302, 303, 307, 308):
            location = resp_headers.get('location')
            if location:
                current_url = urllib.parse.urljoin(current_url, location)
                redirects += 1
                if method == 'POST' and status == 303:
                    method = 'GET'
                continue
        break

    if method == 'GET' and 200 <= status < 300:
        client._cache_set(current_url, body, resp_headers)

    return status, resp_headers, body

def pretty_print_response(headers, body):
    content_type = headers.get('content-type', '').lower()
    if 'application/json' in content_type:
        try:
            obj = json.loads(body.decode())
            print(json.dumps(obj, indent=2, ensure_ascii=False))
        except:
            print(body.decode())
    elif 'text/html' in content_type:
        soup = BeautifulSoup(body, 'html.parser')
        # remove scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        # remove empty lines
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        print(text)
    else:
        print(body.decode())

if __name__ == "__main__":
    args = parse_args()
    if args.url:
        try:
            #scheme, host, port, path = _parse_url(args.url) throwed them in to another function
            #print(f"Connecting to {host}:{port} using {scheme}...")
            #conn = _connect(host, port, scheme)
            # headers = {
            #     'Host': host,
            #     'User-Agent': 'go2web/1.0',
            #     'Accept': '*/*',
            #     'Connection': 'close',
            # }
            # _send_request(conn, 'GET', path, headers)
            status_code, response_headers, body = request(args.url)
            # conn.close()

            # print(f"HTTP status: {status_code}")
            # if status_code in [301, 302]:
            #     new_url = response_headers.get('location')
            #     print(f"Redirecting to: {new_url}")
            
            # content_type = response_headers.get('content-type', '')
            # if content_type:
            #     print(f"Content-Type: {content_type}")
            # print()

            
            pretty_print_response(response_headers, body)

            print(f'cache = {client._cache}')  
        except (ValueError, OSError) as err:
            print(f"Request failed: {err}", file=sys.stderr)
            sys.exit(1)
    
    elif args.search:
        print(f"Searching for term: {args.search}")