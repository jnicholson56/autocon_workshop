# psutil.cpu_freq() returns None on some ARM VMs, which crashes SuzieQ's start-up logging.
import psutil

_cpu_freq = psutil.cpu_freq


def cpu_freq(percpu=False):
    return _cpu_freq(percpu) or psutil._common.scpufreq(0.0, 0.0, 0.0)


psutil.cpu_freq = cpu_freq
