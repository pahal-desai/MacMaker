const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

function getPythonPath() {
    const venvPython = path.join(__dirname, "../../.venv/bin/python");
    const venvPythonWin = path.join(__dirname, "../../.venv/Scripts/python.exe");

    if (fs.existsSync(venvPython)) return venvPython;
    if (fs.existsSync(venvPythonWin)) return venvPythonWin;
    return process.platform === "win32" ? "python" : "python3";
}

function getScriptPath() {
    if (app.isPackaged) {
        const unpackedPath = path.join(process.resourcesPath, "app.asar.unpacked/src/backend/hardware.py");
        if (fs.existsSync(unpackedPath)) return unpackedPath;
    }
    return path.join(__dirname, "../backend/hardware.py");
}

function fetchHardwareSpecs() {
    return new Promise((resolve, reject) => {
        const pythonExecutable = getPythonPath();
        const scriptPath = getScriptPath();

        const pyProc = spawn(pythonExecutable, [scriptPath]);
        let output = "";
        let errorOutput = "";

        pyProc.stdout.on("data", (data) => {
            output += data.toString();
        });

        pyProc.stderr.on("data", (data) => {
            errorOutput += data.toString();
        });

        pyProc.on("close", (code) => {
            if (code !== 0) {
                return reject(new Error(errorOutput || `Python process exited with code ${code}`));
            }
            try {
                const parsed = JSON.parse(output.trim());
                resolve(parsed);
            } catch (err) {
                reject(new Error(`Failed to parse hardware info: ${err.message}`));
            }
        });
    });
}

function installdeps() {
    return new Promise((resolve, reject) => {
        const py = getPythonPath();
        const args = ["-m", "pip", "install", "psutil", "py-cpuinfo"];
        if (process.platform === "win32") {
            args.push("wmi");
        }
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
                resolve("Dependencies installed successfully.");
            } else {
                reject(new Error(err || `Pip exited with code ${code}`));
            }
        });
    });
}

function createWindow() {
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

ipcMain.handle("get-hardware-specs", async () => {
    return await fetchHardwareSpecs();
});

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
