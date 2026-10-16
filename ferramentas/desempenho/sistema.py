"""Leituras do Windows para a medição (só ctypes, sem dependências): árvore de processos, tempo de CPU,
memória privada, afinidade de CPU (perfil P3) e contadores de GPU pelo PDH (nomes em inglês, que
funcionam no Windows em português)."""
import ctypes
import os
import re
import subprocess
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
pdh = ctypes.WinDLL("pdh")

QUERY_LIMITED = 0x1000
SET_INFORMATION = 0x0200
NCPU = os.cpu_count() or 1


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]


class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
k32.CloseHandle.argtypes = (wintypes.HANDLE,)
k32.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
k32.SetProcessAffinityMask.argtypes = (wintypes.HANDLE, ctypes.c_size_t)
psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD)
k32.Process32FirstW.argtypes = k32.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
for _f in ("PdhOpenQueryW", "PdhAddEnglishCounterW", "PdhCollectQueryData", "PdhGetFormattedCounterArrayW"):
    getattr(pdh, _f).restype = ctypes.c_uint32


def processos() -> dict[int, tuple[int, str]]:
    """pid -> (pai, nome do executável) de todos os processos."""
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)
    out = {}
    e = PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(e)
    try:
        ok = k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            out[e.th32ProcessID] = (e.th32ParentProcessID, e.szExeFile)
            ok = k32.Process32NextW(snap, ctypes.byref(e))
    finally:
        k32.CloseHandle(snap)
    return out


def arvore(raiz: int) -> dict[int, str]:
    """O processo `raiz` e todos os descendentes: pid -> nome."""
    todos = processos()
    filhos: dict[int, list[int]] = {}
    for pid, (pai, _n) in todos.items():
        filhos.setdefault(pai, []).append(pid)
    out, fila = {}, [raiz]
    while fila:
        p = fila.pop()
        if p in out or p not in todos and p != raiz:
            continue
        out[p] = todos.get(p, (0, "?"))[1]
        fila.extend(c for c in filhos.get(p, []) if c != p)
    return out


def _ft(f: wintypes.FILETIME) -> float:
    return ((f.dwHighDateTime << 32) | f.dwLowDateTime) / 1e7


def cpu_e_memoria(pid: int) -> tuple[float, float] | None:
    """(segundos de CPU desde que o processo abriu, memória privada em MB)."""
    h = k32.OpenProcess(QUERY_LIMITED, False, pid)
    if not h:
        return None
    try:
        c, x, kk, u = (wintypes.FILETIME() for _ in range(4))
        if not k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(x), ctypes.byref(kk), ctypes.byref(u)):
            return None
        m = PMC()
        m.cb = ctypes.sizeof(m)
        mem = m.PrivateUsage / 2 ** 20 if psapi.GetProcessMemoryInfo(h, ctypes.byref(m), m.cb) else 0.0
        return _ft(kk) + _ft(u), mem
    finally:
        k32.CloseHandle(h)


def afinidade(pid: int, mascara: int) -> bool:
    """Perfil P3: prende o processo a alguns núcleos lógicos (some quando o processo fecha)."""
    h = k32.OpenProcess(SET_INFORMATION | QUERY_LIMITED, False, pid)
    if not h:
        return False
    try:
        return bool(k32.SetProcessAffinityMask(h, mascara))
    finally:
        k32.CloseHandle(h)


def tipos(pids) -> dict[int, str]:
    """Tipo de cada processo do Chromium (renderer, gpu-process, utility...) pela linha de comando."""
    lista = ",".join(str(p) for p in pids)
    if not lista:
        return {}
    cmd = ("Get-CimInstance Win32_Process | Where-Object { @(" + lista + ") -contains $_.ProcessId } | "
           "ForEach-Object { '{0}|{1}' -f $_.ProcessId, $_.CommandLine }")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True,
                           timeout=60, creationflags=0x08000000)
    except Exception:
        return {}
    out = {}
    for linha in r.stdout.splitlines():
        if "|" not in linha:
            continue
        pid, cl = linha.split("|", 1)
        m = re.search(r"--type=([\w-]+)", cl)
        tipo = m.group(1) if m else "principal"
        if tipo == "utility":
            u = re.search(r"--utility-sub-type=([\w.]+)", cl)
            tipo = "utility:" + (u.group(1).split(".")[-1] if u else "?")
        out[int(pid)] = tipo
    return out


# ------------------------------------------------------------------ PDH (contadores de GPU)
class _VALOR(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("doubleValue", ctypes.c_double), ("largeValue", ctypes.c_longlong)]
    _fields_ = [("CStatus", wintypes.DWORD), ("u", _U)]


class _ITEM(ctypes.Structure):
    _fields_ = [("szName", wintypes.LPWSTR), ("FmtValue", _VALOR)]


PDH_FMT_DOUBLE, PDH_FMT_NOCAP100, PDH_MORE_DATA = 0x200, 0x8000, 0x800007D2
_PID = re.compile(r"pid_(\d+)_")


class ContadoresGpu:
    """Uso do motor 3D da GPU (%) e memória dedicada da GPU (MB) por processo. Se o Windows não tiver
    os contadores, `ok` fica False e as leituras vêm vazias."""

    def __init__(self):
        self.q = wintypes.HANDLE()
        self.ok = pdh.PdhOpenQueryW(None, 0, ctypes.byref(self.q)) == 0
        self.c_uso, self.c_mem = wintypes.HANDLE(), wintypes.HANDLE()
        if self.ok:
            self.ok = (pdh.PdhAddEnglishCounterW(self.q, "\\GPU Engine(*)\\Utilization Percentage", 0,
                                                 ctypes.byref(self.c_uso)) == 0 and
                       pdh.PdhAddEnglishCounterW(self.q, "\\GPU Process Memory(*)\\Dedicated Usage", 0,
                                                 ctypes.byref(self.c_mem)) == 0)
        if self.ok:
            pdh.PdhCollectQueryData(self.q)

    def _ler(self, contador) -> list[tuple[str, float]]:
        tam, n = wintypes.DWORD(0), wintypes.DWORD(0)
        r = pdh.PdhGetFormattedCounterArrayW(contador, PDH_FMT_DOUBLE | PDH_FMT_NOCAP100, ctypes.byref(tam),
                                             ctypes.byref(n), None)
        if r != PDH_MORE_DATA or not tam.value:
            return []
        buf = (ctypes.c_byte * tam.value)()
        if pdh.PdhGetFormattedCounterArrayW(contador, PDH_FMT_DOUBLE | PDH_FMT_NOCAP100, ctypes.byref(tam),
                                            ctypes.byref(n), buf) != 0:
            return []
        itens = ctypes.cast(buf, ctypes.POINTER(_ITEM))
        return [(itens[i].szName, itens[i].FmtValue.u.doubleValue) for i in range(n.value)
                if itens[i].FmtValue.CStatus in (0, 1)]

    def amostra(self, pids: set[int]) -> dict | None:
        """{'uso_3d': % somado, 'uso_total': % de todos os motores, 'mem_mb': MB dedicados}."""
        if not self.ok or pdh.PdhCollectQueryData(self.q) != 0:
            return None
        uso3d = usot = mem = 0.0
        for nome, v in self._ler(self.c_uso):
            m = _PID.search(nome or "")
            if m and int(m.group(1)) in pids:
                usot += v
                if "engtype_3D" in nome:
                    uso3d += v
        for nome, v in self._ler(self.c_mem):
            m = _PID.search(nome or "")
            if m and int(m.group(1)) in pids:
                mem += v / 2 ** 20
        return {"uso_3d": uso3d, "uso_total": usot, "mem_mb": mem}
