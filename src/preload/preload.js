const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
    gethardwarespecs: () => ipcRenderer.invoke("gethardwarespecs"),
    getHardwareSpecs: () => ipcRenderer.invoke("gethardwarespecs"),
    getanalysis: () => ipcRenderer.invoke("getanalysis"),
    installdeps: () => ipcRenderer.invoke("installdeps")
});
