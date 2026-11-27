import os
import sys
import json
import glob
import re
import platform
import shutil
import plistlib
import binascii
import subprocess

def runcmd(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return proc.stdout
    except Exception:
        return ""

def hexswap(hexstr):
    pairs = [hexstr[i:i+2] for i in range(0, len(hexstr), 2)]
    return "".join(pairs[::-1]).upper()

def encodeint(num):
    h = hex(num)[2:].zfill(8)
    return binascii.a2b_hex(hexswap(h))

def getlinux():
    ports = []
    pci = "0000:00:14.0"
    hsmax = 14
    ssmax = 6

    for hub in sorted(glob.glob("/sys/bus/usb/devices/usb*")):
        try:
            target = os.readlink(hub)
            match = re.search(r"([0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F])", target)
            if match:
                pci = match.group(1)
        except Exception:
            pass
        try:
            with open(os.path.join(hub, "busnum")) as file:
                bus = int(file.read().strip())
            with open(os.path.join(hub, "maxchild")) as file:
                maxports = int(file.read().strip())
            if bus == 1:
                hsmax = maxports
            elif bus == 2:
                ssmax = maxports
        except Exception:
            pass

    connected = {}
    for dev in sorted(glob.glob("/sys/bus/usb/devices/*")):
        base = os.path.basename(dev)
        if ":" in base or base.startswith("usb"):
            continue
        match = re.match(r"^(\d+)-(\d+)", base)
        if not match:
            continue
        bus = int(match.group(1))
        portnum = int(match.group(2))
        prod = ""
        mfr = ""
        speed = ""
        try:
            with open(os.path.join(dev, "product")) as file:
                prod = file.read().strip()
        except Exception:
            pass
        try:
            with open(os.path.join(dev, "manufacturer")) as file:
                mfr = file.read().strip()
        except Exception:
            pass
        try:
            with open(os.path.join(dev, "speed")) as file:
                speed = file.read().strip()
        except Exception:
            pass
        name = f"{mfr} {prod}".strip() or prod or "USB Device"
        connected[f"{bus}-{portnum}"] = {
            "name": name,
            "speed": speed
        }

    for i in range(1, hsmax + 1):
        key = f"1-{i}"
        item = connected.get(key)
        name = f"HS{str(i).zfill(2)}"
        isinternal = False
        devname = ""
        speedstr = "480 Mbps"

        if item:
            devname = item["name"]
            low = devname.lower()
            if "camera" in low or "bluetooth" in low or "card" in low or "crw" in low:
                isinternal = True

        ports.append({
            "id": name,
            "index": i,
            "bus": 1,
            "protocol": "USB 2.0",
            "type": 255 if isinternal else 3,
            "selected": True if item else False,
            "device": devname,
            "speed": speedstr,
            "companion": f"SS{str(i).zfill(2)}" if i <= ssmax else None,
            "internal": isinternal
        })

    for i in range(1, ssmax + 1):
        key = f"2-{i}"
        item = connected.get(key)
        name = f"SS{str(i).zfill(2)}"
        devname = item["name"] if item else ""
        speedstr = "5 Gbps"

        ports.append({
            "id": name,
            "index": hsmax + i,
            "bus": 2,
            "protocol": "USB 3.0",
            "type": 3,
            "selected": True if item else False,
            "device": devname,
            "speed": speedstr,
            "companion": f"HS{str(i).zfill(2)}",
            "internal": False
        })

    return {
        "controller": "XHC",
        "pci": pci,
        "ports": ports
    }

def getwindows():
    ports = []
    pci = "0000:00:14.0"
    devs = []

    try:
        import wmi
        client = wmi.WMI()
        for item in client.Win32_PnPEntity():
            pnp = getattr(item, "PNPClass", "") or ""
            name = getattr(item, "Name", "") or ""
            devid = getattr(item, "DeviceID", "") or ""
            if pnp.lower() == "usb" or "usb" in devid.lower():
                devs.append(name)
    except Exception:
        out = runcmd(["powershell", "-NoProfile", "-Command", "Get-PnpDevice -Class USB -Status OK | Select-Object -ExpandProperty FriendlyName"])
        for line in out.splitlines():
            line = line.strip()
            if line:
                devs.append(line)

    hsmax = 14
    ssmax = 6

    for i in range(1, hsmax + 1):
        name = f"HS{str(i).zfill(2)}"
        matched = ""
        isinternal = False
        for dev in devs:
            low = dev.lower()
            if "bluetooth" in low and i == 7:
                matched = dev
                isinternal = True
            elif "camera" in low and i == 4:
                matched = dev
                isinternal = True

        ports.append({
            "id": name,
            "index": i,
            "bus": 1,
            "protocol": "USB 2.0",
            "type": 255 if isinternal else 3,
            "selected": True if matched else False,
            "device": matched,
            "speed": "480 Mbps",
            "companion": f"SS{str(i).zfill(2)}" if i <= ssmax else None,
            "internal": isinternal
        })

    for i in range(1, ssmax + 1):
        name = f"SS{str(i).zfill(2)}"
        ports.append({
            "id": name,
            "index": hsmax + i,
            "bus": 2,
            "protocol": "USB 3.0",
            "type": 3,
            "selected": False,
            "device": "",
            "speed": "5 Gbps",
            "companion": f"HS{str(i).zfill(2)}",
            "internal": False
        })

    return {
        "controller": "XHC",
        "pci": pci,
        "ports": ports
    }

def getports():
    if platform.system() == "Windows":
        return getwindows()
    return getlinux()

def buildkext(items):
    if isinstance(items, dict):
        items = items.get("ports", [])
    if not isinstance(items, list):
        items = []

    basedir = os.environ.get("MACMAKERDIR")
    outdir = os.path.join(basedir, "kexts") if basedir else os.path.abspath(os.path.join(os.path.dirname(__file__), "../../kexts"))
    os.makedirs(outdir, exist_ok=True)

    utbmapdir = os.path.join(outdir, "UTBMap.kext")
    contentsdir = os.path.join(utbmapdir, "Contents")
    if os.path.exists(utbmapdir):
        shutil.rmtree(utbmapdir)
    os.makedirs(contentsdir, exist_ok=True)

    portsdict = {}
    maxindex = 0

    for port in items:
        if not isinstance(port, dict):
            continue
        if not port.get("selected"):
            continue
        idx = int(port.get("index", 1))
        if idx > maxindex:
            maxindex = idx
        portid = port.get("id")
        porttype = int(port.get("type", 3))
        comment = port.get("device") or f"{portid} Port"

        portsdict[portid] = {
            "UsbConnector": porttype,
            "port": encodeint(idx),
            "#comment": comment
        }

    if maxindex == 0:
        maxindex = 18

    template = {
        "CFBundleDevelopmentRegion": "English",
        "CFBundleGetInfoString": "v1.1",
        "CFBundleIdentifier": "com.dhinakg.USBToolBox.map",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "UTBMap",
        "CFBundlePackageType": "KEXT",
        "CFBundleShortVersionString": "1.1",
        "CFBundleSignature": "????",
        "CFBundleVersion": "1.1",
        "IOKitPersonalities": {
            "_SB.PCI0.XHC": {
                "CFBundleIdentifier": "com.dhinakg.USBToolBox.kext",
                "IOClass": "USBToolBox",
                "IOMatchCategory": "USBToolBox",
                "IONameMatch": "XHC",
                "IOProviderClass": "IOPCIDevice",
                "IOProviderMergeProperties": {
                    "port-count": encodeint(maxindex),
                    "ports": portsdict
                }
            }
        },
        "OSBundleLibraries": {
            "com.dhinakg.USBToolBox.kext": "1.0.0"
        },
        "OSBundleRequired": "Root"
    }

    plistpath = os.path.join(contentsdir, "Info.plist")
    with open(plistpath, "wb") as file:
        plistlib.dump(template, file, sort_keys=True)

    bundledkext = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../assets/kexts/USBToolBox.kext"))
    if not os.path.exists(bundledkext):
        alt = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../assets/kexts/USBToolBox.kext"))
        if os.path.exists(alt):
            bundledkext = alt
    targetkext = os.path.join(outdir, "USBToolBox.kext")
    if os.path.exists(bundledkext):
        if os.path.exists(targetkext):
            shutil.rmtree(targetkext)
        shutil.copytree(bundledkext, targetkext)

    return {
        "status": "success",
        "path": outdir,
        "kexts": ["UTBMap.kext", "USBToolBox.kext"],
        "count": len(portsdict)
    }

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        data = sys.stdin.read()
        try:
            items = json.loads(data)
        except Exception:
            items = []
        res = buildkext(items)
        print(json.dumps(res))
    else:
        print(json.dumps(getports()))

if __name__ == "__main__":
    main()
