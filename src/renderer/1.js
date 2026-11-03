async function loadSpecs() {
    const container = document.getElementById("specsText");

    try {
        if (!window.api || typeof window.api.getHardwareSpecs !== "function") {
            throw new Error("Electron hardware API not available.");
        }

        const specs = await window.api.getHardwareSpecs();
        container.innerHTML = `
            <p><strong>CPU:</strong> ${specs.cpu || "Unknown"}</p>
            <p><strong>RAM:</strong> ${specs.ram_gb ? specs.ram_gb + " GB" : "Unknown"}</p>
            <p><strong>Architecture:</strong> ${specs.architecture || "Unknown"}</p>
            ${specs.distro ? `<p><strong>Distribution:</strong> ${specs.distro}</p>` : ""}
            <p><strong>OS:</strong> ${specs.os || "Unknown"}</p>
            ${specs.motherboard ? `<p><strong>Motherboard:</strong> ${specs.motherboard}</p>` : ""}
            ${specs.hardware_info ? `<p><strong>Hardware Info:</strong> ${specs.hardware_info}</p>` : ""}
        `;
    } catch (err) {
        container.textContent = "Error: " + err.message;
    }
}

document.addEventListener("DOMContentLoaded", loadSpecs);
