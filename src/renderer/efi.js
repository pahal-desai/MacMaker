function openefi(target) {
    if (window.api && typeof window.api.openfolder === "function") {
        window.api.openfolder(target);
    }
}

async function start() {
    const box = document.getElementById("efibox");
    const msg = document.getElementById("efimsg");
    const fill = document.getElementById("efifill");
    const back = document.getElementById("backbtn");
    const btn = document.getElementById("nextbtn");

    if (back) {
        back.addEventListener("click", () => {
            window.location.href = "usbmap.html";
        });
    }

    if (btn) {
        btn.disabled = true;
        btn.addEventListener("click", () => {
            if (!btn.disabled) {
                window.location.href = "recosver.html";
            }
        });
    }

    if (window.api && typeof window.api.onefiprogress === "function") {
        window.api.onefiprogress((info) => {
            if (msg && info.msg) {
                msg.textContent = info.msg;
            }
            if (fill && typeof info.pct === "number") {
                fill.style.width = `${info.pct}%`;
            }
        });
    }

    try {
        if (!window.api || typeof window.api.makeefi !== "function") {
            throw new Error("EFI generation API not available.");
        }

        const res = await window.api.makeefi();
        const kexts = res.kexts || [];
        let kexthtml = "";
        for (const item of kexts) {
            kexthtml += `<span class="badge info" style="margin: 0.25rem 0.25rem 0 0; display: inline-block;">${item}</span>`;
        }

        box.innerHTML = `
            <div class="scorecard">
                <div class="scoreinfo">
                    <h2>EFI Built Successfully</h2>
                    <p><strong>Target macOS:</strong> ${res.macos || "macOS"} &bull; <strong>SMBIOS:</strong> ${res.smbios || "Unknown"}</p>
                </div>
                <button class="actionbutton" type="button" id="openefibtn">Open EFI Folder</button>
            </div>
            <div class="itemcard">
                <div class="itemhead">
                    <span class="itemname">Hardware &amp; Config</span>
                    <span class="badge good">Ready</span>
                </div>
                <p class="itemnotes"><strong>Board:</strong> ${res.board || "PC"} (${res.chipset || "Standard"})</p>
                <p class="itemnotes"><strong>Saved to:</strong> ${res.path || "EFI"}</p>
            </div>
            <div class="itemcard">
                <div class="itemhead">
                    <span class="itemname">Included Kexts (${kexts.length})</span>
                    <span class="badge good">Loaded</span>
                </div>
                <div style="margin-top: 0.35rem;">${kexthtml}</div>
            </div>
        `;

        const openbtn = document.getElementById("openefibtn");
        if (openbtn) {
            openbtn.addEventListener("click", () => {
                openefi(res.path);
            });
        }

        if (btn) {
            btn.disabled = false;
        }
    } catch (err) {
        box.innerHTML = `<div class="itemcard"><div class="itemhead"><span class="itemname">EFI Error</span><span class="badge bad">Failed</span></div><p class="itemnotes">${err.message}</p></div>`;
    }
}

document.addEventListener("DOMContentLoaded", start);
