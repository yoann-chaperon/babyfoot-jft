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

//ANCHOR - INDEX classement des joueurs START
document.addEventListener("DOMContentLoaded", () => {

    const rows = document.querySelectorAll(".ranking-table tr")

    rows.forEach((row, i) => {

        row.style.opacity = 0
        row.style.transform = "translateX(-20px)"

        setTimeout(() => {

            row.style.transition = "0.4s"

            row.style.opacity = 1

            row.style.transform = "translateX(0)"

        }, i * 80)

    })

})
// défilement automatique du classement
document.querySelectorAll(".scroll-ranking").forEach(table => {

    const body = table.querySelector("tbody")

    body.innerHTML += body.innerHTML

})

// podium animation
function animatePodium() {

    const rows = document.querySelectorAll(".scroll-ranking tbody tr")

    if (rows.length < 3) return

    document.getElementById("p1-name").innerText = rows[0].children[1].innerText
    document.getElementById("p2-name").innerText = rows[1].children[1].innerText
    document.getElementById("p3-name").innerText = rows[2].children[1].innerText

    const podium = document.querySelectorAll(".podium-player")

    podium.forEach((p, i) => {

        setTimeout(() => {

            p.style.transition = "0.6s"
            p.style.opacity = 1
            p.style.transform = "translateY(0)"

        }, i * 300)

    })

}

document.addEventListener("DOMContentLoaded", animatePodium)

// ANCHOR tableau historique des rencontres

const matches = [
    { date: "14/04", adv: "Michel", score: "3-2" },
    { date: "13/04", adv: "Paul", score: "2-1" },
    { date: "12/04", adv: "Julien", score: "1-0" },
    { date: "11/04", adv: "Lucas", score: "2-2" },
    { date: "10/04", adv: "Nico", score: "4-3" }
];

function initHistory(id) {

    const tbody = document.getElementById(id);

    matches.forEach(m => {
        tbody.innerHTML += `
        <tr>
            <td>${m.date}</td>
            <td>${m.adv}</td>
            <td>${m.score}</td>
        </tr>`;
    });

    // clone pour boucle infinie
    matches.slice(0, 2).forEach(m => {
        tbody.innerHTML += `
        <tr>
            <td>${m.date}</td>
            <td>${m.adv}</td>
            <td>${m.score}</td>
        </tr>`;
    });

}

initHistory("duelHistory");
initHistory("goalHistory");

function animateTable(id) {

    const tbody = document.getElementById(id);

    let index = 0;
    const rowHeight = 42;

    setInterval(() => {

        index++;

        tbody.style.transform =
            `translateY(-${index * rowHeight}px)`;

        if (index === matches.length) {

            setTimeout(() => {

                tbody.style.transition = "none";
                tbody.style.transform = "translateY(0)";
                index = 0;

                setTimeout(() => {
                    tbody.style.transition = "transform 0.6s ease";
                }, 50);

            }, 600);

        }

    }, 2500);

}

animateTable("duelHistory");
animateTable("goalHistory");

// ANCHOR - preview background carte
function updateCardPreview() {

    let card = "/static/img/cards/bronze.png"   // masculin défaut

    const sexe = document.querySelector('[name="sexe"]').value
    const interclub = document.querySelector('[name="interclub"]').checked


    // FEMININ
    if (sexe === "F") {
        card = "/static/img/cards/rose.png"
    }

    // MASCULIN INTERCLUB
    else if (sexe === "M" && interclub) {
        card = "/static/img/cards/argent.png"
    }

    // MASCULIN NON INTERCLUB
    else if (sexe === "M" && !interclub) {
        card = "/static/img/cards/bronze.png"
    }

    document.getElementById("card_bg").src = card

}

// ANCHOR chbb
document.querySelectorAll(".chbb-select").forEach(select => {

    select.addEventListener("change", function () {

        fetch("/admin/chbb/update", {

            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },

            body:
            "player_id="+this.dataset.id +
                "&value=" + this.value

        }).then(() => location.reload())

    })

})