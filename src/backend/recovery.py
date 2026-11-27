import os
import sys
import json
import time
import shutil
import struct
import string
import random
import hashlib
import tempfile
import platform
import subprocess
from urllib.request import Request, urlopen
from urllib.parse import urlparse

def emit(step, pct, msg):
    print(json.dumps({"type": "progress", "step": step, "pct": pct, "msg": msg}), flush=True)

def runcmd(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return proc.stdout
    except Exception:
        return ""

def fmtsize(sizebytes):
    gb = sizebytes / (1024 ** 3)
    if gb >= 1:
        return f"{gb:.1f} GB"
    mb = sizebytes / (1024 ** 2)
    return f"{mb:.0f} MB"

def getlinuxdrives():
    drives = []
    raw = runcmd(["lsblk", "-J", "-b", "-o", "NAME,SIZE,MODEL,TRAN,RM,TYPE,HOTPLUG"])
    if not raw.strip():
        return drives
    try:
        data = json.loads(raw)
        for dev in data.get("blockdevices", []):
            dtype = (dev.get("type") or "").lower()
            tran = (dev.get("tran") or "").lower()
            rm = bool(dev.get("rm"))
            hotplug = bool(dev.get("hotplug"))
            size = int(dev.get("size") or 0)
            name = dev.get("name") or ""
            if dtype == "disk" and size > 0 and name and (tran == "usb" or rm or hotplug):
                model = (dev.get("model") or "USB Drive").strip()
                drives.append({
                    "id": f"/dev/{name}",
                    "name": model,
                    "size": fmtsize(size),
                    "bytes": size
                })
    except Exception:
        pass
    return drives

def getwindrives():
    drives = []
    ps = "Get-Disk | Where-Object { $_.BusType -eq 'USB' -and $_.Size -gt 0 } | Select-Object Number, FriendlyName, Size | ConvertTo-Json"
    raw = runcmd(["powershell", "-NoProfile", "-Command", ps])
    if raw.strip():
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                num = item.get("Number")
                size = int(item.get("Size") or 0)
                name = (item.get("FriendlyName") or "USB Drive").strip()
                if num is not None and size > 0:
                    drives.append({
                        "id": str(num),
                        "name": name,
                        "size": fmtsize(size),
                        "bytes": size
                    })
            return drives
        except Exception:
            pass
    try:
        import wmi
        client = wmi.WMI()
        for disk in client.Win32_DiskDrive():
            iface = (getattr(disk, "InterfaceType", "") or "").upper()
            size = int(getattr(disk, "Size", 0) or 0)
            idx = getattr(disk, "Index", None)
            if iface == "USB" and idx is not None and size > 0:
                drives.append({
                    "id": str(idx),
                    "name": (getattr(disk, "Model", "") or "USB Drive").strip(),
                    "size": fmtsize(size),
                    "bytes": size
                })
    except Exception:
        pass
    return drives

def listdrives():
    if platform.system() == "Windows":
        return getwindrives()
    return getlinuxdrives()

def gettargetver(cachedir):
    mapping = {
        "17": "10.13",
        "19": "10.15",
        "20": "11",
        "21": "12",
        "22": "13",
        "23": "14",
        "24": "15",
        "25": "26",
        "26": "26"
    }
    metafile = os.path.join(cachedir, "lastefi.json")
    if os.path.exists(metafile):
        try:
            with open(metafile, "r") as f:
                data = json.load(f)
            darwin = str(data.get("darwin", ""))
            if darwin in mapping:
                return mapping[darwin]
        except Exception:
            pass
    return "13"

def getboards():
    return {
        "10.13": ("Mac-7BA5B2794B2CDB12", "00000000000000000", "latest", "macOS High Sierra 10.13"),
        "10.15": ("Mac-00BE6ED71E35EB86", "00000000000000000", "latest", "macOS Catalina 10.15"),
        "11": ("Mac-42FD25EABCABB274", "00000000000000000", "latest", "macOS Big Sur 11"),
        "12": ("Mac-E43C1C25D4880AD6", "00000000000000000", "latest", "macOS Monterey 12"),
        "13": ("Mac-B4831CEBD52A0C4C", "00000000000000000", "latest", "macOS Ventura 13"),
        "14": ("Mac-827FAC58A8FDFA22", "00000000000000000", "latest", "macOS Sonoma 14"),
        "15": ("Mac-7BA5B2D9E42DDD94", "00000000000000000", "latest", "macOS Sequoia 15"),
        "26": ("Mac-E1008331FDC96864", "00000000000000000", "latest", "macOS Tahoe 26")
    }

def genhex(length):
    return "".join(random.choices(string.hexdigits[:16].upper(), k=length))

def getsession():
    hdrs = {
        "Host": "osrecovery.apple.com",
        "Connection": "close",
        "User-Agent": "InternetRecovery/1.0"
    }
    resp = urlopen(Request("http://osrecovery.apple.com/", headers=hdrs), timeout=15)
    info = dict(resp.info())
    for k, v in info.items():
        if k.lower() == "set-cookie":
            for part in v.split("; "):
                if part.startswith("session="):
                    return part
    raise RuntimeError("Failed to get Apple recovery session.")

def getrecoveryinfo(sess, bid, mlb, ostype):
    hdrs = {
        "Host": "osrecovery.apple.com",
        "Connection": "close",
        "User-Agent": "InternetRecovery/1.0",
        "Cookie": sess,
        "Content-Type": "text/plain"
    }
    post = {
        "cid": genhex(16),
        "sn": mlb,
        "bid": bid,
        "k": genhex(64),
        "fg": genhex(64),
        "os": ostype
    }
    body = "\n".join(f"{k}={v}" for k, v in post.items()).encode()
    resp = urlopen(Request("http://osrecovery.apple.com/InstallationPayload/RecoveryImage", headers=hdrs, data=body), timeout=15)
    out = resp.read().decode("utf-8")
    info = {}
    for line in out.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            info[k] = v.strip()
    for reqkey in ("AP", "AU", "AH", "AT", "CU", "CH", "CT"):
        if reqkey not in info:
            raise RuntimeError(f"Missing recovery info key: {reqkey}")
    return info

def downloadfile(url, sess, dstpath, label):
    purl = urlparse(url)
    hdrs = {
        "Host": purl.hostname,
        "Connection": "close",
        "User-Agent": "InternetRecovery/1.0",
        "Cookie": f"AssetToken={sess}"
    }
    resp = urlopen(Request(url, headers=hdrs), timeout=30)
    total = int(resp.headers.get("Content-Length") or -1)
    done = 0
    lastpct = -1
    os.makedirs(os.path.dirname(dstpath), exist_ok=True)
    with open(dstpath, "wb") as fh:
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            if total > 0:
                pct = int((done / total) * 100)
                if pct != lastpct:
                    lastpct = pct
                    uipct = 10 + int(pct * 0.55)
                    donemb = done / (1024 ** 2)
                    totalmb = total / (1024 ** 2)
                    emit(1, uipct, f"Downloading {label}: {donemb:.1f} / {totalmb:.1f} MB ({pct}%)")

def verifydmg(dmgpath, cnkpath):
    hdrfmt = struct.Struct("<4sIBBBxQQQ")
    chkfmt = struct.Struct("<I32s")
    with open(cnkpath, "rb") as cf, open(dmgpath, "rb") as df:
        hdr = cf.read(hdrfmt.size)
        magic, hsize, fver, cmeth, smeth, ccount, coff, soff = hdrfmt.unpack(hdr)
        if magic != b"CNKL" or hsize != hdrfmt.size or ccount <= 0:
            raise RuntimeError("Invalid recovery chunklist header.")
        for _ in range(ccount):
            csize, chash = chkfmt.unpack(cf.read(chkfmt.size))
            buf = df.read(csize)
            if len(buf) != csize or hashlib.sha256(buf).digest() != chash:
                raise RuntimeError("Recovery download verification failed.")
        if df.read(1) != b"":
            raise RuntimeError("Recovery image size mismatch.")

def downloadrecovery(verkey, cachedir):
    boards = getboards()
    if verkey not in boards:
        verkey = "13"
    bid, mlb, ostype, label = boards[verkey]
    recdir = os.path.join(cachedir, "recovery", verkey, "com.apple.recovery.boot")
    dmgpath = os.path.join(recdir, "BaseSystem.dmg")
    cnkpath = os.path.join(recdir, "BaseSystem.chunklist")

    if os.path.exists(dmgpath) and os.path.exists(cnkpath):
        try:
            emit(1, 55, f"Verifying cached {label} recovery image...")
            verifydmg(dmgpath, cnkpath)
            return recdir, label
        except Exception:
            shutil.rmtree(recdir, ignore_errors=True)

    emit(1, 5, f"Connecting to Apple servers for {label}...")
    sess = getsession()
    info = getrecoveryinfo(sess, bid, mlb, ostype)

    os.makedirs(recdir, exist_ok=True)
    tmprecdmg = dmgpath + ".part"
    tmpreccnk = cnkpath + ".part"

    emit(1, 8, f"Downloading {label} chunklist...")
    downloadfile(info["CU"], info["CT"], tmpreccnk, "BaseSystem.chunklist")

    emit(1, 10, f"Downloading {label} recovery image...")
    downloadfile(info["AU"], info["AT"], tmprecdmg, "BaseSystem.dmg")

    emit(2, 68, "Verifying downloaded recovery image...")
    verifydmg(tmprecdmg, tmpreccnk)

    os.replace(tmpreccnk, cnkpath)
    os.replace(tmprecdmg, dmgpath)
    return recdir, label

def formatlinux(driveid, efidir, recdir):
    script = """#!/bin/sh
set -e
DEV="$1"
EFI="$2"
REC="$3"
for p in "${DEV}"*; do
    umount "$p" 2>/dev/null || true
done
wipefs -a "$DEV" >/dev/null 2>&1 || true
if command -v parted >/dev/null 2>&1; then
    parted -s "$DEV" mklabel gpt mkpart primary fat32 1MiB 100% set 1 esp on
else
    printf "label: gpt\\n, , U\\n" | sfdisk --wipe always "$DEV"
fi
if command -v partprobe >/dev/null 2>&1; then
    partprobe "$DEV" >/dev/null 2>&1 || true
fi
sleep 2
case "$DEV" in
    *[0-9]) PART="${DEV}p1" ;;
    *) PART="${DEV}1" ;;
esac
mkfs.vfat -F 32 -n MACMAKER "$PART" >/dev/null
MNT=$(mktemp -d /tmp/macmaker_mnt_XXXXXX)
cleanup() {
    umount "$MNT" 2>/dev/null || true
    rmdir "$MNT" 2>/dev/null || true
}
trap cleanup EXIT
mount "$PART" "$MNT"
cp -r "$EFI" "$MNT/EFI"
cp -r "$REC" "$MNT/com.apple.recovery.boot"
sync
"""
    fd, shfile = tempfile.mkstemp(prefix="macmaker_usb_", suffix=".sh")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(script)
        os.chmod(shfile, 0o755)
        cmd = ["sh", shfile, driveid, efidir, recdir]
        if os.geteuid() != 0:
            cmd = ["pkexec"] + cmd
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"Format failed (code {proc.returncode})")
    finally:
        if os.path.exists(shfile):
            os.remove(shfile)

