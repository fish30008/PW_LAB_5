# Implementation Lab 5

This document explains each function in the current go2web.py implementation.

## Overview

The program is a small command-line HTTP client with two main modes:
- URL mode: fetch a page/resource from a given URL
- Search mode: search DuckDuckGo HTML results and fetch one selected result

It implements HTTP communication manually with sockets, supports HTTPS, follows redirects, parses chunked responses, and includes a short in-memory cache for GET requests.

## Global Objects

### HTTPClient class

Purpose:
- Stores and serves a simple in-memory cache for HTTP responses.

Internal data:
- _cache: dictionary where key is URL and value is tuple (body, headers, timestamp).

### client

Purpose:
- Single global instance of HTTPClient used by request() for cache read/write.

## Function Explanations

### _cache_get(self, url)

Purpose:
- Tries to read a cached response for a URL.

How it works:
- Checks whether URL exists in _cache.
- If found, reads body, headers, and saved timestamp.
- Returns cached data only if entry is younger than 300 seconds.
- Returns None if missing or expired.

Why it exists:
- Avoids repeated network calls for recently fetched GET resources.

### _cache_set(self, url, body, headers)

Purpose:
- Stores response body and headers in cache with current timestamp.

How it works:
- Writes tuple (body, headers, time.time()) into _cache under the URL key.

Why it exists:
- Paired with _cache_get to provide short-lived client-side caching.

### parse_args()

Purpose:
- Parses command-line arguments and validates allowed usage.

How it works:
- Accepts:
  - -u / --url for direct URL fetch
  - -s / --search for search mode
  - -h / --help for help
- Prints help and exits if no action is provided.
- Rejects using -u and -s together.

Why it exists:
- Centralizes CLI input validation and keeps main flow clean.

### _parse_url(url)

Purpose:
- Converts input URL string into network-ready pieces.

How it works:
- Adds http:// if scheme is missing.
- Uses urllib.parse.urlparse.
- Validates scheme is only http or https.
- Extracts host, chooses default port (80/443), and builds path including query.

Returns:
- scheme, host, port, path

Why it exists:
- Standardizes URL handling before creating socket connections.

### _connect(host, port, scheme)

Purpose:
- Opens network connection to server and wraps with TLS for HTTPS.

How it works:
- Creates TCP socket with timeout.
- If scheme is https, wraps socket using SSL default context and SNI.

Returns:
- connected socket object

Why it exists:
- Isolates transport setup (plain TCP vs TLS) in one place.

### _send_request(sock, method, path, headers)

Purpose:
- Builds and sends raw HTTP/1.1 request bytes.

How it works:
- Creates request line: METHOD PATH HTTP/1.1
- Appends all headers from dictionary.
- Ends header section with empty line.
- Sends encoded request through socket.

Why it exists:
- Encapsulates manual request serialization logic.

### _recv_exact(sock, n, buffer)

Purpose:
- Ensures exactly n bytes are read (when possible), using existing buffered data first.

How it works:
- Keeps reading from socket until buffer has at least n bytes or stream closes.
- Returns tuple:
  - first n bytes
  - remaining bytes after n

Why it exists:
- Supports correct chunked-body parsing where precise byte counts matter.

### _read_response(sock)

Purpose:
- Reads full HTTP response: status code, headers, and body.

How it works:
- Reads until header terminator (CRLF CRLF).
- Parses status line and headers.
- Chooses body strategy:
  - content-length: read exact known size
  - transfer-encoding: chunked: delegate to _read_chunked_body
  - otherwise: read until connection close

Returns:
- status_code, headers_dict, body_bytes

Why it exists:
- Handles multiple common HTTP response framing styles.

### _read_chunked_body(sock, initial_data)

Purpose:
- Decodes HTTP chunked transfer encoding.

How it works:
- Reads chunk size line in hex.
- Reads exact chunk payload bytes plus trailing CRLF.
- Repeats until zero-sized final chunk.

Returns:
- decoded full body bytes

Why it exists:
- Chunked transfer cannot be handled by simple read-until-close logic safely.

### request(url, method='GET', headers=None)

Purpose:
- High-level request function that combines cache, redirect handling, and network IO.

How it works:
- Ensures headers dictionary exists.
- Adds default Accept header if absent.
- For GET:
  - checks cache first and returns cached result when available.
- Performs request loop with up to 5 redirects.
- Resolves relative redirect locations via urljoin.
- Converts POST to GET on HTTP 303 as per standard behavior.
- Caches successful GET responses.

Returns:
- status_code, response_headers, response_body

Why it exists:
- Provides single reusable entry point for both URL and search workflows.

### pretty_print_response(headers, body)

Purpose:
- Displays response body in human-friendly form based on Content-Type.

How it works:
- JSON content:
  - decodes and pretty-prints with indentation.
- HTML content:
  - parses with BeautifulSoup,
  - removes script/style tags,
  - extracts and cleans text.
- Other content:
  - prints decoded body directly.

Why it exists:
- Makes terminal output readable instead of raw markup when possible.

### _normalize_search_result_url(href)

Purpose:
- Converts search result links into real target URLs.

How it works:
- Handles DuckDuckGo redirect links containing uddg parameter.
- Supports both absolute and relative redirect formats.
- Converts protocol-relative links starting with // into https:// links.
- Otherwise returns href unchanged.

Why it exists:
- Search result pages often wrap outbound links; this extracts true destination URL.

### search_and_select(term)

Purpose:
- Executes search mode and lets user pick one result to fetch.

How it works:
- Sends query to DuckDuckGo HTML endpoint.
- Parses result blocks and extracts title + normalized link.
- Prints top 10 results.
- Reads user input for selection.
- Fetches selected URL and prints content using pretty_print_response.

Why it exists:
- Implements interactive search workflow from keyword to fetched page content.

## Main Program Flow

The main block does:
- parse_args()
- if URL mode:
  - calls request(args.url)
  - calls pretty_print_response(...)
- if search mode:
  - prints search message
  - calls search_and_select(args.search)

This keeps entry logic short and delegates technical work to helper functions.
