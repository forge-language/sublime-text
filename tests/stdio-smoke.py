#!/usr/bin/env python3
"""Validate an actual Forge LSP executable without modifying editor profiles."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--command-json', default='["forge-lsp"]', help='JSON argv array, e.g. ["node","/path/out/server.js","--stdio"]')
args = parser.parse_args()
command = json.loads(args.command_json)
if not isinstance(command, list) or not command or any(not isinstance(arg, str) for arg in command):
    parser.error('--command-json must be a nonempty JSON array of strings')
with tempfile.TemporaryDirectory(prefix='forge-lsp-smoke-') as temporary:
    document = Path(temporary) / 'main.fg'
    document.write_text('fn main() {\n    println("hello");\n}\n')
    messages = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'rootUri': Path(temporary).as_uri(), 'capabilities': {}}},
        {'jsonrpc': '2.0', 'method': 'initialized', 'params': {}},
        {'jsonrpc': '2.0', 'method': 'textDocument/didOpen', 'params': {'textDocument': {'uri': document.as_uri(), 'languageId': 'forge', 'version': 1, 'text': document.read_text()}}},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'textDocument/completion', 'params': {'textDocument': {'uri': document.as_uri()}, 'position': {'line': 1, 'character': 4}}},
        {'jsonrpc': '2.0', 'id': 3, 'method': 'shutdown', 'params': None},
        {'jsonrpc': '2.0', 'method': 'exit'},
    ]
    payload = b''
    for message in messages:
        body = json.dumps(message).encode()
        payload += b'Content-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body
    result = subprocess.run(command, input=payload, capture_output=True, timeout=20)
    if result.returncode:
        raise SystemExit('Language server failed: ' + result.stderr.decode(errors='replace'))
    output, responses = result.stdout, {}
    while output:
        header, output = output.split(b'\r\n\r\n', 1)
        headers = dict(line.split(b':', 1) for line in header.split(b'\r\n'))
        length = int(headers[b'Content-Length'].strip())
        body, output = output[:length], output[length:]
        response = json.loads(body)
        if 'id' in response:
            responses[response['id']] = response
    assert set(responses) >= {1, 2, 3}, responses
    assert 'capabilities' in responses[1]['result'], responses[1]
    assert 'completionProvider' in responses[1]['result']['capabilities'], responses[1]
    completion = responses[2]['result']
    items = completion if isinstance(completion, list) else completion['items']
    assert items and any(item['label'] == 'str_builder' for item in items), completion
    assert 'result' in responses[3] and 'error' not in responses[3], responses[3]
    print('Actual stdio initialize, Forge document open, completion (str_builder), shutdown/exit passed')