def formatwin(driveid, efidir, recdir):
    fd, psfile = tempfile.mkstemp(prefix="macmaker_usb_", suffix=".ps1")
    rfd, resfile = tempfile.mkstemp(prefix="macmaker_res_", suffix=".txt")
    os.close(rfd)
    num = int(driveid)
    efisafe = efidir.replace("'", "''")
    recsafe = recdir.replace("'", "''")
    ressafe = resfile.replace("'", "''")
    psscript = f"""
$ErrorActionPreference = 'Stop'
try {{
    $disk = Get-Disk -Number {num}
    if ($disk.BusType -ne 'USB') {{
        throw 'Selected disk is not a USB drive.'
    }}
    Clear-Disk -Number {num} -RemoveData -Confirm:$false
    Initialize-Disk -Number {num} -PartitionStyle GPT
    $maxfat = [int64](31 * 1024 * 1024 * 1024)
    if ($disk.Size -gt $maxfat) {{
        $part = New-Partition -DiskNumber {num} -Size 31GB -AssignDriveLetter
    }} else {{
        $part = New-Partition -DiskNumber {num} -UseMaximumSize -AssignDriveLetter
    }}
    Start-Sleep -Seconds 2
    Format-Volume -Partition $part -FileSystem FAT32 -NewFileSystemLabel 'MACMAKER' -Confirm:$false | Out-Null
    $letter = $part.DriveLetter
    if (-not $letter) {{
        $letter = ($part | Get-Partition).DriveLetter
    }}
    if (-not $letter) {{
        throw 'Failed to assign drive letter.'
    }}
    $dst = "{{0}}:\\" -f $letter
    Copy-Item -Path '{efisafe}' -Destination (Join-Path $dst 'EFI') -Recurse -Force
    Copy-Item -Path '{recsafe}' -Destination (Join-Path $dst 'com.apple.recovery.boot') -Recurse -Force
    Set-Content -Path '{ressafe}' -Value 'OK'
}} catch {{
    Set-Content -Path '{ressafe}' -Value $_.Exception.Message
    exit 1
}}
"""
    try:
        with os.fdopen(fd, "w") as f:
            f.write(psscript)
        import ctypes
        isadmin = False
        try:
            isadmin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            pass
        if isadmin:
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", psfile], check=False)
        else:
            elev = f"Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"{psfile}\"' -Verb RunAs -Wait"
            subprocess.run(["powershell", "-NoProfile", "-Command", elev], check=False)
        res = ""
        if os.path.exists(resfile):
            with open(resfile, "r", errors="ignore") as rf:
                res = rf.read().strip()
        if res != "OK":
            raise RuntimeError(res or "USB creation was cancelled or failed.")
    finally:
        for p in (psfile, resfile):
            if os.path.exists(p):
                os.remove(p)

