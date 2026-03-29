var socket = io()

socket.on("refresh", function () {

    location.reload()

})
// Animation d'apparition des cartes joueurs START
document.addEventListener("DOMContentLoaded", () => {

    const cards = document.querySelectorAll(".fifa-card");

    cards.forEach((card, index) => {

        card.style.opacity = 0;
        card.style.transform = "translateY(30px)";

        setTimeout(() => {

            card.style.transition = "0.6s";

            card.style.opacity = 1;

            card.style.transform = "translateY(0)";

        }, 100 * index);

    });

});
//ANCHOR - Animation d'apparition des cartes joueurs END

// ANCHOR - INDEX classement des joueurs START

document.addEventListener("DOMContentLoaded", () => {

    // ================= FIX PLAYER SPAN =================
    document.querySelectorAll(".player").forEach(cell => {
        if (!cell.querySelector("span")) {
            const text = cell.textContent.trim();
            cell.textContent = "";
            const s = document.createElement("span");
            s.textContent = text;
            cell.appendChild(s);
        }
        const span = cell.querySelector("span");
        span.style.whiteSpace = "nowrap";
        span.style.overflow = "hidden";
        span.style.textOverflow = "ellipsis";
        span.style.display = "block";
        span.style.width = "100%";
    });

    // ================= SCROLL ULTRA SMOOTH =================
    document.querySelectorAll(".scroll-ranking").forEach(table => {

        const container = table.closest(".ranking-window");
        const tbody = table.querySelector("tbody");
        if (!tbody || !container) return;

        let rows = Array.from(tbody.children);
        if (rows.length <= 3) return;

        // CLONAGE DES LIGNES pour scroll infini
        rows.forEach(row => {
            const clone = row.cloneNode(true);

            // Fix span joueur dans clone
            const playerSpan = clone.querySelector(".player span");
            if (playerSpan) {
                playerSpan.style.whiteSpace = "nowrap";
                playerSpan.style.overflow = "hidden";
                playerSpan.style.textOverflow = "ellipsis";
                playerSpan.style.display = "block";
                playerSpan.style.width = "100%";
            }

            tbody.appendChild(clone);
        });

        // SCROLL variables
        let scrollY = 0;
        let speed = 0.5; // ajuste la vitesse
        const rowHeight = rows[0].offsetHeight; // hauteur d'une ligne
        const totalHeight = rowHeight * rows.length;

        function animate() {
            scrollY += speed;
            if (scrollY >= totalHeight) scrollY = 0;
            container.scrollTop = scrollY;
            requestAnimationFrame(animate);
        }

        animate();

        // PAUSE AU HOVER
        container.addEventListener("mouseenter", () => speed = 0);
        container.addEventListener("mouseleave", () => speed = 0.5);

    });

    // ================= PODIUM =================
    function animatePodium() {
        const rows = document.querySelectorAll(".top-ranking tbody tr");
        if (rows.length < 3) return;

        const p1El = document.getElementById("p1-name");
        const p2El = document.getElementById("p2-name");
        const p3El = document.getElementById("p3-name");

        if (p1El) p1El.innerText = rows[0].querySelector(".player span")?.innerText || "";
        if (p2El) p2El.innerText = rows[1].querySelector(".player span")?.innerText || "";
        if (p3El) p3El.innerText = rows[2].querySelector(".player span")?.innerText || "";

        const podium = document.querySelectorAll(".podium-player");
        podium.forEach((p, i) => {
            setTimeout(() => {
                p.style.transition = "0.6s";
                p.style.opacity = 1;
                p.style.transform = "translateY(0)";
            }, i * 300);
        });
    }

    animatePodium();

});
// ================= HISTORIQUE DES MATCHS =================
// matches est injecté depuis Flask dans index.html :
// <script>const matches = {{ matches | tojson }};</script>

document.addEventListener("DOMContentLoaded", () => {

    // ================= INIT TABLE =================
    function initHistory(id, data) {
        const tbody = document.getElementById(id);
        if (!tbody) return; // sécurité anti-crash

        let html = "";

        // contenu principal
        data.forEach(m => {
            html += `
            <tr>
                <img src="${m.playerA_photo}" class="img-player">
                <td class="score-history">${m.scoreA} vs ${m.scoreB}</td>
                <img src="${m.playerB_photo}" class="img-player">
            </tr>`;
        });

        //<td>${m.playerA_name}</td>
        //<td>${m.playerB_name}</td>

        // duplication pour effet boucle infinie
        data.slice(0, 2).forEach(m => {
            html += `
            <tr>
                <img src="${m.playerA_photo}" class="img-player">
                <td class="score-history">${m.scoreA} vs ${m.scoreB}</td>
                <img src="${m.playerB_photo}" class="img-player">
            </tr>`;
        });
        //<td>${m.playerA_name}</td>
        // <td>${m.playerB_name}</td>

        tbody.innerHTML = html;
    }

    // ================= ANIMATION =================
    function animateTable(id, dataLength) {
        const tbody = document.getElementById(id);
        if (!tbody) return;

        // Calculer dynamiquement la hauteur réelle de la première ligne
        const firstRow = tbody.querySelector("tr");
        const rowHeight = firstRow ? firstRow.offsetHeight : 150;

        let index = 0;
        const maxIndex = dataLength;

        tbody.style.transition = "transform 0.6s ease";

        setInterval(() => {
            index++;
            tbody.style.transform = `translateY(-${index * rowHeight}px)`;

            if (index >= maxIndex) {
                setTimeout(() => {
                    tbody.style.transition = "none";
                    tbody.style.transform = "translateY(0)";
                    index = 0;

                    // réactive transition
                    requestAnimationFrame(() => {
                        tbody.style.transition = "transform 0.6s ease";
                    });

                }, 600);
            }

        }, 2500);
    }

    // ================= INITIALISATION =================
    // Historiques séparés : duel / goal
    initHistory("duelHistory", matchesDuel);
    initHistory("goalHistory", matchesGoal);

    animateTable("duelHistory", matchesDuel.length);
    animateTable("goalHistory", matchesGoal.length);

});