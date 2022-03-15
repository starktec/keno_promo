document.querySelectorAll(".number-balls").forEach(botao => {
    botao.addEventListener("click", () => botao.classList.toggle("number-balls-active"));
})