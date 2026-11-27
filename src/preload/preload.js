const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
    gethardwarespecs: () => ipcRenderer.invoke("gethardwarespecs"),
    getHardwareSpecs: () => ipcRenderer.invoke("gethardwarespecs"),
    getanalysis: () => ipcRenderer.invoke("getanalysis"),
    getusb: () => ipcRenderer.invoke("getusb"),
    makekext: (data) => ipcRenderer.invoke("makekext", data),
    makeefi: () => ipcRenderer.invoke("makeefi"),
    onefiprogress: (fn) => ipcRenderer.on("efiprogress", (e, val) => fn(val)),
    openfolder: (target) => ipcRenderer.invoke("openfolder", target),
    installdeps: () => ipcRenderer.invoke("installdeps")
});
