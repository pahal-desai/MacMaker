import os
import sys
import re
import glob
import json
import shutil
import tempfile
import platform
import subprocess
import psutil
import cpuinfo

def emit(step, pct, msg):
    print(json.dumps({"type": "progress", "step": step, "pct": pct, "msg": msg}), flush=True)

def runcmd(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return proc.stdout
    except Exception:
        return ""

def readfile(filepath):
    try:
        with open(filepath, "r", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""

def setupopcore(cachedir):
    scriptsrc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opcore", "Scripts")
    scriptdst = os.path.join(cachedir, "Scripts")
    os.makedirs(cachedir, exist_ok=True)
    if not os.path.exists(scriptdst):
        shutil.copytree(scriptsrc, scriptdst)
    else:
        for root, dirs, files in os.walk(scriptsrc):
            rel = os.path.relpath(root, scriptsrc)
            dstdir = os.path.join(scriptdst, rel) if rel != "." else scriptdst
            os.makedirs(dstdir, exist_ok=True)
            for fname in files:
                srcf = os.path.join(root, fname)
                dstf = os.path.join(dstdir, fname)
                if not os.path.exists(dstf) or os.path.getmtime(srcf) > os.path.getmtime(dstf):
                    shutil.copy2(srcf, dstf)
    if cachedir not in sys.path:
        sys.path.insert(0, cachedir)
    return scriptdst

def pcipath(bdf):
    sysdev = f"/sys/bus/pci/devices/{bdf}"
    if os.path.exists(sysdev):
        real = os.path.realpath(sysdev)
        segs = re.findall(r"[0-9a-fA-F]{4}:([0-9a-fA-F]{2}):([0-9a-fA-F]{2})\.([0-9a-fA-F])", real)
        if segs:
            parts = ["PciRoot(0x0)"]
            for bus, dev, fn in segs:
                parts.append(f"Pci(0x{int(dev, 16):x},0x{int(fn, 16):x})")
            return "/".join(parts)
    match = re.search(r"([0-9a-fA-F]{2}):([0-9a-fA-F]{2})\.([0-9a-fA-F])", bdf)
    if match:
        return f"PciRoot(0x0)/Pci(0x{int(match.group(2), 16):x},0x{int(match.group(3), 16):x})"
    return "PciRoot(0x0)/Pci(0x0,0x0)"

def getcpucodename(brand, gpucodename, cpudata):
    low = brand.lower()
    if "intel" in low:
        if gpucodename and gpucodename != "Unknown":
            for gen in cpudata.IntelCPUGenerations:
                if gpucodename == gen or gen.startswith(gpucodename):
                    return gen
        match = re.search(r"(?:i[3579]|core[^\d]*ultra\s*[579]?)[-\s]+(\d{3,5})([a-z]*)", low)
        if match:
            num = match.group(1)
            suf = match.group(2)
            islap = any(x in suf for x in ("u", "h", "p", "g", "y"))
            if "ultra" in low:
                if num.startswith("2"):
                    return "Lunar Lake" if "v" in suf else "Arrow Lake-S"
                return "Meteor Lake-U" if "u" in suf else "Meteor Lake-H"
            if len(num) == 5:
                gennum = int(num[:2])
            elif len(num) == 4:
                gennum = int(num[0])
            else:
                gennum = 10
            if gennum >= 13:
                return "Raptor Lake-H" if "h" in suf else ("Raptor Lake-P" if "p" in suf else "Raptor Lake-S")
            if gennum == 12:
                return "Alder Lake-H" if "h" in suf else ("Alder Lake-P" if "p" in suf else ("Alder Lake-U" if "u" in suf else "Alder Lake-S"))
            if gennum == 11:
                return "Tiger Lake-H" if "h" in suf else ("Tiger Lake-UP3" if islap else "Rocket Lake-S")
            if gennum == 10:
                return "Ice Lake-U" if "g" in suf else ("Comet Lake-H" if "h" in suf else ("Comet Lake-U" if "u" in suf else "Comet Lake-S"))
            if gennum in (8, 9):
                return "Coffee Lake-U" if "u" in suf else ("Coffee Lake-H" if "h" in suf else "Coffee Lake-S")
            if gennum == 7:
                return "Kaby Lake-H" if "h" in suf else "Kaby Lake"
            if gennum == 6:
                return "Skylake"
            if gennum == 5:
                return "Broadwell-U" if "u" in suf else "Broadwell"
            if gennum == 4:
                return "Haswell-ULT" if "u" in suf else "Haswell"
            if gennum == 3:
                return "Ivy Bridge"
            if gennum == 2:
                return "Sandy Bridge"
        return "Comet Lake-S"
    if "amd" in low:
        match = re.search(r"ryzen\s+\d\s+(\d{4})([a-z]*)", low)
        if match:
            num = match.group(1)
            suf = match.group(2)
            gennum = int(num[0])
            if gennum == 9:
                return "Granite Ridge"
            if gennum == 8:
                return "Hawk Point"
            if gennum == 7:
                return "Phoenix" if ("hs" in suf or "u" in suf) else "Raphael"
            if gennum == 6:
                return "Rembrandt"
            if gennum == 5:
                return "Cezanne" if ("g" in suf or "u" in suf or "h" in suf) else "Vermeer"
            if gennum == 4:
                return "Renoir"
            if gennum == 3:
                return "Picasso" if "g" in suf else "Matisse"
            if gennum == 2:
                return "Raven Ridge" if "g" in suf else "Pinnacle Ridge"
            if gennum == 1:
                return "Summit Ridge"
        return "Vermeer"
    return "Comet Lake-S"

def getchipset(isabridge, codename, cpumfg, islaptop, chipsetdata):
    for chip in chipsetdata.IntelChipsets + chipsetdata.AMDChipsets:
        if chip.lower() in isabridge.lower():
            return chip
    if "AMD" in cpumfg:
        return "B550"
    if "Kaby Lake" in codename or "Skylake" in codename:
        return "Sunrise Point-LP" if islaptop else "Z270"
    if "Coffee Lake" in codename or "Whiskey Lake" in codename:
        return "Cannon Point-LP" if islaptop else "Z390"
    if "Comet Lake" in codename:
        return "Comet Lake"
    if "Ice Lake" in codename:
        return "Ice Lake-LP"
    if "Tiger Lake" in codename:
        return "Tiger Lake-LP"
    if "Alder Lake" in codename:
        return "Alder Lake"
    if "Raptor Lake" in codename:
        return "Z790"
    if "Haswell" in codename:
        return "Lynx Point"
    return "Comet Lake"

def guessgpucodename(mfg, did, name, gpudata):
    if mfg == "Intel":
        for gen, idset in gpudata.IntelGPUDeviceIDs.items():
            if did in idset:
                return gen
        if did in gpudata.WhateverXeDeviceIDs:
            return "Tiger Lake"
        return "Coffee Lake"
    low = name.lower()
    if mfg == "AMD":
        for code in gpudata.AMDCodenames:
            if code.lower() in low:
                return code
        if "rx 6" in low:
            return "Navi 21"
        if "rx 5" in low:
            return "Navi 10"
        if "rx 4" in low or "rx 580" in low or "rx 570" in low:
            return "Polaris 20"
        if "vega" in low:
            return "Vega 10"
        if "radeon" in low and "graphics" in low:
            return "Cezanne"
        return "Polaris 20"
    if mfg == "NVIDIA":
        if "rtx 40" in low:
            return "Ada Lovelace"
        if "rtx 30" in low:
            return "Ampere"
        if "rtx 20" in low or "gtx 16" in low:
            return "Turing"
        if "gtx 10" in low or "mx1" in low or "mx2" in low or "gp10" in low:
            return "Pascal"
        if "940" in low or "950" in low or "960" in low or "970" in low or "980" in low or "gm10" in low or "gm20" in low:
            return "Maxwell"
        if "gk10" in low or "gk20" in low or "gt 710" in low or "gtx 7" in low or "gtx 6" in low:
            return "Kepler"
        return "Maxwell"
    return "Unknown"

def getlinuxreport(gpudata, chipsetdata, cpudata):
    vendor = readfile("/sys/devices/virtual/dmi/id/board_vendor")
    name = readfile("/sys/devices/virtual/dmi/id/board_name")
    product = readfile("/sys/devices/virtual/dmi/id/product_name")
    boardname = f"{vendor} {name}".strip() or product or "Standard PC"

    bats = glob.glob("/sys/class/power_supply/BAT*")
    chassistype = readfile("/sys/class/dmi/id/chassis_type")
    islaptop = bool(bats) or chassistype in ("8", "9", "10", "11", "14", "30", "31", "32")

    fwtype = "UEFI" if os.path.exists("/sys/firmware/efi") else "BIOS"

    cpu = cpuinfo.get_cpu_info()
    brand = cpu.get("brand_raw") or platform.processor() or "Intel Core"
    cpumfg = "AMD" if "amd" in brand.lower() else "Intel"
    flags = [f.upper() for f in cpu.get("flags", [])]
    simdlist = []
    if "SSE4_1" in flags or "SSE4.1" in flags:
        simdlist.append("SSE4.1")
    if "SSE4_2" in flags or "SSE4.2" in flags:
        simdlist.append("SSE4.2")
    if "AVX2" in flags:
        simdlist.append("AVX2")
    if "AVX" in flags:
        simdlist.append("AVX")
    cores = str(psutil.cpu_count(logical=False) or 4)

    gpus = {}
    nets = {}
    bts = {}
    storages = {}
    usbs = {}
    sds = {}
    sysdevs = {}
    sounds = {}
    inputs = {}
    isabridge = ""
    audioctrlid = None
    firstgpucode = None

    pci = runcmd(["lspci", "-Dnn"])
    for line in pci.splitlines():
        match = re.match(r"^([0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F])\s+([^\[]+)\[([0-9a-fA-F]{4})\]:\s+(.+?)\s+\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]", line)
        if not match:
            continue
        bdf = match.group(1)
        clsname = match.group(2).strip().lower()
        clsid = match.group(3).lower()
        devdesc = match.group(4).strip()
        vid = match.group(5).upper()
        did = match.group(6).upper()
        devid = f"{vid}-{did}"
        ppath = pcipath(bdf)

        if "isa bridge" in clsname or clsid == "0601":
            isabridge = devdesc

        if clsid.startswith("03") or "vga" in clsname or "3d controller" in clsname or "display controller" in clsname:
            mfg = "Intel" if vid == "8086" else ("AMD" if vid == "1002" else ("NVIDIA" if vid == "10DE" else "Unknown"))
            gcode = guessgpucodename(mfg, did, devdesc, gpudata)
            dtype = "Integrated GPU" if (mfg == "Intel" or ("amd" in mfg.lower() and not firstgpucode and "graphics" in devdesc.lower())) else "Discrete GPU"
            if mfg == "Intel":
                firstgpucode = gcode
            gpus[devdesc] = {
                "Manufacturer": mfg,
                "Codename": gcode,
                "Device ID": devid,
                "Device Type": dtype,
                "PCI Path": ppath
            }
        elif "ethernet" in clsname or "network" in clsname or "wireless" in clsname or clsid.startswith("02"):
            nets[devdesc] = {
                "Bus Type": "PCI",
                "Device ID": devid,
                "PCI Path": ppath
            }
        elif "nvme" in clsname or "sata" in clsname or "ahci" in clsname or "non-volatile memory" in clsname or clsid.startswith("01"):
            storages[devdesc] = {
                "Bus Type": "PCI",
                "Device ID": devid,
                "PCI Path": ppath,
                "Disk Drives": ["System Drive"]
            }
        elif "usb controller" in clsname or clsid == "0c03":
            usbs[devdesc] = {
                "Bus Type": "PCI",
                "Device ID": devid,
                "PCI Path": ppath
            }
        elif "sd host" in clsname or "card reader" in clsname or clsid == "0805":
            sds[devdesc] = {
                "Bus Type": "PCI",
                "Device ID": devid,
                "PCI Path": ppath
            }
        elif "audio" in clsname or clsid == "0403":
            if not audioctrlid and vid == "8086":
                audioctrlid = devid
            sysdevs[devdesc] = {
                "Bus Type": "PCI",
                "Device ID": devid,
                "PCI Path": ppath
            }
        else:
            sysdevs[devdesc] = {
                "Bus Type": "PCI",
                "Device ID": devid,
                "PCI Path": ppath
            }

    for filepath in glob.glob("/proc/asound/card*/codec#*"):
        text = readfile(filepath)
        cname = ""
        cid = ""
        for line in text.splitlines():
            if line.startswith("Codec:") and not cname:
                cname = line.split(":", 1)[1].strip()
            if line.lower().startswith("vendor id:"):
                m = re.search(r"0x([0-9a-fA-F]{4})([0-9a-fA-F]{4})", line)
                if m:
                    cid = f"{m.group(1).upper()}-{m.group(2).upper()}"
        if cid:
            entry = {
                "Bus Type": "HDAUDIO",
                "Device ID": cid
            }
            if audioctrlid:
                entry["Controller Device ID"] = audioctrlid
            sounds[cname or cid] = entry

    usb = runcmd(["lsusb"])
    for line in usb.splitlines():
        if "bluetooth" in line.lower():
            m = re.search(r"ID\s+([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s+(.*)", line)
            if m:
                btid = f"{m.group(1).upper()}-{m.group(2).upper()}"
                btname = m.group(3).strip() or btid
                bts[btname] = {
                    "Bus Type": "USB",
                    "Device ID": btid
                }

    inputdevs = readfile("/proc/bus/input/devices")
    for block in inputdevs.split("\n\n"):
        if "i8042" in block.lower() or "ps/2" in block.lower() or "at translated set 2" in block.lower():
            inputs["PS2 Keyboard"] = {"Bus Type": "ACPI", "Device": "PNP0303", "Device Type": "PS/2 Keyboard"}
        if "i2c" in block.lower() and ("touchpad" in block.lower() or "elan" in block.lower() or "synaptics" in block.lower()):
            inputs["I2C Touchpad"] = {"Bus Type": "ACPI", "Device": "ELAN0000", "Device Type": "I2C Touchpad"}

    if not storages:
        storages["Standard AHCI Controller"] = {
            "Bus Type": "PCI",
            "Device ID": "8086-A102",
            "PCI Path": "PciRoot(0x0)/Pci(0x17,0x0)",
            "Disk Drives": ["System Drive"]
        }

    if not gpus:
        gpus["Standard Graphics"] = {
            "Manufacturer": "Intel",
            "Codename": "Coffee Lake",
            "Device ID": "8086-3E9B",
            "Device Type": "Integrated GPU",
            "PCI Path": "PciRoot(0x0)/Pci(0x2,0x0)"
        }

    codename = getcpucodename(brand, firstgpucode, cpudata)
    chipset = getchipset(isabridge, codename, cpumfg, islaptop, chipsetdata)

    primarygpu = next((k for k, v in gpus.items() if v.get("Device Type") == "Integrated GPU"), next(iter(gpus)))
    monitors = {
        "Monitor 1": {
            "Connector Type": "Internal" if islaptop else "HDMI",
            "Resolution": "1920x1080",
            "Connected GPU": primarygpu
        }
    }

    return {
        "Motherboard": {
            "Name": boardname,
            "Chipset": chipset,
            "Platform": "Laptop" if islaptop else "Desktop"
        },
        "BIOS": {
            "Firmware Type": fwtype,
            "Secure Boot": "Disabled"
        },
        "CPU": {
            "Manufacturer": cpumfg,
            "Processor Name": brand,
            "Codename": codename,
            "Core Count": cores,
            "CPU Count": "1",
            "SIMD Features": ", ".join(simdlist) or "SSE4.1, SSE4.2"
        },
        "GPU": gpus,
        "Monitor": monitors,
        "Network": nets,
        "Sound": sounds,
        "USB Controllers": usbs,
        "Input": inputs,
        "Storage Controllers": storages,
        "Bluetooth": bts,
        "SD Controller": sds,
        "System Devices": sysdevs
    }

def getwinreport(gpudata, chipsetdata, cpudata):
    import wmi
    client = wmi.WMI()

    boards = []
    for item in client.Win32_BaseBoard():
        boards.append(f"{getattr(item, 'Manufacturer', '')} {getattr(item, 'Product', '')}".strip())
    boardname = ", ".join(boards) or "Standard PC"

    bats = list(client.Win32_Battery())
    islaptop = bool(bats)

    cpu = cpuinfo.get_cpu_info()
    brand = cpu.get("brand_raw") or platform.processor() or "Intel Core"
    cpumfg = "AMD" if "amd" in brand.lower() else "Intel"
    flags = [f.upper() for f in cpu.get("flags", [])]
    simdlist = []
    if "SSE4_1" in flags or "SSE4.1" in flags:
        simdlist.append("SSE4.1")
    if "SSE4_2" in flags or "SSE4.2" in flags:
        simdlist.append("SSE4.2")
    if "AVX2" in flags:
        simdlist.append("AVX2")
    cores = str(psutil.cpu_count(logical=False) or 4)

    gpus = {}
    firstgpucode = None
    for item in client.Win32_VideoController():
        name = getattr(item, "Name", "") or "Display Adapter"
        pnp = getattr(item, "PNPDeviceID", "") or ""
        m = re.search(r"VEN_([0-9A-Fa-f]{4})&DEV_([0-9A-Fa-f]{4})", pnp)
        if not m:
            continue
        vid = m.group(1).upper()
        did = m.group(2).upper()
        mfg = "Intel" if vid == "8086" else ("AMD" if vid == "1002" else ("NVIDIA" if vid == "10DE" else "Unknown"))
        gcode = guessgpucodename(mfg, did, name, gpudata)
        dtype = "Integrated GPU" if mfg == "Intel" else "Discrete GPU"
        if mfg == "Intel":
            firstgpucode = gcode
        gpus[name] = {
            "Manufacturer": mfg,
            "Codename": gcode,
            "Device ID": f"{vid}-{did}",
            "Device Type": dtype,
            "PCI Path": "PciRoot(0x0)/Pci(0x2,0x0)" if mfg == "Intel" else "PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0)"
        }

    nets = {}
    for item in client.Win32_NetworkAdapter():
        if not getattr(item, "PhysicalAdapter", False):
            continue
        name = getattr(item, "Name", "") or ""
        pnp = getattr(item, "PNPDeviceID", "") or ""
        m = re.search(r"VEN_([0-9A-Fa-f]{4})&DEV_([0-9A-Fa-f]{4})", pnp)
        if m and name:
            nets[name] = {
                "Bus Type": "PCI",
                "Device ID": f"{m.group(1).upper()}-{m.group(2).upper()}"
            }

    bts = {}
    sounds = {}
    storages = {}
    usbs = {}
    sysdevs = {}
    audioctrlid = None

    for item in client.Win32_PnPEntity():
        name = getattr(item, "Name", "") or ""
        pnp = getattr(item, "PNPDeviceID", "") or ""
        cls = (getattr(item, "PNPClass", "") or "").lower()
        if "bluetooth" in cls and "USB\\VID_" in pnp.upper():
            m = re.search(r"VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})", pnp)
            if m:
                bts[name or "Bluetooth"] = {"Bus Type": "USB", "Device ID": f"{m.group(1).upper()}-{m.group(2).upper()}"}
        elif "HDAUDIO\\FUNC_01" in pnp.upper():
            m = re.search(r"VEN_([0-9A-Fa-f]{4})&DEV_([0-9A-Fa-f]{4})", pnp)
            if m:
                sounds[name or "Audio Codec"] = {"Bus Type": "HDAUDIO", "Device ID": f"{m.group(1).upper()}-{m.group(2).upper()}"}
        elif pnp.upper().startswith("PCI\\"):
            m = re.search(r"VEN_([0-9A-Fa-f]{4})&DEV_([0-9A-Fa-f]{4})", pnp)
            if not m:
                continue
            devid = f"{m.group(1).upper()}-{m.group(2).upper()}"
            low = name.lower()
            if "nvme" in low or "ahci" in low or "sata" in low or "hdc" in cls or "scsiadapter" in cls:
                storages[name or devid] = {"Bus Type": "PCI", "Device ID": devid, "Disk Drives": ["System Drive"]}
            elif "usb" in cls or "xhci" in low or "ehci" in low:
                usbs[name or devid] = {"Bus Type": "PCI", "Device ID": devid}
            elif "audio" in low or "high definition" in low:
                if not audioctrlid:
                    audioctrlid = devid
                sysdevs[name or devid] = {"Bus Type": "PCI", "Device ID": devid, "PCI Path": "PciRoot(0x0)/Pci(0x1f,0x3)"}

    if audioctrlid:
        for sprops in sounds.values():
            sprops["Controller Device ID"] = audioctrlid

    if not storages:
        storages["Standard AHCI Controller"] = {
            "Bus Type": "PCI",
            "Device ID": "8086-A102",
            "Disk Drives": ["System Drive"]
        }

    if not gpus:
        gpus["Standard Graphics"] = {
            "Manufacturer": "Intel",
            "Codename": "Coffee Lake",
            "Device ID": "8086-3E9B",
            "Device Type": "Integrated GPU",
            "PCI Path": "PciRoot(0x0)/Pci(0x2,0x0)"
        }

    codename = getcpucodename(brand, firstgpucode, cpudata)
    chipset = getchipset("", codename, cpumfg, islaptop, chipsetdata)
    primarygpu = next((k for k, v in gpus.items() if v.get("Device Type") == "Integrated GPU"), next(iter(gpus)))

    return {
        "Motherboard": {
            "Name": boardname,
            "Chipset": chipset,
            "Platform": "Laptop" if islaptop else "Desktop"
        },
        "BIOS": {
            "Firmware Type": "UEFI",
            "Secure Boot": "Disabled"
        },
        "CPU": {
            "Manufacturer": cpumfg,
            "Processor Name": brand,
            "Codename": codename,
            "Core Count": cores,
            "CPU Count": "1",
            "SIMD Features": ", ".join(simdlist) or "SSE4.1, SSE4.2"
        },
        "GPU": gpus,
        "Monitor": {
            "Monitor 1": {
                "Connector Type": "Internal" if islaptop else "HDMI",
                "Resolution": "1920x1080",
                "Connected GPU": primarygpu
            }
        },
        "Network": nets,
        "Sound": sounds,
        "USB Controllers": usbs,
        "Input": {"PS2 Keyboard": {"Bus Type": "ACPI", "Device": "PNP0303", "Device Type": "PS/2 Keyboard"}} if islaptop else {},
        "Storage Controllers": storages,
        "Bluetooth": bts,
        "SD Controller": {},
        "System Devices": sysdevs
    }

def loadacpi(ac):
    if platform.system() == "Linux":
        dsdt = "/sys/firmware/acpi/tables/DSDT"
        if os.path.exists(dsdt) and os.access(dsdt, os.R_OK):
            tmp = tempfile.mkdtemp(prefix="macmaker_acpi_")
            try:
                for fname in os.listdir("/sys/firmware/acpi/tables"):
                    fpath = os.path.join("/sys/firmware/acpi/tables", fname)
                    if os.path.isfile(fpath) and os.access(fpath, os.R_OK):
                        shutil.copy2(fpath, os.path.join(tmp, f"{fname}.aml"))
                ac.read_acpi_tables(tmp)
                return bool(ac.dsdt)
            except Exception:
                pass
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    elif platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\ACPI\DSDT")
            sub = winreg.EnumKey(key, 0)
            k2 = winreg.OpenKey(key, sub)
            sub2 = winreg.EnumKey(k2, 0)
            k3 = winreg.OpenKey(k2, sub2)
            sub3 = winreg.EnumKey(k3, 0)
            k4 = winreg.OpenKey(k3, sub3)
            data, _ = winreg.QueryValueEx(k4, "00000000")
            tmp = tempfile.mkdtemp(prefix="macmaker_acpi_")
            try:
                with open(os.path.join(tmp, "DSDT.aml"), "wb") as f:
                    f.write(data)
                ac.read_acpi_tables(tmp)
                return bool(ac.dsdt)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass
    return False

def patchutils(utilsmod):
    def fakeinput(self, prompt="Press Enter to continue..."):
        low = str(prompt).lower()
        if "uefi" in low:
            return "yes"
        if "force load" in low:
            return "no"
        if "combination" in low or "which" in low:
            return "1"
        return ""

    def noop(*args, **kwargs):
        return None

    def failout(self):
        raise RuntimeError("Hardware not supported for OpenCore EFI generation.")

    utilsmod.Utils.request_input = fakeinput
    utilsmod.Utils.head = noop
    utilsmod.Utils.adjust_window_size = noop
    utilsmod.Utils.progress_bar = noop
    utilsmod.Utils.exit_program = failout

def copyusbkexts(kextsdir, efikextsdir):
    utbmap = os.path.join(kextsdir, "UTBMap.kext")
    utbkext = os.path.join(kextsdir, "USBToolBox.kext")
    added = []
    if os.path.isdir(utbmap):
        shutil.copytree(utbmap, os.path.join(efikextsdir, "UTBMap.kext"), dirs_exist_ok=True)
        added.append("UTBMap.kext")
    if os.path.isdir(utbkext):
        shutil.copytree(utbkext, os.path.join(efikextsdir, "USBToolBox.kext"), dirs_exist_ok=True)
        added.append("USBToolBox.kext")
    return added

def buildefi():
    basedir = os.environ.get("MACMAKERDIR") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
    cachedir = os.environ.get("MACMAKERCACHE") or os.path.join(os.path.expanduser("~"), ".cache", "macmaker")
    kextsdir = os.path.join(basedir, "kexts")
    outroot = os.path.join(basedir, ".efibuild")
    finalefi = os.path.join(basedir, "EFI")

    emit(1, 10, "Setting up OpCore Simplify modules...")
    setupopcore(cachedir)

    from Scripts import utils
    patchutils(utils)

    from Scripts.datasets import os_data
    from Scripts.datasets import gpu_data
    from Scripts.datasets import chipset_data
    from Scripts.datasets import cpu_data
    from Scripts.datasets import kext_data
    from Scripts import compatibility_checker
    from Scripts import hardware_customizer
    from Scripts import smbios
    from Scripts import acpi_guru
    from Scripts import kext_maestro
    from Scripts import gathering_files
    from Scripts import config_prodigy

    emit(2, 20, "Collecting hardware report...")
    if platform.system() == "Windows":
        report = getwinreport(gpu_data, chipset_data, cpu_data)
    else:
        report = getlinuxreport(gpu_data, chipset_data, cpu_data)

    u = utils.Utils("MacMaker")
    cc = compatibility_checker.CompatibilityChecker()
    hc = hardware_customizer.HardwareCustomizer()
    sm = smbios.SMBIOS()
    ac = acpi_guru.ACPIGuru()
    km = kext_maestro.KextMaestro()
    gf = gathering_files.gatheringFiles()
    co = config_prodigy.ConfigProdigy()

    ockdir = os.path.join(cachedir, "OCK_Files")
    for obj in (gf, km, sm.g, co.g):
        obj.ock_files_dir = ockdir
    gf.download_history_file = os.path.join(ockdir, "history.json")
    co.g.download_history_file = os.path.join(ockdir, "history.json")
    sm.g.download_history_file = os.path.join(ockdir, "history.json")
    scriptdir = os.path.join(cachedir, "Scripts")
    sm.script_dir = scriptdir
    co.smbios.script_dir = scriptdir
    ac.smbios.script_dir = scriptdir

    emit(3, 30, "Analyzing hardware compatibility with OpCore Simplify...")
    report, nativever, oclpver, suggestedver = cc.check_compatibility(report)

    hasigpu = any(g.get("Device Type") == "Integrated GPU" for g in report.get("GPU", {}).values())
    islap = report.get("Motherboard", {}).get("Platform") == "Laptop"
    if islap and hasigpu:
        for gname, gprops in report.get("GPU", {}).items():
            if gprops.get("Device Type") == "Discrete GPU" and gprops.get("Manufacturer") == "NVIDIA":
                gprops["Compatibility"] = (None, None)
                gprops.pop("OCLP Compatibility", None)
        igpucompat = [g.get("Compatibility") for g in report.get("GPU", {}).values() if g.get("Compatibility") != (None, None)]
        if igpucompat:
            cc.max_native_macos_version = max(x[0] for x in igpucompat)
            cc.min_native_macos_version = min(x[1] for x in igpucompat)
            suggestedver = cc.get_suggested_macos_version()

    macosver = suggestedver or nativever[1]

    origselect = hc._select_device
    def pickdevice(devtype, devices, devgroups=None):
        if devtype == "GPU" and len(devices) > 1:
            amd = [k for k, v in devices.items() if v.get("Manufacturer") == "AMD" and v.get("Device Type") == "Discrete GPU"]
            if amd:
                return [amd[0]]
            igpu = [k for k, v in devices.items() if v.get("Device Type") == "Integrated GPU"]
            if igpu:
                return [igpu[0]]
        return [next(iter(devices))]
    hc._select_device = pickdevice

    customhw, disableddevs, needsoclp = hc.hardware_customization(report, macosver)
    smbiosmodel = sm.select_smbios_model(customhw, macosver)

    hasdsdt = loadacpi(ac)
    ac.select_acpi_patches(customhw, disableddevs)
    needsoclp = km.select_required_kexts(customhw, macosver, needsoclp, ac.patches)
    sm.smbios_specific_options(customhw, smbiosmodel, macosver, ac.patches, km)

    utbmap = os.path.join(kextsdir, "UTBMap.kext")
    if os.path.isdir(utbmap):
        utbidx = kext_data.kext_index_by_name.get("UTBDefault")
        if utbidx is not None:
            km.uncheck_kext(utbidx)

    emit(4, 45, "Downloading OpenCorePkg and required kexts...")
    gf.gather_bootloader_kexts(km.kexts, macosver)

    emit(5, 70, "Building OpenCore EFI folder...")
    u.create_folder(outroot, remove_content=True)
    sourceefi = os.path.join(ockdir, "OpenCorePkg")
    shutil.copytree(sourceefi, outroot, dirs_exist_ok=True)

    cfgfile = os.path.join(outroot, "EFI", "OC", "config.plist")
    cfgdata = u.read_file(cfgfile)

    cfgdata["ACPI"]["Add"] = []
    cfgdata["ACPI"]["Delete"] = []
    cfgdata["ACPI"]["Patch"] = []

    if hasdsdt:
        ac.hardware_report = customhw
        ac.disabled_devices = disableddevs
        ac.acpi_directory = os.path.join(outroot, "EFI", "OC", "ACPI")
        ac.smbios_model = smbiosmodel
        ac.lpc_bus_device = ac.get_lpc_name()
        for patch in ac.patches:
            if patch.checked:
                if patch.name == "BATP":
                    patch.checked = getattr(ac, patch.function_name)()
                    ecidx = kext_data.kext_index_by_name.get("ECEnabler")
                    if ecidx is not None:
                        km.kexts[ecidx].checked = patch.checked
                    continue
                acpiload = getattr(ac, patch.function_name)()
                if isinstance(acpiload, dict):
                    cfgdata["ACPI"]["Add"].extend(acpiload.get("Add", []))
                    cfgdata["ACPI"]["Delete"].extend(acpiload.get("Delete", []))
                    cfgdata["ACPI"]["Patch"].extend(acpiload.get("Patch", []))
        cfgdata["ACPI"]["Patch"].extend(ac.dsdt_patches)
        cfgdata["ACPI"]["Patch"] = ac.apply_acpi_patches(cfgdata["ACPI"]["Patch"])
    else:
        ac.hardware_report = customhw
        ac.acpi_directory = os.path.join(outroot, "EFI", "OC", "ACPI")
        try:
            usbx = ac.add_usb_power_properties()
            if isinstance(usbx, dict):
                cfgdata["ACPI"]["Add"].extend(usbx.get("Add", []))
        except Exception:
            pass

    emit(6, 82, "Installing kexts and USB map into config.plist...")
    efikextsdir = os.path.join(outroot, "EFI", "OC", "Kexts")
    km.install_kexts_to_efi(macosver, efikextsdir)
    copyusbkexts(kextsdir, efikextsdir)
    cfgdata["Kernel"]["Add"] = km.load_kexts(customhw, macosver, efikextsdir)

    emit(7, 90, "Generating SMBIOS and config.plist...")
    co.genarate(customhw, disableddevs, smbiosmodel, macosver, needsoclp, km.kexts, cfgdata)
    u.write_file(cfgfile, cfgdata)

    emit(8, 95, "Cleaning up unused drivers and tools...")
    toremove = []
    drvdir = os.path.join(outroot, "EFI", "OC", "Drivers")
    drvlist = u.find_matching_paths(drvdir, extension_filter=".efi")
    drvload = [d.get("Path") for d in cfgdata.get("UEFI", {}).get("Drivers", [])]
    for drvpath, _ in drvlist:
        if drvpath not in drvload:
            toremove.append(os.path.join(drvdir, drvpath))

    audiodir = os.path.join(outroot, "EFI", "OC", "Resources", "Audio")
    if os.path.exists(audiodir):
        toremove.append(audiodir)

    picker = cfgdata.get("Misc", {}).get("Boot", {}).get("PickerVariant")
    if picker in (None, "Auto"):
        picker = "Acidanthera/GoldenGate"
    if os.name == "nt":
        picker = picker.replace("/", "\\")

    imgdir = os.path.join(outroot, "EFI", "OC", "Resources", "Image")
    variants = u.find_matching_paths(imgdir, type_filter="dir")
    for vname, _ in variants:
        vpath = os.path.join(imgdir, vname)
        if ".icns" in ", ".join(os.listdir(vpath)):
            if picker not in vname:
                toremove.append(vpath)

    tooldir = os.path.join(outroot, "EFI", "OC", "Tools")
    toollist = u.find_matching_paths(tooldir, extension_filter=".efi")
    toolload = [t.get("Path") for t in cfgdata.get("Misc", {}).get("Tools", [])]
    for toolpath, _ in toollist:
        if toolpath not in toolload:
            toremove.append(os.path.join(tooldir, toolpath))

    manifest = os.path.join(outroot, "manifest.json")
    if os.path.exists(manifest):
        toremove.append(manifest)

    for fpath in toremove:
        try:
            if os.path.isdir(fpath):
                shutil.rmtree(fpath)
            elif os.path.exists(fpath):
                os.remove(fpath)
        except Exception:
            pass

    if os.path.exists(finalefi):
        shutil.rmtree(finalefi)
    shutil.move(os.path.join(outroot, "EFI"), finalefi)
    shutil.rmtree(outroot, ignore_errors=True)

    enabledkexts = []
    for k in cfgdata.get("Kernel", {}).get("Add", []):
        if k.get("Enabled"):
            bpath = k.get("BundlePath", "")
            enabledkexts.append(bpath)

    macosname = os_data.get_macos_name_by_darwin(macosver) or f"macOS ({macosver})"

    try:
        os.makedirs(cachedir, exist_ok=True)
        with open(os.path.join(cachedir, "lastefi.json"), "w") as mf:
            json.dump({"darwin": macosver[:2], "macos": macosname, "smbios": smbiosmodel}, mf)
    except Exception:
        pass

    res = {
        "type": "done",
        "status": "success",
        "path": finalefi,
        "smbios": smbiosmodel,
        "macos": macosname,
        "board": customhw.get("Motherboard", {}).get("Name", "PC"),
        "chipset": customhw.get("Motherboard", {}).get("Chipset", ""),
        "kexts": enabledkexts,
        "acpicount": len(cfgdata.get("ACPI", {}).get("Add", [])),
        "hasdsdt": hasdsdt
    }
    print(json.dumps(res), flush=True)

if __name__ == "__main__":
    buildefi()