def makeusb(driveid, verkey):
    basedir = os.environ.get("MACMAKERDIR") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
    cachedir = os.environ.get("MACMAKERCACHE") or os.path.join(os.path.expanduser("~"), ".cache", "macmaker")
    efidir = os.path.join(basedir, "EFI")

    if not os.path.isdir(efidir):
        raise RuntimeError("EFI folder not found. Please go back and generate the EFI first.")

    drives = listdrives()
    match = next((d for d in drives if d["id"] == driveid), None)
    if not match:
        raise RuntimeError("Selected USB drive was not found or is not removable.")

    if match["bytes"] < 1500000000:
        raise RuntimeError("USB drive must be at least 2 GB.")

    recdir, label = downloadrecovery(verkey, cachedir)

    emit(3, 75, f"Formatting {match['name']} ({driveid}) and copying EFI + Recovery...")
    if platform.system() == "Windows":
        formatwin(driveid, efidir, recdir)
    else:
        formatlinux(driveid, efidir, recdir)

    emit(4, 100, "Bootable USB drive created successfully!")
    res = {
        "type": "done",
        "status": "success",
        "drive": f"{match['name']} ({driveid})",
        "macos": label,
        "efi": efidir
    }
    print(json.dumps(res), flush=True)

def main():
    cachedir = os.environ.get("MACMAKERCACHE") or os.path.join(os.path.expanduser("~"), ".cache", "macmaker")
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print(json.dumps({
            "drives": listdrives(),
            "recommended": gettargetver(cachedir)
        }))
    elif len(sys.argv) > 3 and sys.argv[1] == "make":
        makeusb(sys.argv[2], sys.argv[3])
    else:
        raise RuntimeError("Invalid recovery command arguments.")

if __name__ == "__main__":
    main()
