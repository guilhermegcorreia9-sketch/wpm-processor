# -*- coding: utf-8 -*-
# Created by Miguel Alexandre da Cunha
import os
import sys
import json
import queue
import shutil
import tempfile
import threading
import subprocess

from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
RUNNER_SCRIPT = os.path.join(PLUGIN_DIR, "core", "subprocess_runner.py")

_PYTHON_EXE_CACHE = None

def _looks_like_python(path):
    name = os.path.basename(path).lower()
    return name.startswith("python")

def _resolve_python_executable():
    """Encontra um interpretador Python de verdade para rodar o subprocesso.

    Em algumas instalações do QGIS no Windows, sys.executable NÃO é um
    python.exe - é o próprio binário do QGIS (qgis-bin.exe), porque o Python
    vem embutido nele. Nesse caso, `subprocess.Popen([sys.executable, ...])`
    abre uma SEGUNDA instância do QGIS, que interpreta nossos argumentos
    (script, "search"/"process", os .json) como arquivos para abrir como
    camada - exatamente o erro "Fonte de dados inválida" relatado. Por isso
    procuramos várias localizações prováveis de um python.exe/python3
    verdadeiro e confirmamos executando cada candidato antes de usá-lo."""
    global _PYTHON_EXE_CACHE
    if _PYTHON_EXE_CACHE:
        return _PYTHON_EXE_CACHE

    candidates = []
    if _looks_like_python(sys.executable):
        candidates.append(sys.executable)

    exe_dir = os.path.dirname(sys.executable)
    exec_prefix = sys.exec_prefix
    names = ["python3.exe", "python.exe"] if os.name == "nt" else ["python3", "python"]
    for base in (exec_prefix, exe_dir, os.path.join(exec_prefix, "bin"), os.path.join(exe_dir, "bin")):
        for name in names:
            candidates.append(os.path.join(base, name))

    which_names = ["python3.exe", "python.exe"] if os.name == "nt" else ["python3", "python"]
    for name in which_names:
        found = shutil.which(name)
        if found:
            candidates.append(found)

    seen = set()
    for cand in candidates:
        cand = os.path.normpath(cand)
        if cand in seen or not os.path.isfile(cand):
            continue
        seen.add(cand)
        try:
            r = subprocess.run(
                [cand, "-c", "print(1)"],
                capture_output=True, timeout=10, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if r.returncode == 0 and r.stdout.strip() == "1":
                _PYTHON_EXE_CACHE = cand
                return cand
        except Exception:
            continue

    raise RuntimeError(
        "Não foi possível localizar um interpretador Python válido nesta instalação "
        "do QGIS (sys.executable = '{}' não é um python.exe/python3 utilizável). "
        "Isso ocorre em instalações do QGIS onde o Python vem embutido no próprio "
        "executável do QGIS. Verifique se existe um python3.exe/python.exe na pasta "
        "de instalação do QGIS (ex.: .../apps/Python3XX/) ou instale um QGIS via "
        "OSGeo4W, que inclui um interpretador Python separado.".format(sys.executable))

class _Cancelled(Exception):
    pass

def _make_json_safe(obj):
    """Remove/converte qualquer coisa que json.dump não aceite (ex.: bytes)
    antes de escrever os parâmetros para o processo filho."""
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, bytes):
        return None
    return obj

