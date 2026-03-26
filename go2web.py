import argparse
import sys

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

if __name__ == "__main__":
    args = parse_args()
    if args.url:
        print(f"Making HTTP request to URL: {args.url}")
    elif args.search:
        print(f"Searching for term: {args.search}")