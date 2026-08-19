// main.js — students will add JavaScript here as features are built

(function () {
    "use strict";

    var modal = document.getElementById("how-it-works-modal");
    var trigger = document.getElementById("how-it-works-trigger");
    if (!modal || !trigger) return;

    var iframe = modal.querySelector("iframe");
    var iframeSrc = iframe ? iframe.getAttribute("src") : "";

    function openModal() {
        // Restore src so the iframe reloads and plays.
        if (iframe && !iframe.getAttribute("src")) {
            iframe.setAttribute("src", iframeSrc);
        }
        modal.hidden = false;
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        // Stop playback by clearing the iframe src; openModal restores it.
        if (iframe) iframe.setAttribute("src", "");
        modal.hidden = true;
        document.body.style.overflow = "";
    }

    trigger.addEventListener("click", function (e) {
        e.preventDefault();
        openModal();
    });

    modal.addEventListener("click", function (e) {
        // Close when clicking the overlay itself, not its children.
        if (e.target === modal) closeModal();
    });

    var closeBtn = modal.querySelector(".modal-close");
    if (closeBtn) closeBtn.addEventListener("click", closeModal);

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !modal.hidden) closeModal();
    });
})();
