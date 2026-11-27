let lastres = null;

async function loaddrives() {
    const drivepick = document.getElementById("drivepick");
    const verpick = document.getElementById("verpick");
    const createbtn = document.getElementById("createbtn");
    if (!drivepick) return;

    try {
        if (!window.api || typeof window.api.getusbdrives !== "function") {
            drivepick.innerHTML = `<option value="">USB drive API not available</option>`;
            return;
        }

        const data = await window.api.getusbdrives();
        const drives = data.drives || [];

        if (verpick && data.recommended) {
            const match = Array.from(verpick.options).find(o => o.value === data.recommended);
            if (match) {
                verpick.value = data.recommended;
            }
        }

        if (drives.length === 0) {
            drivepick.innerHTML = `<option value="">No USB flash drives found - plug one in and click Refresh</option>`;
            if (createbtn) createbtn.disabled = true;
            return;
        }

        let html = "";
        for (const item of drives) {
            html += `<option value="${item.id}">${item.name} (${item.size})</option>`;
        }
        drivepick.innerHTML = html;
        if (createbtn) createbtn.disabled = false;
    } catch (err) {
        drivepick.innerHTML = `<option value="">Error scanning drives: ${err.message}</option>`;
        if (createbtn) createbtn.disabled = true;
    }
}

async function startusb() {
    const drivepick = document.getElementById("drivepick");
    const verpick = document.getElementById("verpick");
    const createbtn = document.getElementById("createbtn");
    const refreshbtn = document.getElementById("refreshbtn");
    const statusbox = document.getElementById("usbstatus");
    const resbox = document.getElementById("usbresult");
    const msg = document.getElementById("usbmsg");
    const fill = document.getElementById("usbfill");
    const next = document.getElementById("nextbtn");

    const drive = drivepick ? drivepick.value : "";
    const ver = verpick ? verpick.value : "13";
    if (!drive) return;

    if (createbtn) createbtn.disabled = true;
    if (refreshbtn) refreshbtn.disabled = true;
    if (drivepick) drivepick.disabled = true;
    if (verpick) verpick.disabled = true;
    if (next) next.disabled = true;
    if (resbox) resbox.innerHTML = "";
    if (statusbox) statusbox.style.display = "block";
    if (msg) msg.textContent = "Starting bootable USB setup...";
    if (fill) fill.style.width = "5%";

    try {
        const res = await window.api.makeusb(drive, ver);
        lastres = res;
        if (fill) fill.style.width = "100%";
        if (statusbox) statusbox.style.display = "none";
        if (resbox) {
            resbox.innerHTML = `
                <div class="scorecard">
                    <div class="scoreinfo">
                        <h2>Bootable USB Ready!</h2>
                        <p><strong>Drive:</strong> ${res.drive} &bull; <strong>macOS:</strong> ${res.macos}</p>
                    </div>
                    <span class="badge good">Done</span>
                </div>
            `;
        }
        if (next) next.disabled = false;
    } catch (err) {
        if (statusbox) statusbox.style.display = "none";
        if (resbox) {
            resbox.innerHTML = `<div class="itemcard"><div class="itemhead"><span class="itemname">Error</span><span class="badge bad">Failed</span></div><p class="itemnotes">${err.message}</p></div>`;
        }
        if (createbtn) createbtn.disabled = false;
        if (refreshbtn) refreshbtn.disabled = false;
        if (drivepick) drivepick.disabled = false;
        if (verpick) verpick.disabled = false;
    }
}

function showdone() {
    const mainbox = document.getElementById("mainbox");
    const next = document.getElementById("nextbtn");
    if (!mainbox || !lastres) return;

    mainbox.innerHTML = `
        <h1>All Set!</h1>
        <div class="scorecard">
            <div class="scoreinfo">
                <h2>Your Bootable macOS USB Is Ready</h2>
                <p><strong>Drive:</strong> ${lastres.drive} &bull; <strong>macOS:</strong> ${lastres.macos}</p>
            </div>
            <span class="badge good">Ready</span>
        </div>
        <div class="itemcard">
            <div class="itemhead">
                <span class="itemname">Next Steps to Install macOS</span>
                <span class="badge info">Guide</span>
            </div>
            <p class="itemnotes">1. Restart your PC and open the BIOS/UEFI Boot Menu (usually F12, F11, F8, or Esc).</p>
            <p class="itemnotes">2. Select your USB drive and boot into OpenCore.</p>
            <p class="itemnotes">3. Choose the macOS Recovery entry, open Disk Utility to format your target drive as APFS, and install macOS.</p>
        </div>
    `;
    if (next) next.style.display = "none";
}

function init() {
    const back = document.getElementById("backbtn");
    const next = document.getElementById("nextbtn");
    const refreshbtn = document.getElementById("refreshbtn");
    const createbtn = document.getElementById("createbtn");
    const msg = document.getElementById("usbmsg");
    const fill = document.getElementById("usbfill");

    if (back) {
        back.addEventListener("click", () => {
            window.location.href = "efi.html";
        });
    }

    if (next) {
        next.disabled = true;
        next.addEventListener("click", () => {
            if (!next.disabled) {
                showdone();
            }
        });
    }

    if (refreshbtn) {
        refreshbtn.addEventListener("click", () => {
            loaddrives();
        });
    }

    if (createbtn) {
        createbtn.addEventListener("click", () => {
            startusb();
        });
    }

    if (window.api && typeof window.api.onusbprogress === "function") {
        window.api.onusbprogress((info) => {
            if (msg && info.msg) {
                msg.textContent = info.msg;
            }
            if (fill && typeof info.pct === "number") {
                fill.style.width = `${info.pct}%`;
            }
        });
    }

    loaddrives();
}

document.addEventListener("DOMContentLoaded", init);
