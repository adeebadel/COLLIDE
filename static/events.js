
/* =========================================================
   COLLIDE — EVENTS & EXPERIENCES
   Event creation, RSVP, attendance, feedback and analytics
========================================================= */

const EVENTS_API = "/api";

let allEvents = [];
let activeEventFilter = "all";
let currentEventDetails = null;

async function eventAPI(path, options = {}) {
    const response = await fetch(EVENTS_API + path, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || `Request failed (${response.status})`);
    }

    return data;
}

function eventEscape(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

function eventToast(message) {
    if (typeof toast === "function") {
        toast(message);
    } else {
        alert(message);
    }
}

function getEventMemberId() {
    return Number(document.getElementById("memberSelect")?.value || 0);
}

function eventDateLabel(dateValue) {
    if (!dateValue) return "Date to be announced";

    const date = new Date(`${dateValue}T00:00:00`);

    if (Number.isNaN(date.getTime())) return dateValue;

    return date.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric"
    });
}

function eventTimeLabel(timeValue) {
    if (!timeValue) return "";

    const [hours, minutes] = timeValue.split(":");
    const date = new Date();

    date.setHours(Number(hours), Number(minutes), 0, 0);

    return date.toLocaleTimeString("en-IN", {
        hour: "numeric",
        minute: "2-digit"
    });
}

/* LOAD EVENTS */

async function loadEvents(filter = activeEventFilter) {
    activeEventFilter = filter;

    const grid = document.getElementById("eventGrid");
    if (!grid) return;

    grid.innerHTML = `<div class="loading">Loading events...</div>`;

    try {
        const result = await eventAPI("/events");

        allEvents = Array.isArray(result)
            ? result
            : (result.events || []);

        renderEvents(activeEventFilter);

    } catch (error) {
        console.error("Load events error:", error);
        grid.innerHTML = `
            <div class="empty">
                ${eventEscape(error.message)}
            </div>
        `;
    }
}

/* RENDER EVENT CARDS */

function renderEvents(filter = "all") {
    const grid = document.getElementById("eventGrid");
    if (!grid) return;

    let visibleEvents = [...allEvents];

    if (filter !== "all") {
        visibleEvents = visibleEvents.filter(
            event => event.status === filter
        );
    }

    visibleEvents.sort((a, b) => {
        return new Date(a.event_date) - new Date(b.event_date);
    });

    if (!visibleEvents.length) {
        grid.innerHTML = `
            <div class="empty">
                No ${filter === "all" ? "" : filter + " "}events yet.
                Be the first to create an experience.
            </div>
        `;
        return;
    }

    grid.innerHTML = visibleEvents.map(event => {
        const eventId = Number(event.id);
        const registered = event.my_status === "registered";
        const attended = event.my_status === "attended";
        const cancelled = event.my_status === "cancelled";

        const capacity = Number(event.capacity || 0);
        const registrations = Number(event.registration_count || 0);
        const spotsLeft = capacity > 0
            ? Math.max(0, capacity - registrations)
            : null;

        const isFull = capacity > 0 && spotsLeft <= 0;
        const isCreator = Number(event.created_by) === getEventMemberId();

        let actionButton = "";

        if (registered) {
            actionButton = `
                <button class="outline-btn"
                    onclick="cancelEventRSVP(${eventId})">
                    Cancel registration
                </button>
            `;
        } else if (attended) {
            actionButton = `
                <button class="outline-btn" disabled>
                    ✓ Attended
                </button>
            `;
        } else if (event.status === "completed") {
            actionButton = `
                <button class="outline-btn" disabled>
                    Event completed
                </button>
            `;
        } else if (event.status === "cancelled") {
            actionButton = `
                <button class="outline-btn" disabled>
                    Event cancelled
                </button>
            `;
        } else if (isFull) {
            actionButton = `
                <button class="outline-btn" disabled>
                    Event full
                </button>
            `;
        } else {
            actionButton = `
                <button class="primary-btn"
                    onclick="rsvpToEvent(${eventId})">
                    I'm interested ↗
                </button>
            `;
        }

        return `
            <article class="event-card">
                <div class="event-card-top">
                    <span class="tag">
                        ${eventEscape((event.category || "EVENT").toUpperCase())}
                    </span>

                    <span class="event-status">
                        ${eventEscape((event.status || "upcoming").toUpperCase())}
                    </span>
                </div>

                <div class="event-date-block">
                    <span class="event-date-day">
                        ${eventEscape(
                            event.event_date
                                ? event.event_date.split("-")[2]
                                : "—"
                        )}
                    </span>
                    <span class="event-date-month">
                        ${eventEscape(
                            event.event_date
                                ? new Date(`${event.event_date}T00:00:00`)
                                    .toLocaleDateString("en-IN", { month: "short" })
                                : ""
                        )}
                    </span>
                </div>

                <h3>${eventEscape(event.title)}</h3>

                <p>${eventEscape(event.description)}</p>

                <div class="event-meta">
                    <span>◷ ${eventEscape(eventTimeLabel(event.event_time))}</span>
                    <span>⌖ ${eventEscape(event.venue)}</span>
                </div>

                <div class="event-card-footer">
                    <span>
                        ${registrations} registered
                        ${capacity > 0 ? `· ${spotsLeft} spots left` : ""}
                    </span>
                    <span>By ${eventEscape(event.creator_name || "Community member")}</span>
                </div>

                <div class="event-actions">
                    ${actionButton}
                    <button class="text-btn"
                        onclick="openEventDetails(${eventId})">
                        View details ↗
                    </button>
                </div>

                ${isCreator ? `
                    <div class="event-organiser-note">
                        You organised this event.
                    </div>
                ` : ""}
            </article>
        `;
    }).join("");
}

