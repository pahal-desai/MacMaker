let ports = [];
let known = {};
let lastkext = "";

async function autokext() {
    if (!window.api || typeof window.api.makekext !== "function") return;
    const picked = ports.filter(p => p.selected);
    if (picked.length === 0) return;
    const key = JSON.stringify(picked.map(p => ({ id: p.id, type: p.type, selected: p.selected })));
    if (key === lastkext) return;
    lastkext = key;
    try {
        await window.api.makekext(ports);
    } catch (err) {
        console.error(err);
    }
}

async function scan() {
    try {
        if (!window.api || typeof window.api.getusb !== "function") {
            return;
        }

        const data = await window.api.getusb();
        const incoming = data.ports || [];

        for (const port of incoming) {
            const old = ports.find(p => p.id === port.id);
            if (port.device) {
                known[port.id] = true;
                port.selected = true;
            } else if (known[port.id]) {
                port.selected = old ? old.selected : true;
                if (old && old.type !== undefined) {
                    port.type = old.type;
                }
            } else if (port.internal) {
                known[port.id] = true;
                port.selected = true;
            }
        }

        ports = incoming;
        render();
        autokext();
    } catch (err) {
        console.error(err);
    }
}

function changetype(id, val) {
    const num = parseInt(val, 10);
    for (const port of ports) {
        if (port.id === id) {
            port.type = num;
            if (port.companion) {
                const comp = ports.find(p => p.id === port.companion);
                if (comp) {
                    comp.type = num;
                }
            }
            break;
        }
    }
    render();
    autokext();
}

function render() {
    const box = document.getElementById("portsbox");
    if (!box) return;

    const found = ports.filter(p => p.selected || p.device || known[p.id] || p.internal);

    if (found.length === 0) {
        box.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 2.5rem 1rem; color: var(--subtext);">
                <p style="font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--text);">No USB devices detected yet</p>
                <p style="margin: 0; font-size: 0.95rem;">Plug your USB drive or mouse into any USB port to detect it.</p>
            </div>
        `;
        return;
    }

    let html = "";
    for (const port of found) {
        const devtext = port.device ? port.device : "Detected (currently unplugged)";
        const devcls = port.device ? "portdev" : "portdev empty";
        const compinfo = port.companion ? `<span style="font-size: 0.75rem; color: var(--subtext);">Companion: ${port.companion}</span>` : "";

        html += `
            <div class="portcard">
                <div class="porttop">
                    <div class="portlabel">
                        <span class="portid">${port.id}</span>
                    </div>
                    ${compinfo}
                </div>
                <div class="${devcls}">${devtext}</div>
                <div class="portctrl">
                    <select class="typeopt" onchange="changetype('${port.id}', this.value)">
                        <option value="3" ${port.type === 3 ? "selected" : ""}>USB 3 Type A (3)</option>
                        <option value="0" ${port.type === 0 ? "selected" : ""}>USB 2 Type A (0)</option>
                        <option value="9" ${port.type === 9 ? "selected" : ""}>Type C with switch (9)</option>
                        <option value="10" ${port.type === 10 ? "selected" : ""}>Type C dual (10)</option>
                        <option value="255" ${port.type === 255 ? "selected" : ""}>Internal / Bluetooth (255)</option>
                    </select>
                </div>
            </div>
        `;
    }

    box.innerHTML = html;
}

function init() {
    const back = document.getElementById("backbtn");
    const next = document.getElementById("nextbtn");
    const scanb = document.getElementById("scanbtn");

    if (back) {
        back.addEventListener("click", () => {
            window.location.href = "analysis.html";
        });
    }

    if (next) {
        next.addEventListener("click", async () => {
            await autokext();
            window.location.href = "recosver.html";
        });
    }

    if (scanb) {
        scanb.addEventListener("click", () => {
            scan();
        });
    }

    scan();
    setInterval(scan, 2000);
}

document.addEventListener("DOMContentLoaded", init);