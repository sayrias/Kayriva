"""Read local runtime memory/CPU counters without extra dependencies."""
import os
import subprocess
from pathlib import Path


def snapshot():
    result={}
    try:
        values={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
        total=values['MemTotal']; used=total-values['MemAvailable']
        result.update(ram_used=used/1024**3,ram_total=total/1024**3,
                      ram_total_bytes=total,ram_available_bytes=total-used)
        proc=Path('/proc/self/status').read_text().splitlines()
        rss=next(int(line.split()[1])/1024 for line in proc if line.startswith('VmRSS:'))
        result['app_ram_mb']=rss
        fields=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
        result.update(cpu_total=sum(fields),cpu_idle=fields[3]+fields[4])
    except (OSError,ValueError,KeyError,StopIteration):
        if os.name=='nt':
            import ctypes
            class Memory(ctypes.Structure):
                _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ['total','available','page','free_page','virtual','free_virtual','extended']]
            mem=Memory(); mem.length=ctypes.sizeof(mem)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
                result.update(ram_used=(mem.total-mem.available)/1024**3,ram_total=mem.total/1024**3,
                              ram_total_bytes=mem.total,ram_available_bytes=mem.available)
    try:
        response=subprocess.run(['nvidia-smi','--query-gpu=memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=1)
        if response.returncode==0:
            used,total,load=map(float,response.stdout.splitlines()[0].split(','))
            result.update(vram_used=used/1024,vram_total=total/1024,gpu_load=load)
            result.update(vram_total_bytes=int(total*1024**2),vram_available_bytes=max(0,int((total-used)*1024**2)))
    except (OSError,ValueError,IndexError,subprocess.TimeoutExpired): pass
    return result
