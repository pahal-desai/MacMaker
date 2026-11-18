import os
import sys
import json
import glob
import re
import platform
import subprocess
import cpuinfo

basepath = os.path.dirname(os.path.abspath(__file__))
if basepath not in sys.path:
    sys.path.insert(0, basepath)

from datasets import os_data
from datasets import gpu_data
from datasets import pci_data
from datasets import codec_layouts

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

def getcpu():
    info = cpuinfo.get_cpu_info()
    brand = info.get("brand_raw") or platform.processor() or "Unknown CPU"
    flags = info.get("flags", [])
    lowerflags = [item.lower() for item in flags]

    hasse41 = any("sse4_1" in item or "sse4.1" in item for item in lowerflags)
    hasse42 = any("sse4_2" in item or "sse4.2" in item for item in lowerflags)

    score = 0
    status = "Unsupported"
    color = "bad"
    notes = "Missing SSE4 instructions required by macOS"
    maxos = "17.99.99"

    if hasse42:
        score = 25
        status = "Supported"
        color = "good"
        notes = "Full support with SSE4.2 and modern CPU instructions"
        maxos = "24.99.99"
    elif hasse41:
        score = 15
        status = "Limited"
        color = "warn"
        notes = "Supports up to macOS Monterey with SSE4.1"
        maxos = "21.99.99"

    return {
        "name": "CPU",
        "model": brand,
        "status": status,
        "color": color,
        "notes": notes,
        "score": score,
        "maxos": maxos
    }

def getgpu(pciids):
    items = []
    bestscore = 0
    bestmacos = "17.99.99"

    for vid, did, line in pciids:
        lower = line.lower()
        if "vga compatible controller" in lower or "3d controller" in lower or "display controller" in lower or "video" in lower:
            gpuname = line.split(":", 2)[-1].strip() if ":" in line else line

            if vid == "8086":
                foundgen = None
                for genname, idset in gpu_data.IntelGPUDeviceIDs.items():
                    if did in idset:
                        foundgen = genname
                        break

                if foundgen in ("Kaby Lake", "Coffee Lake", "Comet Lake"):
                    items.append({
                        "name": "GPU (Intel)",
                        "model": gpuname,
                        "status": "Supported",
                        "color": "good",
                        "notes": f"Intel {foundgen} iGPU has native acceleration up to macOS Ventura 13",
                        "score": 30,
                        "maxos": "22.99.99"
                    })
                elif foundgen in ("Skylake", "Haswell", "Broadwell", "Ivy Bridge"):
                    items.append({
                        "name": "GPU (Intel)",
                        "model": gpuname,
                        "status": "Supported",
                        "color": "good",
                        "notes": f"Intel {foundgen} iGPU supported natively up to macOS Monterey 12",
                        "score": 28,
                        "maxos": "21.99.99"
                    })
                elif foundgen == "Ice Lake":
                    items.append({
                        "name": "GPU (Intel)",
                        "model": gpuname,
                        "status": "Supported",
                        "color": "good",
                        "notes": "Intel Ice Lake iGPU supported natively up to macOS Ventura 13",
                        "score": 30,
                        "maxos": "22.99.99"
                    })
                elif did in gpu_data.WhateverXeDeviceIDs:
                    items.append({
                        "name": "GPU (Intel)",
                        "model": gpuname,
                        "status": "Patch Required",
                        "color": "warn",
                        "notes": "Intel 11th-14th Gen iGPU requires WhateverXe or custom framebuffer",
                        "score": 15,
                        "maxos": "22.99.99"
                    })
                else:
                    items.append({
                        "name": "GPU (Intel)",
                        "model": gpuname,
                        "status": "Limited",
                        "color": "warn",
                        "notes": "Intel graphics without native acceleration",
                        "score": 10,
                        "maxos": "17.99.99"
                    })

            elif vid == "1002":
                items.append({
                    "name": "GPU (AMD)",
                    "model": gpuname,
                    "status": "Supported",
                    "color": "good",
                    "notes": "AMD Radeon GPU supported natively in modern macOS",
                    "score": 30,
                    "maxos": "24.99.99"
                })

            elif vid == "10DE":
                items.append({
                    "name": "GPU (NVIDIA)",
                    "model": gpuname,
                    "status": "Turned Off in macOS",
                    "color": "info",
                    "notes": "NVIDIA Optimus dGPU will be disabled via SSDT (laptop uses Intel iGPU smoothly)",
                    "score": 0,
                    "maxos": "17.99.99"
                })

    for item in items:
        if item["score"] > bestscore:
            bestscore = item["score"]
            bestmacos = item["maxos"]

    if not items:
        items.append({
            "name": "GPU",
            "model": "Integrated Graphics",
            "status": "Compatible",
            "color": "good",
            "notes": "Standard integrated graphics detected",
            "score": 20,
            "maxos": "21.99.99"
        })
        bestscore = 20
        bestmacos = "21.99.99"

    return items, bestscore, bestmacos

