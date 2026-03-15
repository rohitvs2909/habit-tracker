const completeCountEl = document.getElementById("completeCount");
const incompleteCountEl = document.getElementById("incompleteCount");
const percentageCountEl = document.getElementById("percentageCount");
const addHabitBtn = document.getElementById("addHabitBtn");
const newHabitInput = document.getElementById("newHabitInput");
const habitCategorySelect = document.getElementById("habitCategorySelect");
const pageShell = document.querySelector(".page-shell");
const monthLabelEl = document.getElementById("monthLabel");
const liveNowEl = document.getElementById("liveNow");
const progressPieEl = document.getElementById("progressPie");
const pieCaptionEl = document.getElementById("pieCaption");
let monthlyGridAutoScrolled = false;

function updatePieChart(complete, incomplete) {
    if (!progressPieEl || !pieCaptionEl) {
        return;
    }

    const total = Math.max(complete + incomplete, 0);
    const completePct = total ? (complete / total) * 100 : 0;
    const incompletePct = Math.max(100 - completePct, 0);
    const degrees = (completePct / 100) * 360;

    progressPieEl.style.background = `conic-gradient(#96c9a3 0deg, #96c9a3 ${degrees}deg, #ecd7b7 ${degrees}deg 360deg)`;
    progressPieEl.dataset.label = `${completePct.toFixed(1)}%`;
    pieCaptionEl.textContent = `Complete ${completePct.toFixed(1)}% | Incomplete ${incompletePct.toFixed(1)}%`;
}

function scrollMonthlyGridToCurrentDay(day) {
    if (monthlyGridAutoScrolled) {
        return;
    }

    const container = document.querySelector(".monthly-grid-scroll");
    const header = document.querySelector(`.habit-grid-table th[data-day=\"${day}\"]`);
    if (!container || !header) {
        return;
    }

    const target = Math.max(header.offsetLeft - 120, 0);
    container.scrollTo({ left: target, behavior: "smooth" });
    monthlyGridAutoScrolled = true;
}

function formatLiveDateTime(date) {
    return new Intl.DateTimeFormat(undefined, {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    }).format(date);
}

function refreshRealtimeCalendar() {
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    const today = now.getDate();
    const currentWeek = Math.min(Math.ceil(today / 7), 5);

    scrollMonthlyGridToCurrentDay(today);

    if (liveNowEl) {
        liveNowEl.textContent = formatLiveDateTime(now);
    }

    if (monthLabelEl) {
        const monthName = new Intl.DateTimeFormat(undefined, { month: "long" }).format(now);
        monthLabelEl.textContent = `${monthName} ${currentYear}`;
    }

    document.querySelectorAll(".current-day-col").forEach((el) => {
        el.classList.remove("current-day-col");
    });
    document.querySelectorAll(".current-day-cell").forEach((el) => {
        el.classList.remove("current-day-cell");
    });
    document.querySelectorAll(".current-week-col").forEach((el) => {
        el.classList.remove("current-week-col");
    });
    document.querySelectorAll(".current-week-cell").forEach((el) => {
        el.classList.remove("current-week-cell");
    });

    const header = document.querySelector(`.habit-grid-table th[data-day=\"${today}\"]`);
    if (header) {
        header.classList.add("current-day-col");
    }

    document.querySelectorAll(`.habit-grid-table input[data-type=\"daily\"][data-day=\"${today}\"]`).forEach((input) => {
        const cell = input.closest("td");
        if (cell) {
            cell.classList.add("current-day-cell");
        }
    });

    const weeklyHeader = document.querySelector(`.secondary-table th[data-week=\"${currentWeek}\"]`);
    if (weeklyHeader) {
        weeklyHeader.classList.add("current-week-col");
    }

    document.querySelectorAll(`.secondary-table input[data-type=\"weekly\"][data-week=\"${currentWeek}\"]`).forEach((input) => {
        const cell = input.closest("td");
        if (cell) {
            cell.classList.add("current-week-cell");
        }
    });

    if (pageShell) {
        const pageYear = Number(pageShell.dataset.year);
        const pageMonth = Number(pageShell.dataset.month);
        if (pageYear !== currentYear || pageMonth !== currentMonth) {
            window.location.reload();
        }
    }
}

