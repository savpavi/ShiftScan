"""Private, bounded JSONL transport to the official Codex app-server.

Each instance must receive a disposable private home, never an operator's home.
No upstream text is included in transport errors or application logs.
"""
import asyncio
import json
import os
from pathlib import Path


LIMIT = 1024 * 1024
SAFE_ITEMS = {'agentMessage', 'userMessage', 'reasoning', 'contextCompaction'}
DISABLED_FEATURES = (
    'shell_tool', 'unified_exec', 'shell_snapshot', 'apps', 'browser_use',
    'computer_use', 'multi_agent', 'multi_agent_v2', 'hooks', 'image_generation',
    'skill_search', 'skill_mcp_dependency_install', 'code_mode', 'code_mode_host',
    'goals', 'sleep_tool', 'tool_suggest', 'artifact',
)


class CodexError(Exception):
    """Safe error suitable for conversion to a public connection failure."""


class CodexSession:
    def __init__(self, home: str):
        self.home = str(Path(home).resolve())
        self.work = str(Path(self.home) / 'work')
        self._process = None
        self._reader = None
        self._pending = {}
        self._next_id = 0
        self._failure = None
        self._login_results = {}
        self._login_event = asyncio.Event()
        self._events = asyncio.Queue(maxsize=128)
        self._generating = False

    async def start(self):
        if self._process is not None:
            raise CodexError('Codex oturumu zaten başlatıldı.')
        Path(self.home).mkdir(mode=0o700, parents=True, exist_ok=True)
        Path(self.work).mkdir(mode=0o700, exist_ok=True)
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
               'HOME': self.home, 'CODEX_HOME': self.home, 'RUST_LOG': 'off'}
        for key in ('SSL_CERT_FILE', 'SSL_CERT_DIR'):
            if os.environ.get(key):
                env[key] = os.environ[key]
        binary = os.environ.get('SHIFTSCAN_CODEX_BIN', 'codex')
        if binary != 'codex' and not os.path.isabs(binary):
            raise CodexError('Codex çalıştırılabilir dosyası yapılandırılmamış.')
        args = [binary, 'app-server', '-c', 'cli_auth_credentials_store="file"',
                '-c', 'web_search="disabled"', '-c', 'history.persistence="none"',
                '-c', 'sandbox_mode="read-only"', '-c', 'approval_policy="never"']
        for feature in DISABLED_FEATURES:
            args.extend(['-c', f'features.{feature}=false'])
        try:
            self._process = await asyncio.create_subprocess_exec(
                *args, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, cwd=self.work, env=env, limit=LIMIT,
            )
            self._reader = asyncio.create_task(self._read())
            await self.request('initialize', {
                'clientInfo': {'name': 'shiftscan', 'version': '1.0.0'},
                'capabilities': {'experimentalApi': False},
            })
            await self._send({'method': 'initialized', 'params': {}})
        except asyncio.CancelledError:
            await self.close()
            raise
        except Exception:
            await self.close()
            raise CodexError('Codex bağlantısı başlatılamadı.') from None

    async def _send(self, message):
        if self._failure or not self._process or self._process.returncode is not None:
            raise CodexError(self._failure or 'Codex bağlantısı kapalı.')
        encoded = json.dumps(message, ensure_ascii=False).encode() + b'\n'
        if len(encoded) > LIMIT:
            raise CodexError('Codex isteği çok büyük.')
        try:
            self._process.stdin.write(encoded)
            await self._process.stdin.drain()
        except (OSError, RuntimeError):
            raise CodexError('Codex bağlantısı kesildi.') from None

    def _fail(self):
        self._failure = 'Codex yanıtı güvenli biçimde işlenemedi.'
        for future in self._pending.values():
            if not future.done():
                future.set_exception(CodexError(self._failure))
        self._login_event.set()
        try:
            self._events.put_nowait(None)
        except asyncio.QueueFull:
            pass
        if self._process and self._process.returncode is None:
            try:
                self._process.kill()
            except ProcessLookupError:
                pass

    async def _read(self):
        total = 0
        try:
            while True:
                raw = await self._process.stdout.readline()
                if not raw:
                    self._fail()
                    return
                total += len(raw)
                if total > LIMIT:
                    raise ValueError('limit')
                message = json.loads(raw)
                if not isinstance(message, dict):
                    raise ValueError('object')
                # Never approve or execute any server-initiated request.
                if 'method' in message and 'id' in message:
                    raise ValueError('server request')
                if 'id' in message:
                    future = self._pending.get(message['id'])
                    if future is not None and not future.done():
                        if 'error' in message:
                            future.set_exception(CodexError('Codex isteği tamamlanamadı.'))
                        else:
                            future.set_result(message.get('result', {}))
                    continue
                method, params = message.get('method'), message.get('params', {})
                if not isinstance(params, dict):
                    raise ValueError('params')
                if method == 'account/login/completed':
                    login_id = params.get('loginId')
                    if isinstance(login_id, str):
                        if len(self._login_results) >= 16:
                            raise ValueError('login limit')
                        self._login_results[login_id] = params.get('success') is True
                        self._login_event.set()
                elif method in ('item/started', 'item/completed'):
                    if params.get('item', {}).get('type') not in SAFE_ITEMS:
                        raise ValueError('tool item')
                    if self._generating and method == 'item/completed':
                        self._events.put_nowait((method, params))
                elif method == 'turn/completed' and self._generating:
                    self._events.put_nowait((method, params))
        except asyncio.CancelledError:
            raise
        except Exception:
            self._fail()

    async def request(self, method, params, timeout=30):
        self._next_id += 1
        request_id = self._next_id
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        try:
            await self._send({'id': request_id, 'method': method, 'params': params})
            return await asyncio.wait_for(future, timeout)
        except (TimeoutError, asyncio.TimeoutError):
            raise CodexError('Codex isteği zaman aşımına uğradı.') from None
        finally:
            self._pending.pop(request_id, None)
            if not future.done():
                future.cancel()

    async def await_login(self, login_id, timeout=600):
        async def wait():
            while login_id not in self._login_results:
                if self._failure:
                    raise CodexError(self._failure)
                self._login_event.clear()
                await self._login_event.wait()
            return self._login_results.pop(login_id)
        try:
            return await asyncio.wait_for(wait(), timeout)
        except (TimeoutError, asyncio.TimeoutError):
            raise CodexError('ChatGPT girişi zaman aşımına uğradı.') from None

    async def generate(self, prompt, model):
        if self._generating:
            raise CodexError('Codex oturumu meşgul.')
        self._generating = True
        try:
            return await asyncio.wait_for(self._generate(prompt, model), 90)
        except (TimeoutError, asyncio.TimeoutError):
            raise CodexError('Codex yanıtı zaman aşımına uğradı.') from None
        finally:
            self._generating = False

    async def _generate(self, prompt, model):
        result = await self.request('thread/start', {
            'model': model, 'cwd': self.work, 'ephemeral': True,
            'approvalPolicy': 'never', 'sandbox': 'read-only',
            'baseInstructions': 'Return only the requested JSON object. Never use tools, read files, execute commands or access websites.',
        })
        try:
            thread_id = result['thread']['id']
        except (KeyError, TypeError):
            raise CodexError('Codex oturumu oluşturulamadı.') from None
        await self.request('turn/start', {
            'threadId': thread_id, 'input': [{'type': 'text', 'text': prompt}],
            'approvalPolicy': 'never',
            'sandboxPolicy': {'type': 'readOnly', 'networkAccess': False},
        })
        messages = []
        while True:
            if self._failure:
                raise CodexError(self._failure)
            event = await self._events.get()
            if event is None:
                raise CodexError('Codex bağlantısı kesildi.')
            method, params = event
            if params.get('threadId') != thread_id:
                continue
            if method == 'item/completed':
                item = params['item']
                if item['type'] == 'agentMessage':
                    messages.append(item.get('text', ''))
            else:
                turn = params.get('turn', {})
                if turn.get('status') != 'completed':
                    raise CodexError('Codex planı tamamlanamadı.')
                items = turn.get('items', [])
                if any(item.get('type') not in SAFE_ITEMS for item in items):
                    self._fail()
                    raise CodexError(self._failure)
                final = [item.get('text', '') for item in items if item.get('type') == 'agentMessage']
                if final:
                    messages = final
                break
        try:
            value = json.loads(messages[-1])
            if not isinstance(value, (dict, list)):
                raise ValueError('json shape')
            return value
        except (ValueError, IndexError, TypeError):
            raise CodexError('Codex geçerli bir JSON planı döndürmedi.') from None

    async def close(self):
        process = self._process
        if process:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            await process.wait()
        if self._reader:
            self._reader.cancel()
            try:
                await self._reader
            except asyncio.CancelledError:
                pass
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()
        self._failure = 'Codex bağlantısı kapalı.'