def getmotherboard():
    vendor = readfile("/sys/devices/virtual/dmi/id/board_vendor")
    name = readfile("/sys/devices/virtual/dmi/id/board_name")
    product = readfile("/sys/devices/virtual/dmi/id/product_name")

    if platform.system() == "Windows":
        try:
            import wmi
            client = wmi.WMI()
            for item in client.Win32_BaseBoard():
                vendor = getattr(item, "Manufacturer", "") or vendor
                name = getattr(item, "Product", "") or name
        except Exception:
            pass

    board = f"{vendor} {name}".strip() or product or "Standard PC Motherboard"

    return {
        "name": "Motherboard",
        "model": board,
        "status": "Supported",
        "color": "good",
        "notes": "Standard UEFI motherboard fully compatible with OpenCore",
        "score": 15
    }

def getaudio(pciids):
    foundcodec = None
    codecid = None

    for filepath in glob.glob("/proc/asound/card*/codec#*"):
        text = readfile(filepath)
        for line in text.splitlines():
            if line.startswith("Codec:") and not foundcodec:
                foundcodec = line.split(":", 1)[1].strip()
            if line.lower().startswith("vendor id:"):
                match = re.search(r"0x([0-9a-fA-F]{4})([0-9a-fA-F]{4})", line)
                if match:
                    codecid = f"{match.group(1).upper()}-{match.group(2).upper()}"

    if codecid and codecid in codec_layouts.data:
        layouts = codec_layouts.data[codecid]
        return {
            "name": "Audio Codec",
            "model": foundcodec or codecid,
            "status": "Supported",
            "color": "good",
            "notes": f"Supported natively by AppleALC ({len(layouts)} layout presets available)",
            "score": 10
        }

    for vid, did, line in pciids:
        if "audio" in line.lower():
            return {
                "name": "Audio",
                "model": line.split(":", 2)[-1].strip() if ":" in line else line,
                "status": "Supported",
                "color": "good",
                "notes": "Intel / High Definition Audio supported via AppleALC or VoodooHDA",
                "score": 9
            }

    return {
        "name": "Audio",
        "model": foundcodec or "High Definition Audio",
        "status": "Supported",
        "color": "good",
        "notes": "Audio device supported via AppleALC or generic audio driver",
        "score": 8
    }

def getnet(pciids):
    items = []
    ethfound = None
    wififound = None
    ethscore = 0
    wifiscore = 0

    for vid, did, line in pciids:
        fullid = f"{vid}-{did}"
        lower = line.lower()

        if "ethernet" in lower:
            ethname = line.split(":", 2)[-1].strip() if ":" in line else line
            if fullid in pci_data.EthernetIDs or "8168" in did or "8111" in did or "8125" in did:
                ethscore = 10
                items.append({
                    "name": "Ethernet",
                    "model": ethname,
                    "status": "Supported",
                    "color": "good",
                    "notes": "Supported with RealtekRTL8111 or IntelMausi kext",
                    "score": 10
                })
            else:
                ethscore = 7
                items.append({
                    "name": "Ethernet",
                    "model": ethname,
                    "status": "Supported",
                    "color": "good",
                    "notes": "Standard PCI ethernet controller",
                    "score": 7
                })
            ethfound = True

        if "network controller" in lower or "wireless" in lower or "wi-fi" in lower:
            wifiname = line.split(":", 2)[-1].strip() if ":" in line else line
            if fullid in pci_data.WirelessCardIDs or fullid in pci_data.IntelWiFiIDs:
                wifiscore = 10
                items.append({
                    "name": "Wi-Fi",
                    "model": wifiname,
                    "status": "Supported",
                    "color": "good",
                    "notes": "Supported with AirportItlwm or Broadcom kext",
                    "score": 10
                })
            elif "realtek" in lower or "8821" in did or "8822" in did or "8723" in did:
                wifiscore = 3
                items.append({
                    "name": "Wi-Fi",
                    "model": wifiname,
                    "status": "Replacement / Dongle Needed",
                    "color": "warn",
                    "notes": "Realtek PCIe Wi-Fi is unsupported natively in macOS; use a USB Wi-Fi dongle or swap M.2 card",
                    "score": 3
                })
            else:
                wifiscore = 5
                items.append({
                    "name": "Wi-Fi",
                    "model": wifiname,
                    "status": "Check Compatibility",
                    "color": "warn",
                    "notes": "Wireless card may require third-party kext or USB adapter",
                    "score": 5
                })
            wififound = True

    usb = runcmd(["lsusb"])
    btfound = None
    for line in usb.splitlines():
        if "bluetooth" in line.lower():
            btname = line.split("ID ", 1)[-1].strip() if "ID " in line else line
            if "intel" in line.lower():
                items.append({
                    "name": "Bluetooth",
                    "model": btname,
                    "status": "Supported",
                    "color": "good",
                    "notes": "Supported via IntelBluetoothFirmware kext",
                    "score": 5
                })
            else:
                items.append({
                    "name": "Bluetooth",
                    "model": btname,
                    "status": "Limited",
                    "color": "warn",
                    "notes": "Bluetooth chip may require third-party firmware injection",
                    "score": 3
                })
            btfound = True
            break

    if not ethfound:
        ethscore = 5

    if not wififound:
        wifiscore = 3

    return items, ethscore, wifiscore

