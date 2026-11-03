const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
    getHardwareSpecs: () => ipcRenderer.invoke("get-hardware-specs"),
    installdeps: () => ipcRenderer.invoke("installdeps")
});
