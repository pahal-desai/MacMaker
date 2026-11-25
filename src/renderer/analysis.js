async function load() {
    const box = document.getElementById("results");
    const btn = document.getElementById("nextbtn");

    if (btn) {
        btn.addEventListener("click", () => {
            window.location.href = "usbmap.html";
        });
    }

    try {
        if (!window.api || typeof window.api.getanalysis !== "function") {
            throw new Error("Analysis API not available.");
        }

        const data = await window.api.getanalysis();

        let list = "";
        for (const item of data.items) {
            list += `
                <div class="itemcard">
                    <div class="itemhead">
                        <span class="itemname">${item.name}: ${item.model}</span>
                        <span class="badge ${item.color}">${item.status}</span>
                    </div>
                    <p class="itemnotes">${item.notes}</p>
                </div>
            `;
        }

        box.innerHTML = `
            <div class="scorecard">
                <div class="scoreinfo">
                    <h2>${data.summary}</h2>
                    <p><strong>Recommended:</strong> ${data.macos} (${data.smooth})</p>
                </div>
                <div class="scorenum">${data.score}%</div>
            </div>
            <div>${list}</div>
        `;
    } catch (err) {
        box.textContent = "Error: " + err.message;
    }
}

document.addEventListener("DOMContentLoaded", load);