def analyze():
    pciids = []

    if platform.system() == "Windows":
        try:
            import wmi
            client = wmi.WMI()
            for item in client.Win32_VideoController():
                pnp = getattr(item, "PNPDeviceID", "") or ""
                name = getattr(item, "Name", "") or ""
                match = re.search(r"VEN_([0-9A-Fa-f]{4})&DEV_([0-9A-Fa-f]{4})", pnp)
                if match:
                    pciids.append((match.group(1).upper(), match.group(2).upper(), f"Video: {name}"))
            for item in client.Win32_NetworkAdapter():
                pnp = getattr(item, "PNPDeviceID", "") or ""
                name = getattr(item, "Name", "") or ""
                match = re.search(r"VEN_([0-9A-Fa-f]{4})&DEV_([0-9A-Fa-f]{4})", pnp)
                if match:
                    pciids.append((match.group(1).upper(), match.group(2).upper(), f"Network: {name}"))
            for item in client.Win32_SoundDevice():
                pnp = getattr(item, "PNPDeviceID", "") or ""
                name = getattr(item, "Name", "") or ""
                match = re.search(r"VEN_([0-9A-Fa-f]{4})&DEV_([0-9A-Fa-f]{4})", pnp)
                if match:
                    pciids.append((match.group(1).upper(), match.group(2).upper(), f"Audio: {name}"))
        except Exception:
            pass
    else:
        pci = runcmd(["lspci", "-nn"])
        for line in pci.splitlines():
            match = re.search(r"\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]", line)
            if match:
                vid = match.group(1).upper()
                did = match.group(2).upper()
                pciids.append((vid, did, line))

    cpuitem = getcpu()
    gpuitems, gpuscore, gpumacos = getgpu(pciids)
    boarditem = getmotherboard()
    audioitem = getaudio(pciids)
    netitems, ethscore, wifiscore = getnet(pciids)

    allitems = [cpuitem]
    allitems.extend(gpuitems)
    allitems.append(boarditem)
    allitems.append(audioitem)
    allitems.extend(netitems)

    totalscore = cpuitem["score"] + gpuscore + boarditem["score"] + audioitem["score"] + ethscore + wifiscore
    if totalscore > 100:
        totalscore = 100

    targetmacos = "macOS Ventura 13"
    smoothnotes = "Runs smoothly and natively with full hardware acceleration"

    if gpumacos == "24.99.99" and cpuitem["maxos"] == "24.99.99":
        targetmacos = "macOS Sonoma 14 / Sequoia 15"
        smoothnotes = "Latest macOS supported natively"
    elif gpumacos.startswith("22") or gpumacos.startswith("23"):
        targetmacos = "macOS Ventura 13"
        smoothnotes = "Recommended for smooth native graphics acceleration and modern apps"
    elif gpumacos.startswith("21"):
        targetmacos = "macOS Monterey 12"
        smoothnotes = "Recommended for stable and fast daily performance"
    elif gpumacos.startswith("20"):
        targetmacos = "macOS Big Sur 11"
        smoothnotes = "Recommended for optimal legacy graphics support"
    else:
        targetmacos = "macOS High Sierra 10.13"
        smoothnotes = "Compatible with legacy graphics web drivers"

    summarystatus = "Great Hackintosh Candidate"
    if totalscore >= 85:
        summarystatus = "Excellent Hackintosh Support"
    elif totalscore >= 70:
        summarystatus = "Good Hackintosh Support"
    elif totalscore >= 50:
        summarystatus = "Partial Support (Hardware Upgrades Recommended)"
    else:
        summarystatus = "Low Compatibility"

    return {
        "score": totalscore,
        "macos": targetmacos,
        "smooth": smoothnotes,
        "summary": summarystatus,
        "items": allitems
    }

if __name__ == "__main__":
    print(json.dumps(analyze()))
