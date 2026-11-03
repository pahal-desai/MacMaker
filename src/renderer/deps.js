async function start() {
    const box = document.getElementById("status");
    const btn = document.getElementById("nextbtn");

    btn.addEventListener("click", () => {
        window.location.href = "1.html";
    });

    try {
        const res = await window.api.installdeps();
        box.textContent = res;
        btn.style.display = "inline-flex";
    } catch (err) {
        box.textContent = "Error: " + err.message;
        btn.style.display = "inline-flex";
    }
}

document.addEventListener("DOMContentLoaded", start);
