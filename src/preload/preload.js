const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
    gethardwarespecs: () => ipcRenderer.invoke("gethardwarespecs"),
    getHardwareSpecs: () => ipcRenderer.invoke("gethardwarespecs"),
    installdeps: () => ipcRenderer.invoke("installdeps")
});
