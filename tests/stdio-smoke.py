#!/usr/bin/env python3
"""Validate an actual Forge LSP executable without modifying editor profiles."""
import argparse
import json
from pathlib import Path
import subprocess
import queue
import threading
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--command-json', default='["forge-lsp"]', help='JSON argv array, e.g. ["node","/path/out/server.js","--stdio"]')
args = parser.parse_args()
command = json.loads(args.command_json)
if not isinstance(command, list) or not command or any(not isinstance(arg, str) for arg in command):
    parser.error('--command-json must be a nonempty JSON array of strings')
with tempfile.TemporaryDirectory(prefix='forge-lsp-smoke-') as temporary:
    document = Path(temporary) / 'main.fg'
    document.write_text('native main {\n    println("hello");\n}\n')
    messages = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'rootUri': Path(temporary).as_uri(), 'capabilities': {}}},
        {'jsonrpc': '2.0', 'method': 'initialized', 'params': {}},
        {'jsonrpc': '2.0', 'method': 'textDocument/didOpen', 'params': {'textDocument': {'uri': document.as_uri(), 'languageId': 'forge', 'version': 1, 'text': document.read_text()}}},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/completion', 'params': {'textDocument': {'uri': document.as_uri()}, 'position': {'line': 1, 'character': 4}}},
        {'jsonrpc': '2.0', 'id': 3, 'method': 'shutdown', 'params': None},
        {'jsonrpc': '2.0', 'method': 'exit'},
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    received = queue.Queue()

    def reader():
        try:
            while True:
                header = process.stdout.readline()
                if not header:
                    return
                headers = {}
                while header not in (b'\r\n', b'\n'):
                    key, value = header.split(b':', 1)
                    headers[key.lower()] = value.strip()
                    header = process.stdout.readline()
                length = int(headers[b'content-length'])
                body = process.stdout.read(length)
                received.put(json.loads(body))
        except Exception as error:
            received.put(error)

    threading.Thread(target=reader, daemon=True).start()
    responses = {}
    try:
        for message in messages:
            body = json.dumps(message).encode()
            process.stdin.write(b'Content-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
            process.stdin.flush()
            if 'id' in message:
                while message['id'] not in responses:
                    response = received.get(timeout=20)
                    if isinstance(response, Exception):
                        raise response
                    if 'id' in response:
                        responses[response['id']] = response
        process.stdin.close()
        assert process.wait(timeout=10) == 0, process.stderr.read().decode(errors='replace')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    assert set(responses) >= {1, 2, 3}, responses
    assert 'capabilities' in responses[1]['result'], responses[1]
    assert 'completionProvider' in responses[1]['result']['capabilities'], responses[1]
    completion = responses[2]['result']
    items = completion if isinstance(completion, list) else completion['items']
    assert items and any(item['label'] == 'return' for item in items), completion
    assert 'result' in responses[3] and 'error' not in responses[3], responses[3]
    print('Actual stdio initialize, Forge document open, completion (return), shutdown/exit passed')
