import platform
import psutil
import cpuinfo
import subprocess
import glob
import json

def runcmd(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return proc.stdout
    except Exception:
        return ""

def readfile(filepath):
    try:
        with open(filepath, "r") as file:
            return file.read().strip()
    except Exception:
        return ""

def getlinux():
    info = {}

    boardvendor = readfile("/sys/devices/virtual/dmi/id/board_vendor")
    boardname = readfile("/sys/devices/virtual/dmi/id/board_name")
    productname = readfile("/sys/devices/virtual/dmi/id/product_name")
    board = f"{boardvendor} {boardname}".strip()
    if not board and productname:
        board = productname
    info["motherboard"] = board or "Unknown"

    pci = runcmd(["lspci"])
    usb = runcmd(["lsusb"])

    gpulist = []
    for line in pci.splitlines():
        lower = line.lower()
        if "vga compatible controller:" in lower or "3d controller:" in lower or "display controller:" in lower:
            parts = line.split(":", 2)
            gpulist.append(parts[2].strip() if len(parts) >= 3 else line.strip())
    info["gpu"] = ", ".join(gpulist) if gpulist else "Unknown"

    ethlist = []
    for line in pci.splitlines():
        if "ethernet controller:" in line.lower():
            parts = line.split(":", 2)
            ethlist.append(parts[2].strip() if len(parts) >= 3 else line.strip())
    info["ethernet"] = ", ".join(ethlist) if ethlist else "Unknown"

    wifilist = []
    for line in pci.splitlines():
        lower = line.lower()
        if "network controller:" in lower or "wireless" in lower:
            parts = line.split(":", 2)
            wifilist.append(parts[2].strip() if len(parts) >= 3 else line.strip())
    for line in usb.splitlines():
        lower = line.lower()
        if ("wireless" in lower or "802.11" in lower or "wifi" in lower) and "bluetooth" not in lower:
            parts = line.split("ID ", 1)
            wifilist.append(parts[1].split(" ", 1)[1].strip() if len(parts) > 1 and " " in parts[1] else line.strip())
    info["wifi"] = ", ".join(wifilist) if wifilist else "Unknown"

    btlist = []
    for line in usb.splitlines():
        if "bluetooth" in line.lower():
            parts = line.split("ID ", 1)
            if len(parts) > 1 and " " in parts[1]:
                btlist.append(parts[1].split(" ", 1)[1].strip())
            else:
                btlist.append(line.strip())
    for line in pci.splitlines():
        if "bluetooth" in line.lower():
            parts = line.split(":", 2)
            btlist.append(parts[2].strip() if len(parts) >= 3 else line.strip())
    info["bluetooth"] = ", ".join(btlist) if btlist else "Unknown"

    audiolist = []
    for filepath in glob.glob("/proc/asound/card*/codec#*"):
        text = readfile(filepath)
        for line in text.splitlines():
            if line.startswith("Codec:"):
                audiolist.append(line.split(":", 1)[1].strip())
    if not audiolist:
        for line in pci.splitlines():
            lower = line.lower()
            if "audio device:" in lower or "audio:" in lower:
                parts = line.split(":", 2)
                audiolist.append(parts[2].strip() if len(parts) >= 3 else line.strip())
    info["audio"] = ", ".join(audiolist) if audiolist else "Unknown"

    return info

def getwindows():
    info = {}
    try:
        import wmi
        client = wmi.WMI()

        boards = []
        for item in client.Win32_BaseBoard():
            boards.append(f"{getattr(item, 'Manufacturer', '')} {getattr(item, 'Product', '')}".strip())
        info["motherboard"] = ", ".join(boards) or "Unknown"

        gpus = []
        for item in client.Win32_VideoController():
            name = getattr(item, "Name", "")
            if name:
                gpus.append(name.strip())
        info["gpu"] = ", ".join(gpus) or "Unknown"

        eth = []
        wifi = []
        for item in client.Win32_NetworkAdapter():
            if not getattr(item, "PhysicalAdapter", False):
                continue
            name = getattr(item, "Name", "")
            if not name:
                continue
            lower = name.lower()
            if "wireless" in lower or "wi-fi" in lower or "802.11" in lower or "wlan" in lower:
                wifi.append(name.strip())
            else:
                eth.append(name.strip())
        info["ethernet"] = ", ".join(eth) or "Unknown"
        info["wifi"] = ", ".join(wifi) or "Unknown"

        bts = []
        try:
            for item in client.Win32_PnPEntity(PNPClass="Bluetooth"):
                name = getattr(item, "Name", "")
                if name and "enumerator" not in name.lower():
                    bts.append(name.strip())
        except Exception:
            for item in client.Win32_PnPEntity():
                name = getattr(item, "Name", "")
                if "bluetooth" in name.lower() and "enumerator" not in name.lower():
                    bts.append(name.strip())
        info["bluetooth"] = ", ".join(bts) or "Unknown"

        audios = []
        for item in client.Win32_SoundDevice():
            name = getattr(item, "Name", "")
            if name:
                audios.append(name.strip())
        info["audio"] = ", ".join(audios) or "Unknown"

    except Exception:
        pass

    return info

def getdarwin():
    info = {}
    try:
        out = runcmd(["system_profiler", "SPHardwareDataType", "SPDisplaysDataType", "SPNetworkDataType", "SPAudioDataType", "SPBluetoothDataType"])
        info["hardware"] = out
    except Exception:
        pass
    return info

def getspecs():
    specs = {
        "os": platform.platform(),
        "cpu": cpuinfo.get_cpu_info().get("brand_raw") or platform.processor() or "Unknown",
        "ram": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "arch": platform.machine(),
    }

    currentos = platform.system()
    if currentos == "Linux":
        try:
            specs["distro"] = platform.freedesktop_os_release()["PRETTY_NAME"]
        except Exception:
            specs["distro"] = "Linux"
        extra = getlinux()
        specs.update(extra)

    elif currentos == "Windows":
        specs["distro"] = "Windows"
        extra = getwindows()
        specs.update(extra)

    elif currentos == "Darwin":
        specs["distro"] = "macOS"
        extra = getdarwin()
        specs.update(extra)

    return specs

if __name__ == "__main__":
    print(json.dumps(getspecs()))