function updateStatsFromDom() {
    const dailyCheckboxes = document.querySelectorAll(".daily-checkbox");
    const complete = Array.from(dailyCheckboxes).filter((box) => box.checked).length;
    const total = dailyCheckboxes.length;
    const incomplete = Math.max(total - complete, 0);
    const percentage = total ? ((complete / total) * 100).toFixed(1) : "0.0";

    completeCountEl.textContent = String(complete);
    incompleteCountEl.textContent = String(incomplete);
    percentageCountEl.textContent = `${percentage}%`;
    updatePieChart(complete, incomplete);
}

function renderStats(stats) {
    if (!stats) {
        updateStatsFromDom();
        return;
    }

    completeCountEl.textContent = String(stats.complete);
    incompleteCountEl.textContent = String(stats.incomplete);
    percentageCountEl.textContent = `${Number(stats.percentage).toFixed(1)}%`;
    updatePieChart(Number(stats.complete) || 0, Number(stats.incomplete) || 0);
}

document.querySelectorAll(".habit-checkbox").forEach((checkbox) => {
    checkbox.addEventListener("change", async (event) => {
        const target = event.currentTarget;
        const type = target.dataset.type;
        const habitId = Number(target.dataset.habitId);
        const checked = target.checked;

        const payload = {
            type,
            habit_id: habitId,
            checked
        };

        if (type === "daily") {
            payload.day = Number(target.dataset.day);
        }

        if (type === "weekly") {
            payload.week = Number(target.dataset.week);
        }

        try {
            const response = await fetch("/api/toggle", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error("Failed to update checkbox state");
            }

            const data = await response.json();
            renderStats(data.stats);
        } catch (error) {
            console.error(error);
            target.checked = !checked;
            updateStatsFromDom();
            alert("Could not save this checkbox right now.");
        }
    });
});

async function saveHabitNameToBackend(group, habitId, name) {
    const response = await fetch(`/api/habits/${group}/${habitId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
    });

    if (!response.ok) {
        throw new Error("Failed to update habit name");
    }
}

document.querySelectorAll(".editable-habit-name").forEach((element) => {
    element.dataset.originalName = element.textContent.trim();

    element.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            event.currentTarget.blur();
        }
    });

    element.addEventListener("blur", async (event) => {
        const target = event.currentTarget;
        const nextValue = target.textContent.trim();
        const previousValue = target.dataset.originalName || "";
        const group = target.dataset.group;
        const habitId = Number(target.dataset.habitId);

        if (!nextValue) {
            target.textContent = previousValue;
            return;
        }

        if (nextValue === previousValue) {
            return;
        }

        try {
            await saveHabitNameToBackend(group, habitId, nextValue);
            target.textContent = nextValue;
            target.dataset.originalName = nextValue;
        } catch (error) {
            console.error(error);
            target.textContent = previousValue;
            alert("Could not update this habit name right now.");
            return;
        }
    });
});

async function addHabit() {
    const habitName = newHabitInput.value.trim();
    const category = habitCategorySelect.value;

    if (!habitName) {
        alert("Please enter a habit name.");
        return;
    }

    try {
        const response = await fetch("/api/habits", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: habitName, category })
        });

        if (!response.ok) {
            throw new Error("Failed to add habit");
        }

        window.location.reload();
    } catch (error) {
        console.error(error);
        alert("Could not add habit right now. Please try again.");
    }
}

if (addHabitBtn) {
    addHabitBtn.addEventListener("click", addHabit);
}

if (newHabitInput) {
    newHabitInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            addHabit();
        }
    });
}

document.querySelectorAll(".delete-habit-btn").forEach((button) => {
    button.addEventListener("click", async (event) => {
        const target = event.currentTarget;
        const group = target.dataset.group;
        const habitId = Number(target.dataset.habitId);
        const habitName = (target.dataset.habitName || "this habit").trim();

        const isConfirmed = window.confirm(`Delete "${habitName}"?`);
        if (!isConfirmed) {
            return;
        }

        try {
            const response = await fetch(`/api/habits/${group}/${habitId}`, {
                method: "DELETE"
            });

            if (!response.ok) {
                throw new Error("Failed to delete habit");
            }

            window.location.reload();
        } catch (error) {
            console.error(error);
            alert("Could not delete this habit right now.");
        }
    });
});

updateStatsFromDom();
refreshRealtimeCalendar();
setInterval(refreshRealtimeCalendar, 1000);
