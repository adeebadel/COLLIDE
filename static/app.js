
const API = "/api";

let allSignals = [];
let members = [];
let workspaceTaskFilter = "all";

/* =========================================================
   API + UTILITIES
========================================================= */

async function api(path, options = {}) {
    const response = await fetch(API + path, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error(`Invalid server response (${response.status})`);
    }

    if (!response.ok) {
        throw new Error(data.error || `Request failed (${response.status})`);
    }

    return data;
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

function toast(message) {
    const element = document.getElementById("toast");
    if (!element) return;

    element.textContent = message;
    element.classList.add("show");

    setTimeout(() => element.classList.remove("show"), 3000);
}

function openModal(id) {
    document.getElementById(id)?.classList.add("open");
}

function closeModal(id) {
    document.getElementById(id)?.classList.remove("open");
}

function scrollToSection(id) {
    document.getElementById(id)?.scrollIntoView({
        behavior: "smooth"
    });
}

function memberName(id) {
    return members.find(m => Number(m.id) === Number(id))?.name
        || "Community member";
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value ?? 0;
}

function setWidth(id, value) {
    const element = document.getElementById(id);
    if (!element) return;

    const percentage = Math.max(
        0,
        Math.min(100, Number(value) || 0)
    );

    element.style.width = `${percentage}%`;
}

/* =========================================================
   COMMUNITY DASHBOARD
========================================================= */

async function loadDashboard() {
    const data = await api("/dashboard");

    setText("memberCount", data.members);
    setText("signalCount", data.open_signals);
    setText("collabCount", data.active_collaborations);
    setText("updateCount", data.project_updates);

    const community = data.community || {};
    const engagement = data.engagement || {};
    const events = data.events || {};
    const projects = data.projects || {};
    const tasks = data.tasks || {};

    const health = Number(community.health_score) || 0;

    setText("healthScore", `${health}%`);
    setText("healthActiveMembers", community.active_members_30_days || 0);
    setText("healthAttendance", `${events.attendance_rate || 0}%`);
    setText("healthProjects", projects.multi_member_projects || 0);
    setText("healthTasks", `${tasks.completion_rate || 0}%`);

    setWidth("healthMeterFill", health);

    const healthDescription =
        document.getElementById("healthDescription");

    if (healthDescription) {
        if (health >= 80) {
            healthDescription.textContent =
                "Strong community activity. Keep creating opportunities for people to connect.";
        } else if (health >= 60) {
            healthDescription.textContent =
                "Your community is showing promising activity. There is room to strengthen participation.";
        } else if (health >= 40) {
            healthDescription.textContent =
                "Some activity is happening, but more member participation and collaboration could help.";
        } else {
            healthDescription.textContent =
                "Your community needs more activity. Start conversations and create opportunities to collaborate.";
        }
    }

    // Community metrics
    setText("dashTotalMembers",
        community.total_members ?? data.members ?? 0);
    setText("dashActiveMembers",
        community.active_members_30_days || 0);
    setText("dashReturningMembers",
        community.returning_members_30_days || 0);
    setText("dashInactiveMembers",
        community.inactive_members || 0);

    // Connections
    setText("dashAcceptedConnections",
        engagement.accepted_connections || 0);
    setText("dashPendingConnections",
        engagement.pending_connections || 0);
    setText("dashMemberships",
        engagement.total_project_memberships || 0);

    // Projects
    setText("dashActiveProjects", projects.active || 0);
    setText("dashCompletedProjects", projects.completed || 0);
    setText("dashProjectUpdates", projects.updates || 0);

    // Events
    setText("dashTotalEvents", events.total_events || 0);
    setText("dashRegistrations", events.registrations || 0);
    setText("dashAttended", events.attended || 0);
    setText("dashAttendanceRate",
        `${events.attendance_rate || 0}%`);

    const rating = Number(events.average_rating);
    setText(
        "dashEventRating",
        Number.isFinite(rating) && rating > 0
            ? `Average event rating: ${rating.toFixed(1)}/5`
            : "Average event rating: —"
    );

    setWidth("dashAttendanceBar", events.attendance_rate || 0);

    // Tasks
    setText("dashTotalTasks", tasks.total || 0);
    setText("dashCompletedTasks", tasks.completed || 0);
    setText("dashPendingTasks", tasks.pending || 0);
    setText("dashInProgressTasks",
        `In progress: ${tasks.in_progress || 0}`);
    setText("dashTaskRate",
        `${tasks.completion_rate || 0}%`);

    setWidth("dashTaskBar", tasks.completion_rate || 0);

    // Recent activity
    renderDashboardActivity(data.recent_activity || []);

    return data;
}

function renderDashboardActivity(activity) {
    const container = document.getElementById("dashboardActivity");
    if (!container) return;

    if (!activity.length) {
        container.innerHTML = `
            <div class="empty">
                No recent activity yet. Signals, connections and project updates
                will appear here as your community grows.
            </div>
        `;
        return;
    }

    container.innerHTML = activity.map(item => `
        <article class="dashboard-activity-item">
            <div class="dashboard-activity-dot"></div>

            <div class="dashboard-activity-content">
                <p>${escapeHTML(item.message || "Community activity")}</p>

                <div class="dashboard-activity-meta">
                    ${escapeHTML(item.member_name || "Community member")}
                    ${item.project_title
                        ? ` · ${escapeHTML(item.project_title)}`
                        : ""}
                    ${item.created_at
                        ? ` · ${escapeHTML(item.created_at)}`
                        : ""}
                </div>
            </div>
        </article>
    `).join("");
}

/* =========================================================
   MEMBERS
========================================================= */

async function loadMembers() {
    members = await api("/members");

    const options = members.map(member => `
        <option value="${Number(member.id)}">
            ${escapeHTML(member.name)}
        </option>
    `).join("");

    const memberSelect = document.getElementById("memberSelect");

    if (memberSelect) {
        memberSelect.innerHTML = options;
    }

    document.querySelectorAll(".member-options").forEach(select => {
        select.innerHTML = options;
    });

    if (memberSelect?.value) {
        setText(
            "currentAvatar",
            memberName(memberSelect.value).charAt(0).toUpperCase()
        );
    }
}

/* =========================================================
   SIGNALS
========================================================= */

async function loadSignals(filter = "all") {
    allSignals = await api("/signals");
    renderSignals(filter);
}

function renderSignals(filter = "all") {
    const visible = filter === "all"
        ? allSignals
        : allSignals.filter(
            signal => signal.signal_type === filter
        );

    const grid = document.getElementById("signalGrid");
    if (!grid) return;

    if (!visible.length) {
        grid.innerHTML = `
            <div class="empty">No signals in this category yet.</div>
        `;
        return;
    }

    grid.innerHTML = visible.map(signal => `
        <article class="signal-card">
            <div class="card-top">
                <span class="tag ${escapeHTML(signal.signal_type)}">
                    ${escapeHTML((signal.signal_type || "").toUpperCase())}
                </span>

                <span class="card-category">
                    ${escapeHTML(signal.category)}
                </span>
            </div>

            <h3>${escapeHTML(signal.title)}</h3>
            <p>${escapeHTML(signal.description)}</p>

            <div class="card-footer">
                <span class="person-name">
                    ${escapeHTML(signal.member_name)}
                </span>
                <span>
                    ${escapeHTML(signal.member_skills || "Community member")}
                </span>
            </div>
        </article>
    `).join("");
}

/* =========================================================
   MEMBER MATCHES
========================================================= */

async function loadMatches() {
    const memberId = document.getElementById("memberSelect")?.value;
    const grid = document.getElementById("matchGrid");

    if (!grid) return;

    if (!memberId) {
        grid.innerHTML = `<div class="empty">Add a member first.</div>`;
        return;
    }

    const avatar = document.getElementById("currentAvatar");

    if (avatar) {
        avatar.textContent =
            memberName(memberId).charAt(0).toUpperCase();
    }

    grid.innerHTML = `
        <div class="loading">Finding your people...</div>
    `;

    try {
        const results = await api(`/matches/${memberId}`);

        if (!results.length) {
            grid.innerHTML = `
                <div class="empty">No other members yet.</div>
            `;
            return;
        }

        grid.innerHTML = results.map(result => `
            <article class="match-card">
                <div class="card-top">
                    <span class="tag">POTENTIAL CONNECTION</span>
                    <span class="match-score">
                        ${Number(result.score) || 0} MATCH POINTS
                    </span>
                </div>

                <h3>${escapeHTML(result.member.name)}</h3>
                <p>${escapeHTML(result.member.bio)}</p>

                <div class="match-reason">
                    ${(result.reasons || []).map(reason => `
                        <div>✳ ${escapeHTML(reason)}</div>
                    `).join("")}
                </div>

                <div class="card-footer">
                    <span>${escapeHTML(result.member.skills)}</span>
                </div>

                <button class="outline-btn"
                    onclick="sendConnectionRequest(${Number(result.member.id)})">
                    Request to collaborate ↗
                </button>
            </article>
        `).join("");

    } catch (error) {
        grid.innerHTML = `
            <div class="empty">${escapeHTML(error.message)}</div>
        `;
    }
}

/* =========================================================
   ACCEPTED CONNECTIONS
========================================================= */

function ensureAcceptedConnectionsSection() {
    let section = document.getElementById(
        "acceptedConnectionsSection"
    );

    if (section) return section;

    const projectsSection = document.getElementById("projects");
    if (!projectsSection) return null;

    section = document.createElement("section");
    section.id = "acceptedConnectionsSection";
    section.className = "section accepted-connections-section";

    section.innerHTML = `
        <div class="section-heading">
            <div>
                <span class="eyebrow">YOUR COMMUNITY CIRCLE</span>
                <h2 class="section-title">Accepted Connections</h2>
                <p class="section-description">
                    Good conversations can become great things.
                    Start building something together.
                </p>
            </div>
        </div>

        <div id="acceptedConnectionGrid" class="match-grid">
            <div class="loading">Finding your connections...</div>
        </div>
    `;

    projectsSection.parentNode.insertBefore(
        section,
        projectsSection
    );

    return section;
}

async function loadAcceptedConnections(requests, memberId) {
    const section = ensureAcceptedConnectionsSection();
    const grid = document.getElementById("acceptedConnectionGrid");

    if (!section || !grid) return;

    const uniqueConnections = new Map();

    requests
        .filter(request => request.status === "accepted")
        .forEach(request => {
            const incoming =
                Number(request.recipient_id) === Number(memberId);

            const otherId = incoming
                ? Number(request.sender_id)
                : Number(request.recipient_id);

            const otherName = incoming
                ? request.sender_name
                : request.recipient_name;

            if (otherId && !uniqueConnections.has(otherId)) {
                uniqueConnections.set(otherId, {
                    id: otherId,
                    name: otherName
                });
            }
        });

    const connections = Array.from(uniqueConnections.values());

    if (!connections.length) {
        grid.innerHTML = `
            <div class="empty">
                No accepted connections yet. When someone accepts your
                request, they'll appear here.
            </div>
        `;
        return;
    }

    grid.innerHTML = connections.map(person => `
        <article class="match-card">
            <div class="card-top">
                <span class="tag">CONNECTED</span>
                <span class="request-status accepted">READY TO BUILD</span>
            </div>

            <h3>${escapeHTML(person.name)}</h3>

            <p>
                You and ${escapeHTML(person.name)} are connected.
                Turn that connection into a shared project.
            </p>

            <button class="primary-btn"
                onclick="startCollaboration(${Number(person.id)})">
                Start a collaboration ↗
            </button>
        </article>
    `).join("");
}

/* =========================================================
   START COLLABORATION
========================================================= */

async function startCollaboration(partnerId) {
    const ownerId = Number(
        document.getElementById("memberSelect").value
    );

    const partner = members.find(
        member => Number(member.id) === Number(partnerId)
    );

    if (!ownerId || !partnerId || ownerId === Number(partnerId)) {
        toast("Please select a valid member first.");
        return;
    }

    const title = prompt(
        `Give your collaboration with ${partner?.name || "your connection"} a title:`
    );

    if (title === null) return;

    if (!title.trim()) {
        toast("A project title is required.");
        return;
    }

    const description = prompt(
        "What are you both planning to build or work on?"
    );

    if (description === null) return;

    if (!description.trim()) {
        toast("Please add a short project description.");
        return;
    }

    const goal = prompt("What would success look like? (Optional)") ?? "";
    const deadline = prompt("Target date (optional, YYYY-MM-DD):") ?? "";

    try {
        const created = await api("/collaborations", {
            method: "POST",
            body: JSON.stringify({
                owner_id: ownerId,
                title: title.trim(),
                description: description.trim(),
                goal: goal.trim(),
                deadline: deadline.trim()
            })
        });

        if (!created.collaboration_id) {
            throw new Error(
                "Project created, but no project ID was returned."
            );
        }

        try {
            await api(
                `/collaborations/${created.collaboration_id}/join`,
                {
                    method: "POST",
                    body: JSON.stringify({
                        member_id: Number(partnerId)
                    })
                }
            );

            toast(
                `Collaboration created with ${partner?.name || "your connection"}!`
            );

        } catch (joinError) {
            toast(
                `Project created, but adding your partner failed: ${joinError.message}`
            );
        }

        await refresh();
        await loadMatches();

    } catch (error) {
        console.error("Start collaboration error:", error);
        toast(error.message);
    }
}

/* =========================================================
   CONNECTION REQUESTS
========================================================= */

async function loadRequests() {
    const memberId = document.getElementById("memberSelect")?.value;
    const grid = document.getElementById("requestGrid");

    if (!memberId || !grid) return;

    grid.innerHTML = `
        <div class="loading">Loading your inbox...</div>
    `;

    try {
        const requests = await api(
            `/requests?member_id=${memberId}`
        );

        await loadAcceptedConnections(requests, memberId);

        const inboxRequests = requests.filter(
            request => request.status !== "accepted"
        );

        if (!inboxRequests.length) {
            grid.innerHTML = `
                <div class="empty">
                    No pending or declined requests.
                    Discover someone and make the first move.
                </div>
            `;
            return;
        }

        grid.innerHTML = inboxRequests.map(request => {
            const incoming =
                Number(request.recipient_id) === Number(memberId);

            const otherPerson = incoming
                ? request.sender_name
                : request.recipient_name;

            let action = "";

            if (incoming && request.status === "pending") {
                action = `
                    <div class="request-actions">
                        <button class="primary-btn"
                            onclick="respondToRequest(${Number(request.id)}, 'accepted')">
                            Accept
                        </button>

                        <button class="outline-btn"
                            onclick="respondToRequest(${Number(request.id)}, 'declined')">
                            Decline
                        </button>
                    </div>
                `;
            }

            return `
                <article class="request-card">
                    <div class="card-top">
                        <span class="tag">
                            ${incoming ? "RECEIVED" : "SENT"}
                        </span>

                        <span class="request-status ${escapeHTML(request.status)}">
                            ${escapeHTML(request.status.toUpperCase())}
                        </span>
                    </div>

                    <h3>${escapeHTML(otherPerson)}</h3>
                    <p>${escapeHTML(request.message)}</p>

                    ${action}
                </article>
            `;
        }).join("");

    } catch (error) {
        grid.innerHTML = `
            <div class="empty">${escapeHTML(error.message)}</div>
        `;
    }
}

async function sendConnectionRequest(recipientId) {
    const senderId = Number(
        document.getElementById("memberSelect").value
    );

    if (!senderId || !recipientId) {
        toast("Please select a member first.");
        return;
    }

    const message = prompt(
        "Why would you like to connect? Write a short personal message:"
    );

    if (message === null) return;

    if (!message.trim()) {
        toast("Please enter a message.");
        return;
    }

    try {
        const result = await api("/requests", {
            method: "POST",
            body: JSON.stringify({
                sender_id: senderId,
                recipient_id: Number(recipientId),
                message: message.trim()
            })
        });

        toast(result.message || "Connection request sent!");

        await loadRequests();
        await loadDashboard();

    } catch (error) {
        console.error("Connection request error:", error);
        toast(error.message);
    }
}

async function respondToRequest(requestId, status) {
    const memberId = Number(
        document.getElementById("memberSelect").value
    );

    try {
        const result = await api(`/requests/${requestId}`, {
            method: "PATCH",
            body: JSON.stringify({
                member_id: memberId,
                status
            })
        });

        toast(result.message || "Request updated.");

        await loadRequests();
        await loadDashboard();

    } catch (error) {
        console.error(error);
        toast(error.message);
    }
}

/* =========================================================
   PROJECTS
========================================================= */

async function loadProjects() {
    const projects = await api("/collaborations");
    const grid = document.getElementById("projectGrid");

    if (!grid) return;

    if (!projects.length) {
        grid.innerHTML = `
            <div class="empty">No projects yet. Start the first one.</div>
        `;
        return;
    }

    grid.innerHTML = projects.map(project => `
        <article class="project-card">
            <div class="card-top">
                <span class="tag">
                    ${escapeHTML((project.status || "").toUpperCase())}
                </span>

                <span class="card-category">
                    ${Number(project.member_count) || 0} MEMBERS
                </span>
            </div>

            <h3>${escapeHTML(project.title)}</h3>
            <p>${escapeHTML(project.description)}</p>

            <div class="progress-line"><span></span></div>

            <div class="project-meta">
                OWNER: ${escapeHTML(project.owner_name)}<br><br>
                GOAL: ${escapeHTML(project.goal || "Not specified")}<br><br>
                UPDATES: ${Number(project.update_count) || 0}
                ${project.deadline
                    ? `<br><br>TARGET: ${escapeHTML(project.deadline)}`
                    : ""}
            </div>

            <button class="outline-btn"
                onclick="openProjectWorkspace(${Number(project.id)})">
                Open workspace ↗
            </button>

            <button class="text-btn"
                onclick="joinProject(${Number(project.id)})"
                style="margin-top:12px">
                Join this collaboration ＋
            </button>

            <button class="text-btn"
                onclick="postUpdate(${Number(project.id)})"
                style="margin-top:14px">
                Post a progress update ＋
            </button>
        </article>
    `).join("");
}

/* =========================================================
   PROJECT WORKSPACE
========================================================= */

function ensureWorkspaceModal() {
    let modal = document.getElementById("projectWorkspaceModal");
    if (modal) return modal;

    modal = document.createElement("div");
    modal.id = "projectWorkspaceModal";
    modal.className = "modal workspace-modal";

    modal.innerHTML = `
        <div class="workspace-modal-card">
            <button type="button"
                class="workspace-close"
                onclick="closeProjectWorkspace()">×</button>

            <div id="workspaceContent">
                <div class="loading">Loading workspace...</div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    modal.addEventListener("click", event => {
        if (event.target === modal) {
            closeProjectWorkspace();
        }
    });

    return modal;
}

async function openProjectWorkspace(projectId) {
    const modal = ensureWorkspaceModal();
    const content = document.getElementById("workspaceContent");

    modal.style.display = "flex";
    content.innerHTML = `
        <div class="loading">Loading workspace...</div>
    `;

    try {
        const [
            projects,
            updates,
            team,
            taskData,
            activity,
            analytics
        ] = await Promise.all([
            api("/collaborations"),
            api(`/collaborations/${projectId}/updates`),
            api(`/collaborations/${projectId}/members`),
            api(`/collaborations/${projectId}/tasks`),
            api(`/collaborations/${projectId}/activity`),
            api(`/collaborations/${projectId}/analytics`)
        ]);

        const project = projects.find(
            item => Number(item.id) === Number(projectId)
        );

        if (!project) throw new Error("Project not found.");

        const currentMember = Number(
            document.getElementById("memberSelect").value
        );

        const tasks = taskData.tasks || [];
        const progress = Math.max(
            0,
            Math.min(
                100,
                Number(analytics.progress ?? taskData.progress) || 0
            )
        );

        const filteredTasks = workspaceTaskFilter === "all"
            ? tasks
            : tasks.filter(
                task => task.status === workspaceTaskFilter
            );

        const teamHTML = team.map(member => `
            <article class="workspace-team-member">
                <div class="workspace-member-avatar">
                    ${escapeHTML(member.name.charAt(0).toUpperCase())}
                </div>

                <div>
                    <strong>${escapeHTML(member.name)}</strong>
                    <div class="workspace-muted">
                        ${escapeHTML(member.role || "Member")} ·
                        ${escapeHTML(member.skills || "No skills listed")}
                    </div>
                </div>
            </article>
        `).join("");

        const taskHTML = filteredTasks.length
            ? filteredTasks.map(task => `
                <article class="workspace-task">
                    <div class="workspace-task-heading">
                        <div>
                            <strong>${escapeHTML(task.title)}</strong>
                            <p>${escapeHTML(task.description || "No description")}</p>
                        </div>

                        <span class="workspace-task-status">
                            ${escapeHTML(
                                (task.status || "todo")
                                    .replace("_", " ")
                                    .toUpperCase()
                            )}
                        </span>
                    </div>

                    <div class="workspace-task-meta">
                        <span>Assigned: ${escapeHTML(task.assigned_name || "Unassigned")}</span>
                        <span>Due: ${escapeHTML(task.due_date || "No deadline")}</span>
                    </div>

                    <label>Update status</label>

                    <select
                        onchange="updateTaskStatus(${Number(task.id)}, this.value, ${Number(projectId)})">
                        <option value="todo" ${task.status === "todo" ? "selected" : ""}>To Do</option>
                        <option value="in_progress" ${task.status === "in_progress" ? "selected" : ""}>In Progress</option>
                        <option value="done" ${task.status === "done" ? "selected" : ""}>Done</option>
                    </select>

                    <div class="workspace-task-actions">
                        <button class="outline-btn"
                            onclick="editTask(${Number(task.id)}, ${Number(projectId)})">
                            ✎ Edit task
                        </button>

                        <button class="outline-btn"
                            onclick="deleteTask(${Number(task.id)}, ${Number(projectId)})">
                            Delete task
                        </button>
                    </div>
                </article>
            `).join("")
            : `<div class="empty">No tasks in this filter.</div>`;

        const totalTasks = Number(
            analytics.total_tasks ?? tasks.length
        );

        const completedTasks = Number(
            analytics.completed_tasks ??
            tasks.filter(task => task.status === "done").length
        );

        const todoTasks = Number(
            analytics.todo_tasks ??
            tasks.filter(task => task.status === "todo").length
        );

        const inProgressTasks = Number(
            analytics.in_progress_tasks ??
            tasks.filter(task => task.status === "in_progress").length
        );

        const teamSize = Number(
            analytics.team_size ?? team.length
        );

        const updatesCount = Number(
            analytics.updates_count ?? updates.length
        );

        const contributions =
            analytics.member_contributions || [];

        const contributionHTML = contributions.length
            ? contributions.map(person => {
                const assigned = Number(person.assigned_tasks || 0);
                const completed = Number(person.completed_tasks || 0);

                const percentage = assigned
                    ? Math.round((completed / assigned) * 100)
                    : 0;

                return `
                    <div class="workspace-contribution">
                        <div class="workspace-contribution-label">
                            <strong>${escapeHTML(person.name || "Community member")}</strong>
                            <span>${completed}/${assigned} tasks completed</span>
                        </div>

                        <div class="workspace-contribution-track">
                            <div style="width:${percentage}%"></div>
                        </div>
                    </div>
                `;
            }).join("")
            : `
                <div class="empty">
                    Contribution data will appear when tasks are assigned.
                </div>
            `;

        const activityHTML = activity.length
            ? activity.map(item => `
                <article class="workspace-timeline-item">
                    <div class="workspace-timeline-dot"></div>
                    <div>
                        <p>${escapeHTML(item.message)}</p>
                        <small>${escapeHTML(item.created_at || "Recent activity")}</small>
                    </div>
                </article>
            `).join("")
            : `<div class="empty">No recorded project activity yet.</div>`;

        const updatesHTML = updates.length
            ? updates.map(update => `
                <article class="workspace-update">
                    <strong>${escapeHTML(update.member_name || "Community member")}</strong>
                    <small>${escapeHTML(update.created_at || "")}</small>
                    <p>${escapeHTML(update.content)}</p>
                </article>
            `).join("")
            : `<div class="empty">No progress updates yet.</div>`;

        content.innerHTML = `
            <span class="eyebrow">COLLABORATION WORKSPACE</span>

            <h2 class="workspace-title">
                ${escapeHTML(project.title)}
            </h2>

            <p class="workspace-description">
                ${escapeHTML(project.description || "No description added.")}
            </p>

            <div class="workspace-overview-grid">
                <div>
                    <small>OWNER</small>
                    <strong>${escapeHTML(project.owner_name)}</strong>
                </div>

                <div>
                    <small>TEAM SIZE</small>
                    <strong>${teamSize} members</strong>
                </div>

                <div>
                    <small>PROJECT STATUS</small>
                    <strong>${escapeHTML(project.status || "Active")}</strong>
                </div>
            </div>

            <h3>Shared goal</h3>
            <p class="workspace-description">
                ${escapeHTML(project.goal || "No goal defined yet.")}
            </p>

            ${project.deadline
                ? `<p class="workspace-muted">Target date: ${escapeHTML(project.deadline)}</p>`
                : ""}

            <section class="workspace-insights">
                <span class="eyebrow">PROJECT INSIGHTS</span>
                <h3>How is the team doing?</h3>

                <div class="workspace-insight-grid">
                    <div><small>PROGRESS</small><strong>${progress}%</strong></div>
                    <div><small>COMPLETED</small><strong>${completedTasks}</strong></div>
                    <div><small>IN PROGRESS</small><strong>${inProgressTasks}</strong></div>
                    <div><small>TO DO</small><strong>${todoTasks}</strong></div>
                </div>

                <div class="workspace-progress-heading">
                    <strong>Overall completion</strong>
                    <strong>${progress}%</strong>
                </div>

                <div class="workspace-progress-track">
                    <div style="width:${progress}%"></div>
                </div>

                <p class="workspace-muted">
                    ${completedTasks} of ${totalTasks} tasks completed ·
                    ${updatesCount} progress updates · ${teamSize} team members
                </p>

                <h4>Team contributions</h4>
                ${contributionHTML}
            </section>

            <section class="workspace-section">
                <h3>Your team</h3>
                ${teamHTML || `<div class="empty">No team members found.</div>`}
            </section>

            <section class="workspace-create-task">
                <h3>＋ Create a task</h3>

                <form id="workspaceTaskForm">
                    <input name="title" type="text"
                        placeholder="Task title" maxlength="150" required>

                    <textarea name="description"
                        placeholder="Describe what needs to be done..."
                        rows="3"></textarea>

                    <label>Assign to</label>

                    <select name="assigned_to">
                        <option value="">Unassigned</option>
                        ${team.map(member => `
                            <option value="${Number(member.id)}">
                                ${escapeHTML(member.name)}
                            </option>
                        `).join("")}
                    </select>

                    <label>Due date</label>
                    <input type="date" name="due_date">

                    <button class="primary-btn" type="submit">
                        Create task ＋
                    </button>
                </form>
            </section>

            <section class="workspace-section">
                <div class="workspace-task-heading">
                    <h3>Tasks & milestones (${tasks.length})</h3>

                    <select id="workspaceTaskFilter"
                        onchange="filterWorkspaceTasks(this.value, ${Number(projectId)})">
                        <option value="all" ${workspaceTaskFilter === "all" ? "selected" : ""}>All tasks</option>
                        <option value="todo" ${workspaceTaskFilter === "todo" ? "selected" : ""}>To Do</option>
                        <option value="in_progress" ${workspaceTaskFilter === "in_progress" ? "selected" : ""}>In Progress</option>
                        <option value="done" ${workspaceTaskFilter === "done" ? "selected" : ""}>Done</option>
                    </select>
                </div>

                ${taskHTML}
            </section>

            <div class="workspace-actions">
                <button class="outline-btn"
                    onclick="postUpdate(${Number(projectId)});closeProjectWorkspace();">
                    ＋ Post progress update
                </button>

                <button class="outline-btn"
                    onclick="joinProject(${Number(projectId)})">
                    Join project
                </button>
            </div>

            <section class="workspace-section">
                <span class="eyebrow">PROJECT HISTORY</span>
                <h3>Activity timeline</h3>
                ${activityHTML}
            </section>

            <section class="workspace-section">
                <h3>Progress updates</h3>
                ${updatesHTML}
            </section>
        `;

        document.getElementById("workspaceTaskForm")
            .addEventListener("submit", async event => {
                event.preventDefault();

                const formData = new FormData(event.target);
                const assignedValue = formData.get("assigned_to");

                try {
                    await api(
                        `/collaborations/${projectId}/tasks`,
                        {
                            method: "POST",
                            body: JSON.stringify({
                                title: formData.get("title"),
                                description: formData.get("description"),
                                assigned_to: assignedValue
                                    ? Number(assignedValue)
                                    : null,
                                created_by: currentMember,
                                due_date: formData.get("due_date")
                            })
                        }
                    );

                    toast("Task created successfully!");

                    await openProjectWorkspace(projectId);
                    await loadProjects();
                    await loadDashboard();

                } catch (error) {
                    toast(error.message);
                }
            });

    } catch (error) {
        console.error("Workspace error:", error);

        content.innerHTML = `
            <div class="empty">${escapeHTML(error.message)}</div>
        `;
    }
}

/* =========================================================
   TASK FILTERS + TASK ACTIONS
========================================================= */

function filterWorkspaceTasks(filter, projectId) {
    workspaceTaskFilter = filter;
    openProjectWorkspace(projectId);
}

async function editTask(taskId, projectId) {
    try {
        const taskData = await api(
            `/collaborations/${projectId}/tasks`
        );

        const task = taskData.tasks.find(
            item => Number(item.id) === Number(taskId)
        );

        if (!task) throw new Error("Task not found.");

        const title = prompt("Edit task title:", task.title);
        if (title === null) return;

        if (!title.trim()) {
            toast("Task title cannot be empty.");
            return;
        }

        const description = prompt(
            "Edit task description:",
            task.description || ""
        );

        if (description === null) return;

        const team = await api(
            `/collaborations/${projectId}/members`
        );

        const assigneeList = team.map(member =>
            `${member.id} = ${member.name}`
        ).join("\n");

        const assignedTo = prompt(
            `Enter assignee member ID, or leave blank for unassigned:\n\n${assigneeList}`,
            task.assigned_to || ""
        );

        if (assignedTo === null) return;

        const assigneeId = assignedTo.trim()
            ? Number(assignedTo)
            : null;

        if (
            assignedTo.trim() &&
            !Number.isInteger(assigneeId)
        ) {
            toast("Please enter a valid member ID.");
            return;
        }

        const dueDate = prompt(
            "Edit deadline (YYYY-MM-DD), or leave blank:",
            task.due_date || ""
        );

        if (dueDate === null) return;

        const memberId = Number(
            document.getElementById("memberSelect").value
        );

        await api(`/tasks/${taskId}`, {
            method: "PATCH",
            body: JSON.stringify({
                member_id: memberId,
                title: title.trim(),
                description: description.trim(),
                assigned_to: assigneeId,
                due_date: dueDate.trim()
            })
        });

        toast("Task updated successfully!");

        await openProjectWorkspace(projectId);
        await loadProjects();
        await loadDashboard();

    } catch (error) {
        toast(error.message);
    }
}

async function deleteTask(taskId, projectId) {
    const confirmed = confirm(
        "Are you sure you want to delete this task? This cannot be undone."
    );

    if (!confirmed) return;

    const memberId = Number(
        document.getElementById("memberSelect").value
    );

    try {
        await api(`/tasks/${taskId}`, {
            method: "DELETE",
            body: JSON.stringify({
                member_id: memberId
            })
        });

        toast("Task deleted successfully!");

        await openProjectWorkspace(projectId);
        await loadProjects();
        await loadDashboard();

    } catch (error) {
        toast(error.message);
    }
}

async function updateTaskStatus(taskId, status, projectId) {
    const memberId = Number(
        document.getElementById("memberSelect").value
    );

    try {
        await api(`/tasks/${taskId}`, {
            method: "PATCH",
            body: JSON.stringify({
                member_id: memberId,
                status
            })
        });

        toast("Task status updated!");

        await openProjectWorkspace(projectId);
        await loadProjects();
        await loadDashboard();

    } catch (error) {
        toast(error.message);
        await openProjectWorkspace(projectId);
    }
}

function closeProjectWorkspace() {
    const modal = document.getElementById(
        "projectWorkspaceModal"
    );

    if (modal) modal.style.display = "none";
}

/* =========================================================
   JOIN PROJECT
========================================================= */

async function joinProject(projectId) {
    const memberId = Number(
        document.getElementById("memberSelect").value
    );

    try {
        const result = await api(
            `/collaborations/${projectId}/join`,
            {
                method: "POST",
                body: JSON.stringify({
                    member_id: memberId
                })
            }
        );

        toast(result.message || "Joined project!");
        await refresh();

    } catch (error) {
        toast(error.message);
    }
}

/* =========================================================
   PROGRESS UPDATES
========================================================= */

async function postUpdate(projectId) {
    const memberId = Number(
        document.getElementById("memberSelect").value
    );

    const content = prompt("What progress have you made?");

    if (content === null || !content.trim()) return;

    try {
        const result = await api(
            `/collaborations/${projectId}/updates`,
            {
                method: "POST",
                body: JSON.stringify({
                    member_id: memberId,
                    content: content.trim()
                })
            }
        );

        toast(result.message || "Progress update posted!");
        await refresh();

    } catch (error) {
        toast(error.message);
    }
}

/* =========================================================
   REFRESH
========================================================= */

async function refresh() {
    try {
        await Promise.all([
            loadDashboard(),
            loadSignals(
                document.querySelector(
                    '.filter-row .filter.active'
                )?.dataset.filter || "all"
            ),
            loadProjects(),
            loadRequests()
        ]);

    } catch (error) {
        console.error("COLLIDE refresh error:", error);
        toast(error.message);
    }
}

/* =========================================================
   INITIALIZATION
========================================================= */

document.addEventListener("DOMContentLoaded", async () => {

    // Expose functions used by HTML inline handlers.
    window.openModal = openModal;
    window.closeModal = closeModal;
    window.scrollToSection = scrollToSection;
    window.loadMatches = loadMatches;
    window.loadRequests = loadRequests;
    window.loadDashboard = loadDashboard;
    window.sendConnectionRequest = sendConnectionRequest;
    window.respondToRequest = respondToRequest;
    window.startCollaboration = startCollaboration;
    window.joinProject = joinProject;
    window.openProjectWorkspace = openProjectWorkspace;
    window.closeProjectWorkspace = closeProjectWorkspace;
    window.postUpdate = postUpdate;
    window.editTask = editTask;
    window.deleteTask = deleteTask;
    window.filterWorkspaceTasks = filterWorkspaceTasks;
    window.updateTaskStatus = updateTaskStatus;

    // Signal form
    const signalForm = document.getElementById("signalForm");

    signalForm?.addEventListener("submit", async event => {
        event.preventDefault();

        const data = Object.fromEntries(
            new FormData(event.target)
        );

        data.member_id = Number(data.member_id);

        try {
            const result = await api("/signals", {
                method: "POST",
                body: JSON.stringify(data)
            });

            toast(result.message || "Signal posted!");

            event.target.reset();
            closeModal("signalModal");

            await refresh();

        } catch (error) {
            toast(error.message);
        }
    });

    // Project form
    const projectForm = document.getElementById("projectForm");

    projectForm?.addEventListener("submit", async event => {
        event.preventDefault();

        const data = Object.fromEntries(
            new FormData(event.target)
        );

        data.owner_id = Number(data.owner_id);

        try {
            const result = await api("/collaborations", {
                method: "POST",
                body: JSON.stringify(data)
            });

            toast(result.message || "Project created!");

            event.target.reset();
            closeModal("projectModal");

            await refresh();

        } catch (error) {
            toast(error.message);
        }
    });

    // SIGNAL FILTERS ONLY
    // Event filters are handled separately by events.js.
    document.querySelectorAll(".filter-row .filter")
        .forEach(button => {
            button.addEventListener("click", () => {
                document.querySelectorAll(
                    ".filter-row .filter"
                ).forEach(item => {
                    item.classList.remove("active");
                });

                button.classList.add("active");
                renderSignals(button.dataset.filter);
            });
        });

    // Member selector
    document.getElementById("memberSelect")
        ?.addEventListener("change", async () => {
            await loadMatches();
            await loadRequests();
        });

    // Dashboard refresh
    const refreshButton = document.getElementById(
        "refreshDashboard"
    );

    refreshButton?.addEventListener("click", async () => {
        refreshButton.disabled = true;
        refreshButton.textContent = "Refreshing...";

        try {
            await loadDashboard();
            toast("Dashboard refreshed.");
        } catch (error) {
            toast(error.message);
        } finally {
            refreshButton.disabled = false;
            refreshButton.textContent = "↻ Refresh data";
        }
    });

    // Close standard modals on backdrop click.
    document.querySelectorAll(".modal").forEach(modal => {
        modal.addEventListener("click", event => {
            if (event.target === modal) {
                modal.classList.remove("open");
            }
        });
    });

    // Initialize application
    try {
        await loadMembers();
        await refresh();
        await loadMatches();

        console.log("COLLIDE initialized successfully.");

    } catch (error) {
        console.error("COLLIDE initialization error:", error);
        toast("Could not connect to the server. Check Flask.");
    }
});
