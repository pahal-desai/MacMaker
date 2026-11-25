async function start() {
    const box = document.getElementById("status");
    const btn = document.getElementById("nextbtn");

    if (btn) {
        btn.disabled = true;
        btn.addEventListener("click", () => {
            if (!btn.disabled) {
                window.location.href = "1.html";
            }
        });
    }

    try {
        const res = await window.api.installdeps();
        box.textContent = res;
        if (btn) {
            btn.disabled = false;
        }
    } catch (err) {
        box.textContent = "Error: " + err.message;
        if (btn) {
            btn.disabled = false;
        }
    }
}

document.addEventListener("DOMContentLoaded", start);
