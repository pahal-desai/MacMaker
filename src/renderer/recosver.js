function init() {
    const back = document.getElementById("backbtn");
    const next = document.getElementById("nextbtn");

    if (back) {
        back.addEventListener("click", () => {
            window.location.href = "efi.html";
        });
    }

    if (next) {
        next.addEventListener("click", () => {
        });
    }
}

document.addEventListener("DOMContentLoaded", init);