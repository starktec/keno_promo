document.querySelectorAll("button.theme-btn").forEach(btn => {
    btn.addEventListener("click",() => SendTheme(btn.getAttribute("value")));
    })

    document.querySelectorAll("button.theme-btn2").forEach(btn => {
        btn.addEventListener("click", () => SendName(btn.getAttribute("value")));
    })

    function SendTheme(theme){
        fetch(`http://0745f62ec521.ngrok.io/api/v1/broadcast/32/update_theme/${theme}`, {
        method: "POST",
    })
        // .then((response) => {alert("Recebido")})
        }
    function SendName(name) {
        fetch(`http://0745f62ec521.ngrok.io/api/v1/broadcast/32/update_name/${name}`, {
        method: "POST",
    })
    .then((response) => {alert("Recebido")})
}