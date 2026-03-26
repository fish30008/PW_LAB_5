import argparse
import sys
import urllib.parse
import socket
import ssl

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

if __name__ == "__main__":
    args = parse_args()
    if args.url:
        try:
            scheme, host, port, path = _parse_url(args.url)
            print(f"Parsed URL -> scheme={scheme}, host={host}, port={port}, path={path}")

            conn = _connect(host, port, scheme)
            conn.close()
            print("Connection check -> OK")
        except (ValueError, OSError) as err:
            print(f"Connection check -> FAILED: {err}", file=sys.stderr)
            sys.exit(1)
    elif args.search:
        print(f"Searching for term: {args.search}")