const { app, BrowserWindow, ipcMain } = require("electron");
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

function getscript() {
    if (app.isPackaged) {
        const unpacked = path.join(process.resourcesPath, "app.asar.unpacked/src/backend/hardware.py");
        if (fs.existsSync(unpacked)) return unpacked;
    }
    return path.join(__dirname, "../backend/hardware.py");
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
    const script = getscript();
    const out = await run(py, [script]);
    try {
        return JSON.parse(out.trim());
    } catch (err) {
        throw new Error(`Failed to parse hardware info: ${err.message}`);
    }
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