/* CREATE EVENT */

async function createEvent(event) {
    event.preventDefault();

    const form = event.target;
    const data = Object.fromEntries(new FormData(form));

    data.created_by = Number(data.created_by);
    data.capacity = Number(data.capacity);

    if (!data.created_by) {
        eventToast("Please select an event organiser.");
        return;
    }

    if (data.capacity < 0) {
        eventToast("Capacity cannot be negative.");
        return;
    }

    try {
        const result = await eventAPI("/events", {
            method: "POST",
            body: JSON.stringify(data)
        });

        form.reset();

        if (typeof closeModal === "function") {
            closeModal("eventModal");
        }

        eventToast(result.message || "Event created successfully!");

        await loadEvents("all");

    } catch (error) {
        console.error("Create event error:", error);
        eventToast(error.message);
    }
}

/* RSVP */

async function rsvpToEvent(eventId) {
    const memberId = getEventMemberId();

    if (!memberId) {
        eventToast("Select a member first.");
        return;
    }

    try {
        const result = await eventAPI(`/events/${eventId}/rsvp`, {
            method: "POST",
            body: JSON.stringify({
                member_id: memberId
            })
        });

        eventToast(result.message || "You're registered!");

        await loadEvents();

        if (currentEventDetails === Number(eventId)) {
            await openEventDetails(eventId);
        }

    } catch (error) {
        eventToast(error.message);
    }
}

/* CANCEL RSVP */

async function cancelEventRSVP(eventId) {
    const memberId = getEventMemberId();

    if (!confirm("Cancel your registration for this event?")) {
        return;
    }

    try {
        const result = await eventAPI(`/events/${eventId}/rsvp`, {
            method: "DELETE",
            body: JSON.stringify({
                member_id: memberId
            })
        });

        eventToast(result.message || "Registration cancelled.");

        await loadEvents();

        if (currentEventDetails === Number(eventId)) {
            await openEventDetails(eventId);
        }

    } catch (error) {
        eventToast(error.message);
    }
}

/* EVENT DETAILS */

