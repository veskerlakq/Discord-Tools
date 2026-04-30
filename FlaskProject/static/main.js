
const translations = {
    en: {
        dashboard: "Dashboard",
        welcome: "Welcome",
        bot: "Bot Generator",
        templates: "Server Templates",
        open: "Open"
    },
    ru: {
        dashboard: "Панель",
        welcome: "Добро пожаловать",
        bot: "Генератор ботов",
        templates: "Шаблоны серверов",
        open: "Открыть"
    }
};

let lang = localStorage.getItem("lang") || "en";
let theme = localStorage.getItem("theme") || "dark";

document.addEventListener("DOMContentLoaded", () => {
    applyLang();
    applyTheme();
});

function toggleLang() {
    lang = (lang === "en") ? "ru" : "en";
    localStorage.setItem("lang", lang);
    applyLang();
}

function applyLang() {
    document.getElementById("langText").innerText = lang.toUpperCase();

    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (translations[lang][key]) {
            el.innerText = translations[lang][key];
        }
    });
}

function toggleTheme() {
    theme = (theme === "dark") ? "light" : "dark";
    localStorage.setItem("theme", theme);
    applyTheme();
}

function applyTheme() {
    document.body.classList.remove("dark", "light");
    document.body.classList.add(theme);
}