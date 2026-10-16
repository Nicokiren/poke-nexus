"""Memória de um processo do Windows (só leitura), sem dependências: usada para vigiar os
processos de página do Qt WebEngine (um por conta)."""
import ctypes
import os
from ctypes import wintypes


class _PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


_QUERY_LIMITED = 0x1000

if os.name == "nt":
    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _psapi = ctypes.WinDLL("psapi", use_last_error=True)
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(_PMC), wintypes.DWORD)


def memoria_privada_mb(pid: int) -> float | None:
    """Memória privada (commit) do processo em MB, ou None se não deu para ler."""
    if os.name != "nt" or not pid:
        return None
    h = _k32.OpenProcess(_QUERY_LIMITED, False, int(pid))
    if not h:
        return None
    try:
        c = _PMC()
        c.cb = ctypes.sizeof(c)
        if not _psapi.GetProcessMemoryInfo(h, ctypes.byref(c), c.cb):
            return None
        return c.PrivateUsage / (1024 * 1024)
    finally:
        _k32.CloseHandle(h)
