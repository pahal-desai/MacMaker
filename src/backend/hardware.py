import platform
import psutil
import cpuinfo
import subprocess

os = platform.system()

def getspecs():
    specs = {
        "os": platform.platform(),
        "cpu": cpuinfo.get_cpu_info().get("brand_raw"),
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "architecture": platform.machine(),
    }

    if os == "Linux":
        specs["distro"] = platform.freedesktop_os_release()["PRETTY_NAME"]

    elif os == "Windows":
        import wmi
        computer = wmi.WMI()
        specs["motherboard"] = computer.Win32_BaseBoard()[0].Product

    elif os == "Darwin":
        result = subprocess.run(
            ["system_profiler", "SPHardwareDataType"],
            capture_output=True,
            text=True
        )
        specs["hardware_info"] = result.stdout

    return specs


if __name__ == "__main__":
    print(getspecs())