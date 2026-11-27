const { app, BrowserWindow, ipcMain, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

function getpython() {
    const venv = path.join(__dirname, "../../.venv/bin/python");
    const venvwin = path.join(__dirname, "../../.venv/Scripts/python.exe");

    if (fs.existsSync(venv)) return venv;
    if (fs.existsSync(venvwin)) return venvwin;
    return process.platform === "win32" ? "python" : "python3";
}

function getscript(name = "hardware.py") {
    if (app.isPackaged) {
        const unpacked = path.join(process.resourcesPath, `app.asar.unpacked/src/backend/${name}`);
        if (fs.existsSync(unpacked)) return unpacked;
    }
    return path.join(__dirname, `../backend/${name}`);
}

function run(py, args) {
    return new Promise((resolve, reject) => {
        const proc = spawn(py, args);
        let out = "";
        let err = "";

        proc.stdout.on("data", (data) => {
            out += data.toString();
        });

        proc.stderr.on("data", (data) => {
            err += data.toString();
        });

        proc.on("close", (code) => {
            if (code === 0) {
                resolve(out);
            } else {
                reject(new Error(err || `Exit code ${code}`));
            }
        });
    });
}

async function fetchspecs() {
    const py = getpython();
    const script = getscript("hardware.py");
    const out = await run(py, [script]);
    try {
        return JSON.parse(out.trim());
    } catch (err) {
        throw new Error(`Failed to parse hardware info: ${err.message}`);
    }
}

async function fetchanalysis() {
    const py = getpython();
    const script = getscript("analysis.py");
    const out = await run(py, [script]);
    try {
        return JSON.parse(out.trim());
    } catch (err) {
        throw new Error(`Failed to parse analysis info: ${err.message}`);
    }
}

async function getusb() {
    const py = getpython();
    const script = getscript("usbmap.py");
    const out = await run(py, [script]);
    try {
        return JSON.parse(out.trim());
    } catch (err) {
        throw new Error(`Failed to parse usb info: ${err.message}`);
    }
}

function getdatadir() {
    if (app.isPackaged) {
        return path.join(app.getPath("documents"), "MacMaker");
    }
    return path.join(__dirname, "../..");
}

function getcachedir() {
    return path.join(app.getPath("userData"), "cache");
}

function getscriptenv() {
    return {
        ...process.env,
        MACMAKERDIR: getdatadir(),
        MACMAKERCACHE: getcachedir()
    };
}

function makekext(data) {
    return new Promise((resolve, reject) => {
        const py = getpython();
        const script = getscript("usbmap.py");
        const proc = spawn(py, [script, "build"], { env: getscriptenv() });
        let out = "";
        let err = "";

        proc.stdout.on("data", (chunk) => {
            out += chunk.toString();
        });

        proc.stderr.on("data", (chunk) => {
            err += chunk.toString();
        });

        proc.on("close", (code) => {
            if (code === 0) {
                try {
                    resolve(JSON.parse(out.trim()));
                } catch (e) {
                    resolve({ status: "success", path: out.trim() });
                }
            } else {
                reject(new Error(err || `Exit code ${code}`));
            }
        });

        proc.stdin.write(JSON.stringify(data));
        proc.stdin.end();
    });
}

function makeefi(win) {
    return new Promise((resolve, reject) => {
        const py = getpython();
        const script = getscript("efi.py");
        const proc = spawn(py, [script], { env: getscriptenv() });
        let buf = "";
        let err = "";
        let res = null;

        proc.stdout.on("data", (chunk) => {
            buf += chunk.toString();
            const lines = buf.split(/\r?\n/);
            buf = lines.pop() || "";
            for (const line of lines) {
                const text = line.trim();
                if (!text.startsWith("{")) continue;
                try {
                    const parsed = JSON.parse(text);
                    if (parsed.type === "progress" && win && !win.isDestroyed()) {
                        win.webContents.send("efiprogress", parsed);
                    } else if (parsed.type === "done") {
                        res = parsed;
                    }
                } catch (e) {
                }
            }
        });

        proc.stderr.on("data", (chunk) => {
            err += chunk.toString();
        });

        proc.on("close", (code) => {
            if (buf.trim().startsWith("{")) {
                try {
                    const parsed = JSON.parse(buf.trim());
                    if (parsed.type === "done") res = parsed;
                } catch (e) {
                }
            }
            if (code === 0 && res) {
                resolve(res);
            } else {
                reject(new Error(err || `EFI generation failed with exit code ${code}`));
            }
        });
    });
}

async function getusbdrives() {
    const py = getpython();
    const script = getscript("recovery.py");
    return new Promise((resolve, reject) => {
        const proc = spawn(py, [script, "list"], { env: getscriptenv() });
        let out = "";
        let err = "";
        proc.stdout.on("data", (d) => { out += d.toString(); });
        proc.stderr.on("data", (d) => { err += d.toString(); });
        proc.on("close", (code) => {
            if (code === 0) {
                try {
                    resolve(JSON.parse(out.trim()));
                } catch (e) {
                    reject(new Error(`Failed to parse USB drives: ${e.message}`));
                }
            } else {
                reject(new Error(err || `Exit code ${code}`));
            }
        });
    });
}

function makeusb(win, drive, ver) {
    return new Promise((resolve, reject) => {
        const py = getpython();
        const script = getscript("recovery.py");
        const proc = spawn(py, [script, "make", drive, ver], { env: getscriptenv() });
        let buf = "";
        let err = "";
        let res = null;

        proc.stdout.on("data", (chunk) => {
            buf += chunk.toString();
            const lines = buf.split(/\r?\n/);
            buf = lines.pop() || "";
            for (const line of lines) {
                const text = line.trim();
                if (!text.startsWith("{")) continue;
                try {
                    const parsed = JSON.parse(text);
                    if (parsed.type === "progress" && win && !win.isDestroyed()) {
                        win.webContents.send("usbprogress", parsed);
                    } else if (parsed.type === "done") {
                        res = parsed;
                    }
                } catch (e) {
                }
            }
        });

        proc.stderr.on("data", (chunk) => {
            err += chunk.toString();
        });

        proc.on("close", (code) => {
            if (buf.trim().startsWith("{")) {
                try {
                    const parsed = JSON.parse(buf.trim());
                    if (parsed.type === "done") res = parsed;
                } catch (e) {
                }
            }
            if (code === 0 && res) {
                resolve(res);
            } else {
                reject(new Error(err || `Bootable USB failed with exit code ${code}`));
            }
        });
    });
}

async function installdeps() {
    const py = getpython();
    const pkgs = ["psutil", "py-cpuinfo"];
    if (process.platform === "win32") {
        pkgs.push("wmi");
    }

    const check = process.platform === "win32"
        ? "import psutil, cpuinfo, wmi"
        : "import psutil, cpuinfo";

    try {
        await run(py, ["-c", check]);
        return "Dependencies already installed.";
    } catch (e) {
    }

    const tries = [
        ["-m", "pip", "install", "--user", "--break-system-packages", ...pkgs],
        ["-m", "pip", "install", "--user", ...pkgs],
        ["-m", "pip", "install", ...pkgs]
    ];

    let last = "";
    for (const item of tries) {
        try {
            await run(py, item);
            return "Dependencies installed successfully.";
        } catch (err) {
            last = err.message;
        }
    }

    throw new Error(last);
}

function createwin() {
    const win = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 900,
        minHeight: 600,
        title: "MacMaker",
        webPreferences: {
            preload: path.join(__dirname, "../preload/preload.js"),
            contextIsolation: true,
            nodeIntegration: false
        }
    });

    win.loadFile(path.join(__dirname, "../renderer/index.html"));
}

ipcMain.handle("installdeps", async () => {
    return await installdeps();
});

ipcMain.handle("gethardwarespecs", async () => {
    return await fetchspecs();
});

ipcMain.handle("getanalysis", async () => {
    return await fetchanalysis();
});

ipcMain.handle("getusb", async () => {
    return await getusb();
});

ipcMain.handle("makekext", async (event, data) => {
    return await makekext(data);
});

ipcMain.handle("makeefi", async (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    return await makeefi(win);
});

ipcMain.handle("getusbdrives", async () => {
    return await getusbdrives();
});

ipcMain.handle("makeusb", async (event, drive, ver) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    return await makeusb(win, drive, ver);
});

ipcMain.handle("openfolder", async (event, target) => {
    if (target) {
        await shell.openPath(target);
    }
});

ipcMain.handle("get-hardware-specs", async () => {
    return await fetchspecs();
});

app.whenReady().then(createwin);

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createwin();
});
