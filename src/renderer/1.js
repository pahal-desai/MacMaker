async function loadspecs() {
    const box = document.getElementById("specs");

    try {
        const fn = window.api.gethardwarespecs || window.api.getHardwareSpecs;
        if (typeof fn !== "function") {
            throw new Error("Electron hardware API not available.");
        }

        const specs = await fn();
        box.innerHTML = `
            <p><strong>CPU:</strong> ${specs.cpu || "Unknown"}</p>
            <p><strong>GPU:</strong> ${specs.gpu || "Unknown"}</p>
            <p><strong>Motherboard:</strong> ${specs.motherboard || "Unknown"}</p>
            <p><strong>Wi-Fi:</strong> ${specs.wifi || "Unknown"}</p>
            <p><strong>Bluetooth:</strong> ${specs.bluetooth || "Unknown"}</p>
            <p><strong>Ethernet:</strong> ${specs.ethernet || "Unknown"}</p>
            <p><strong>Audio Codec:</strong> ${specs.audio || "Unknown"}</p>
            <p><strong>RAM:</strong> ${specs.ram || (specs.ram_gb ? specs.ram_gb + " GB" : "Unknown")}</p>
            <p><strong>Architecture:</strong> ${specs.arch || specs.architecture || "Unknown"}</p>
            ${specs.distro ? `<p><strong>Distribution:</strong> ${specs.distro}</p>` : ""}
            <p><strong>OS:</strong> ${specs.os || "Unknown"}</p>
            ${specs.hardware ? `<p><strong>Hardware:</strong> ${specs.hardware}</p>` : ""}
        `;
    } catch (err) {
        box.textContent = "Error: " + err.message;
    }
}

document.addEventListener("DOMContentLoaded", loadspecs);