async function openEventDetails(eventId) {
    const modal = document.getElementById("eventDetailsModal");
    const content = document.getElementById("eventDetailsContent");

    if (!modal || !content) return;

    currentEventDetails = Number(eventId);

    modal.classList.add("open");
    content.innerHTML = `<div class="loading">Loading event details...</div>`;

    try {
        const [eventResult, attendeeResult, analytics] = await Promise.all([
            eventAPI(`/events/${eventId}`),
            eventAPI(`/events/${eventId}/attendees`),
            eventAPI(`/events/${eventId}/analytics`)
        ]);

        const event = eventResult.event || eventResult;
        const attendees = Array.isArray(attendeeResult)
            ? attendeeResult
            : (attendeeResult.attendees || []);

        const memberId = getEventMemberId();
        const isCreator = Number(event.created_by) === memberId;
        const myAttendance = attendees.find(
            person => Number(person.member_id) === memberId
        );

        const canGiveFeedback = myAttendance &&
            ["attended", "registered"].includes(myAttendance.attendance_status);

        const attendeeHTML = attendees.length
            ? attendees.map(person => {
                const attended = person.attendance_status === "attended";

                return `
                    <div class="event-attendee">
                        <div>
                            <strong>${eventEscape(person.member_name || person.name)}</strong>
                            <small>
                                ${eventEscape(
                                    person.attendance_status || "registered"
                                )}
                            </small>
                        </div>

                        ${isCreator && person.attendance_status !== "cancelled" ? `
                            <button class="outline-btn"
                                onclick="markEventAttendance(
                                    ${Number(eventId)},
                                    ${Number(person.member_id)},
                                    ${!attended}
                                )">
                                ${attended ? "Undo attendance" : "Mark attended"}
                            </button>
                        ` : ""}
                    </div>
                `;
            }).join("")
            : `<div class="empty">No registrations yet.</div>`;

        content.innerHTML = `
            <div class="eyebrow">COMMUNITY EXPERIENCE</div>

            <h2>${eventEscape(event.title)}<span>.</span></h2>

            <span class="tag">
                ${eventEscape((event.category || "EVENT").toUpperCase())}
            </span>

            <p class="event-detail-description">
                ${eventEscape(event.description)}
            </p>

            <div class="event-detail-meta">
                <div><strong>DATE</strong><span>${eventEscape(eventDateLabel(event.event_date))}</span></div>
                <div><strong>TIME</strong><span>${eventEscape(eventTimeLabel(event.event_time))}</span></div>
                <div><strong>VENUE</strong><span>${eventEscape(event.venue)}</span></div>
                <div><strong>ORGANISER</strong><span>${eventEscape(event.creator_name || "Community member")}</span></div>
            </div>

            <div class="event-analytics-grid">
                <div><strong>${Number(analytics.registrations || 0)}</strong><small>Registrations</small></div>
                <div><strong>${Number(analytics.attended || 0)}</strong><small>Attended</small></div>
                <div><strong>${Number(analytics.attendance_rate || 0)}%</strong><small>Attendance rate</small></div>
                <div><strong>${Number(analytics.average_rating || 0).toFixed(1)} / 5</strong><small>Average rating</small></div>
            </div>

            <div class="event-detail-section">
                <h3>Who's coming?</h3>
                <div class="event-attendee-list">
                    ${attendeeHTML}
                </div>
            </div>

            ${canGiveFeedback ? `
                <div class="event-detail-section">
                    <h3>Share your experience</h3>

                    <form id="eventFeedbackForm">
                        <label>YOUR RATING</label>
                        <select name="rating" class="form-control" required>
                            <option value="5">5 — Excellent</option>
                            <option value="4">4 — Great</option>
                            <option value="3">3 — Good</option>
                            <option value="2">2 — Could be better</option>
                            <option value="1">1 — Poor</option>
                        </select>

                        <label>YOUR FEEDBACK</label>
                        <textarea name="feedback" class="form-control"
                            maxlength="1000"
                            placeholder="What worked? What could improve?"
                            required></textarea>

                        <button class="primary-btn full-btn" type="submit">
                            Submit feedback ↗
                        </button>
                    </form>
                </div>
            ` : ""}

            ${analytics.feedback && analytics.feedback.length ? `
                <div class="event-detail-section">
                    <h3>Community feedback</h3>
                    ${analytics.feedback.map(item => `
                        <div class="event-feedback-item">
                            <strong>${eventEscape(item.member_name || "Attendee")}</strong>
                            <span>${"★".repeat(Number(item.rating || 0))}</span>
                            <p>${eventEscape(item.feedback || "")}</p>
                        </div>
                    `).join("")}
                </div>
            ` : ""}
        `;

        const feedbackForm = document.getElementById("eventFeedbackForm");

        if (feedbackForm) {
            feedbackForm.addEventListener("submit", submitEventFeedback);
        }

    } catch (error) {
        console.error("Event details error:", error);
        content.innerHTML = `
            <div class="empty">${eventEscape(error.message)}</div>
        `;
    }
}

/* MARK ATTENDANCE — ORGANISER */

async function markEventAttendance(eventId, attendeeId, attended) {
    const creatorId = getEventMemberId();

    try {
        const result = await eventAPI(`/events/${eventId}/attendance`, {
            method: "PATCH",
            body: JSON.stringify({
                creator_id: creatorId,
                member_id: attendeeId,
                attended
            })
        });

        eventToast(result.message || "Attendance updated.");

        await loadEvents();
        await openEventDetails(eventId);

    } catch (error) {
        eventToast(error.message);
    }
}

/* SUBMIT FEEDBACK */

async function submitEventFeedback(event) {
    event.preventDefault();

    const eventId = currentEventDetails;
    const memberId = getEventMemberId();
    const data = Object.fromEntries(new FormData(event.target));

    data.member_id = memberId;
    data.rating = Number(data.rating);

    try {
        const result = await eventAPI(`/events/${eventId}/feedback`, {
            method: "POST",
            body: JSON.stringify(data)
        });

        eventToast(result.message || "Thanks for sharing your feedback!");

        await openEventDetails(eventId);

    } catch (error) {
        eventToast(error.message);
    }
}

/* INITIALIZE EVENTS */

document.addEventListener("DOMContentLoaded", () => {
    const eventForm = document.getElementById("eventForm");

    if (eventForm) {
        eventForm.addEventListener("submit", createEvent);
    }

    document.querySelectorAll("[data-event-filter]").forEach(button => {
        button.addEventListener("click", () => {
            document.querySelectorAll("[data-event-filter]").forEach(item => {
                item.classList.remove("active");
            });

            button.classList.add("active");
            loadEvents(button.dataset.eventFilter);
        });
    });

    const eventDateInput = document.querySelector(
        '#eventForm input[name="event_date"]'
    );

    if (eventDateInput) {
        const today = new Date();
        const localDate = [
            today.getFullYear(),
            String(today.getMonth() + 1).padStart(2, "0"),
            String(today.getDate()).padStart(2, "0")
        ].join("-");

        eventDateInput.min = localDate;
    }

    window.loadEvents = loadEvents;
    window.renderEvents = renderEvents;
    window.rsvpToEvent = rsvpToEvent;
    window.cancelEventRSVP = cancelEventRSVP;
    window.openEventDetails = openEventDetails;
    window.markEventAttendance = markEventAttendance;

    loadEvents();
});