class _SubprocessRunnerMixin:
    """Roda o pipeline (busca ou processamento) em um PROCESSO Python
    separado e isolado do processo do QGIS - ver core/subprocess_runner.py
    para o motivo. Esta thread (a própria thread da QgsTask) só faz I/O:
    escreve os parâmetros em disco, inicia o processo filho, lê a saída dele
    linha a linha por uma thread auxiliar (encaminhando cada linha de log
    para a caixa de diálogo) e, no fim, lê o resultado em JSON."""

    def _run_in_subprocess(self, mode, params):
        work_dir = tempfile.mkdtemp(prefix="cbers_wpm_ipc_")
        params_path = os.path.join(work_dir, "params.json")
        result_path = os.path.join(work_dir, "result.json")

        try:
            with open(params_path, "w", encoding="utf-8") as f:
                json.dump(_make_json_safe(params), f)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "Falha ao serializar os parâmetros para o processo filho: {}".format(exc))

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        proc = subprocess.Popen(
            [_resolve_python_executable(), RUNNER_SCRIPT, mode, params_path, result_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )
        self._proc = proc

        line_queue = queue.Queue()

        def _reader():
            try:
                for line in proc.stdout:
                    line_queue.put(line.rstrip("\n"))
            except Exception:
                pass
            finally:
                line_queue.put(None)

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        try:
            while True:
                if self.isCanceled():
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        proc.kill()
                    raise _Cancelled()
                try:
                    line = line_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                if line is None:
                    break
                if line.startswith("LOG: "):
                    self._log(line[5:])
                elif line.strip():
                    self._log(line)

            proc.wait()
            reader_thread.join(timeout=5)
        finally:
            self._proc = None

        if not os.path.exists(result_path):
            raise RuntimeError(
                "O processo de {} terminou sem gerar resultado (código de saída {}). "
                "Verifique o log acima para a causa.".format(
                    "busca" if mode == "search" else "processamento", proc.returncode))

        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        shutil.rmtree(work_dir, ignore_errors=True)
        return result

class CbersWpmTask(QgsTask, _SubprocessRunnerMixin):
    """Executa run_pipeline() em um processo separado (ver
    core/subprocess_runner.py), encaminhando mensagens de log para a caixa
    de diálogo através de sinais."""

    messageLogged = pyqtSignal(str)

    def __init__(self, description, params):
        super().__init__(description, QgsTask.CanCancel)
        self.params = params
        self.exception = None
        self.error_message = None
        self.outputs = []
        self._proc = None

    def _log(self, *args):
        self.messageLogged.emit(" ".join(str(a) for a in args))

    def run(self):
        try:
            result = self._run_in_subprocess("process", self.params)
        except _Cancelled:
            self.error_message = "Processamento cancelado pelo usuário."
            return False
        except Exception as exc:
            import traceback
            self.exception = exc
            self.error_message = "Erro inesperado: {}\n\n{}".format(exc, traceback.format_exc())
            return False

        if not result.get("ok"):
            self.error_message = result.get("error") or "Erro desconhecido no processamento."
            return False

        self.outputs = result.get("outputs", [])
        return True

    def cancel(self):
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:
                pass
        super().cancel()

    def finished(self, result):
        pass

class CbersWpmSearchTask(QgsTask, _SubprocessRunnerMixin):
    """Executa search_available_scenes() em um processo separado, para não
    travar a interface enquanto o STAC é consultado e as miniaturas (PNG)
    são baixadas - e para não arriscar derrubar o QGIS (ver
    core/subprocess_runner.py)."""

    messageLogged = pyqtSignal(str)

    def __init__(self, description, params):
        super().__init__(description, QgsTask.CanCancel)
        self.params = params
        self.exception = None
        self.error_message = None
        self.results = []
        self._proc = None

    def _log(self, *args):
        self.messageLogged.emit(" ".join(str(a) for a in args))

    def run(self):
        try:
            result = self._run_in_subprocess("search", self.params)
        except _Cancelled:
            self.error_message = "Busca cancelada pelo usuário."
            return False
        except Exception as exc:
            import traceback
            self.exception = exc
            self.error_message = "Erro inesperado: {}\n\n{}".format(exc, traceback.format_exc())
            return False

        if not result.get("ok"):
            self.error_message = result.get("error") or "Erro desconhecido na busca."
            return False

        self.results = result.get("results", [])
        return True

    def cancel(self):
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:
                pass
        super().cancel()

    def finished(self, result):
        pass
