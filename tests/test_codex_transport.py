import asyncio
import json

import pytest

from services.codex_transport import CodexError, CodexSession


class Input:
    def __init__(self, process):
        self.process = process
        self.messages = []

    def write(self, raw):
        message = json.loads(raw)
        self.messages.append(message)
        method = message.get('method')
        if 'id' in message and method and method != 'no-response':
            result = {'thread': {'id': 'thread1'}} if method == 'thread/start' else {}
            self.process.feed({'id': message['id'], 'result': result})
        if method == 'turn/start':
            self.process.feed({'method': 'item/completed', 'params': {'threadId': 'thread1', 'item': {'type': 'agentMessage', 'text': '{"plan": []}'}}})
            self.process.feed({'method': 'turn/completed', 'params': {'threadId': 'thread1', 'turn': {'status': 'completed', 'items': []}}})

    async def drain(self):
        pass

    def close(self):
        pass


class Process:
    def __init__(self):
        self.stdout = None
        self.stdin = Input(self)
        self.returncode = None
        self.killed = False

    def feed(self, value):
        self.stdout.feed_data(json.dumps(value).encode() + b'\n')

    def kill(self):
        self.killed = True
        self.returncode = -9
        self.stdout.feed_eof()

    async def wait(self):
        return self.returncode


def setup(monkeypatch):
    process = Process()
    captured = {}

    async def spawn(*args, **kwargs):
        captured.update(args=args, **kwargs)
        process.stdout = asyncio.StreamReader()
        return process

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    return process, captured


def test_isolated_environment_and_generate(monkeypatch, tmp_path):
    process, captured = setup(monkeypatch)
    monkeypatch.setenv('OPENAI_API_KEY', 'never-inherit')
    monkeypatch.setenv('CODEX_HOME', '/private/user')

    async def run():
        session = CodexSession(str(tmp_path))
        await session.start()
        assert await session.generate('create plan', 'test-model') == {'plan': []}
        await session.close()
    asyncio.run(run())
    assert 'OPENAI_API_KEY' not in captured['env']
    assert captured['env']['CODEX_HOME'] == str(tmp_path)
    assert captured['cwd'] == str(tmp_path / 'work')
    assert 'features.shell_tool=false' in captured['args']
    thread = next(m['params'] for m in process.stdin.messages if m.get('method') == 'thread/start')
    assert thread['ephemeral'] and thread['sandbox'] == 'read-only'
    assert thread['approvalPolicy'] == 'never'
    assert process.killed


def test_login_notification_before_wait_is_retained(monkeypatch, tmp_path):
    process, _ = setup(monkeypatch)

    async def run():
        session = CodexSession(str(tmp_path))
        await session.start()
        process.feed({'method': 'account/login/completed', 'params': {'loginId': 'login1', 'success': True}})
        await asyncio.sleep(0)
        assert await session.await_login('login1', timeout=1)
        await session.close()
    asyncio.run(run())


def test_request_timeout_and_cancellation_do_not_leak_pending(monkeypatch, tmp_path):
    setup(monkeypatch)

    async def run():
        session = CodexSession(str(tmp_path))
        await session.start()
        with pytest.raises(CodexError, match='zaman'):
            await session.request('no-response', {}, timeout=0.001)
        assert not session._pending
        task = asyncio.create_task(session.request('no-response', {}))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not session._pending
        await session.close()
    asyncio.run(run())


@pytest.mark.parametrize('message', [
    {'id': 900, 'method': 'item/commandExecution/requestApproval', 'params': {'command': 'secret'}},
    {'method': 'item/started', 'params': {'item': {'type': 'commandExecution'}}},
    {'method': 'item/completed', 'params': {'item': {'type': 'fileChange'}}},
])
def test_tool_requests_fail_closed(monkeypatch, tmp_path, message):
    process, _ = setup(monkeypatch)

    async def run():
        session = CodexSession(str(tmp_path))
        await session.start()
        process.feed(message)
        await asyncio.sleep(0)
        with pytest.raises(CodexError):
            await session.request('account/read', {})
        assert process.killed
        await session.close()
    asyncio.run(run())


def test_malformed_and_oversized_output_are_safe(monkeypatch, tmp_path):
    process, _ = setup(monkeypatch)

    async def run():
        session = CodexSession(str(tmp_path))
        await session.start()
        process.stdout.feed_data(b'secret-invalid-json\n')
        await asyncio.sleep(0)
        with pytest.raises(CodexError) as error:
            await session.request('account/read', {})
        assert 'secret' not in str(error.value)
        await session.close()
    asyncio.run(run())


def test_stdout_budget_is_enforced(monkeypatch, tmp_path):
    process, _ = setup(monkeypatch)

    async def run():
        session = CodexSession(str(tmp_path))
        await session.start()
        process.stdout.feed_data(json.dumps({'method': 'ignored', 'params': {'text': 'x' * (1024 * 1024)}}).encode() + b'\n')
        await asyncio.sleep(0)
        with pytest.raises(CodexError):
            await session.request('account/read', {})
        assert process.killed
        await session.close()
    asyncio.run(run())


def test_rpc_error_is_redacted(monkeypatch, tmp_path):
    process, _ = setup(monkeypatch)

    async def run():
        session = CodexSession(str(tmp_path))
        await session.start()
        pending = asyncio.create_task(session.request('no-response', {}))
        await asyncio.sleep(0)
        request_id = process.stdin.messages[-1]['id']
        process.feed({'id': request_id, 'error': {'message': 'secret-token-value'}})
        with pytest.raises(CodexError) as error:
            await pending
        assert 'secret' not in str(error.value)
        await session.close()
    asyncio.run(run())
