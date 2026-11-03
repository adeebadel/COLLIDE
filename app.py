
from flask import Flask, jsonify, request, render_template
from database import get_db, init_db
from datetime import date

app = Flask(__name__)
init_db()


# ==========================================
# HELPER: ACTIVITY LOGGING
# ==========================================

def log_activity(db, project_id, member_id, action_type, message, task_id=None):
    db.execute("""
        INSERT INTO activity_logs
        (collaboration_id, member_id, task_id, action_type, message)
        VALUES (?, ?, ?, ?, ?)
    """, (project_id, member_id, task_id, action_type, message))


def valid_member(db, member_id):
    if not member_id:
        return None

    return db.execute(
        "SELECT id, name FROM members WHERE id = ?",
        (member_id,)
    ).fetchone()


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "running",
        "app": "COLLIDE"
    })


# ==========================================
# COMMUNITY DASHBOARD & ANALYTICS
# ==========================================

@app.route("/api/dashboard")
def dashboard():

    with get_db() as db:

        # --------------------------------------
        # BASIC COMMUNITY COUNTS
        # --------------------------------------

        total_members = db.execute("""
            SELECT COUNT(*) FROM members
        """).fetchone()[0]

        open_signals = db.execute("""
            SELECT COUNT(*) FROM signals
            WHERE status = 'open'
        """).fetchone()[0]

        active_projects = db.execute("""
            SELECT COUNT(*) FROM collaborations
            WHERE status = 'active'
        """).fetchone()[0]

        completed_projects = db.execute("""
            SELECT COUNT(*) FROM collaborations
            WHERE status = 'completed'
        """).fetchone()[0]

        total_updates = db.execute("""
            SELECT COUNT(*) FROM updates
        """).fetchone()[0]

        accepted_connections = db.execute("""
            SELECT COUNT(*) FROM connection_requests
            WHERE status = 'accepted'
        """).fetchone()[0]

        pending_connections = db.execute("""
            SELECT COUNT(*) FROM connection_requests
            WHERE status = 'pending'
        """).fetchone()[0]

        # --------------------------------------
        # MEMBER ACTIVITY
        # --------------------------------------

        activity_query = """
            SELECT member_id, activity_date
            FROM (
                SELECT member_id, date(created_at) AS activity_date
                FROM signals

                UNION

                SELECT sender_id AS member_id, date(created_at)
                FROM connection_requests

                UNION

                SELECT recipient_id AS member_id, date(created_at)
                FROM connection_requests

                UNION

                SELECT member_id, date(created_at)
                FROM updates

                UNION

                SELECT member_id, date(updated_at)
                FROM event_attendees

                UNION

                SELECT member_id, date(created_at)
                FROM activity_logs
                WHERE member_id IS NOT NULL
            )
            WHERE member_id IS NOT NULL
        """

        recent_activity_rows = db.execute(
            activity_query + """
                AND activity_date >= date('now', '-30 days')
            """
        ).fetchall()

        previous_activity_rows = db.execute(
            activity_query + """
                AND activity_date >= date('now', '-60 days')
                AND activity_date < date('now', '-30 days')
            """
        ).fetchall()

        recent_member_ids = {
            row["member_id"] for row in recent_activity_rows
        }

        previous_member_ids = {
            row["member_id"] for row in previous_activity_rows
        }

        active_members = len(recent_member_ids)

        returning_members = len(
            recent_member_ids & previous_member_ids
        )

        inactive_members = max(
            total_members - active_members, 0
        )

        # --------------------------------------
        # EVENT ANALYTICS
        # --------------------------------------

        upcoming_events = db.execute("""
            SELECT COUNT(*) FROM events
            WHERE status = 'upcoming'
            AND event_date >= ?
        """, (date.today().isoformat(),)).fetchone()[0]

        total_events = db.execute("""
            SELECT COUNT(*) FROM events
        """).fetchone()[0]

        event_stats = db.execute("""
            SELECT
                SUM(
                    CASE
                        WHEN attendance_status IN ('registered', 'attended')
                        THEN 1 ELSE 0
                    END
                ) AS registrations,

                SUM(
                    CASE
                        WHEN attendance_status = 'attended'
                        THEN 1 ELSE 0
                    END
                ) AS attended,

                SUM(
                    CASE
                        WHEN attendance_status = 'cancelled'
                        THEN 1 ELSE 0
                    END
                ) AS cancelled,

                AVG(rating) AS average_rating

            FROM event_attendees
        """).fetchone()

        registrations = event_stats["registrations"] or 0
        attended = event_stats["attended"] or 0
        cancelled = event_stats["cancelled"] or 0

        attendance_rate = (
            round((attended / registrations) * 100)
            if registrations else 0
        )

        average_event_rating = (
            round(event_stats["average_rating"], 1)
            if event_stats["average_rating"] is not None
            else None
        )

        # --------------------------------------
        # COLLABORATION ANALYTICS
        # --------------------------------------

        multi_member_projects = db.execute("""
            SELECT COUNT(*)
            FROM collaborations c
            WHERE c.status = 'active'
            AND (
                SELECT COUNT(*)
                FROM collaboration_members cm
                WHERE cm.collaboration_id = c.id
            ) >= 2
        """).fetchone()[0]

        total_project_memberships = db.execute("""
            SELECT COUNT(*) FROM collaboration_members
        """).fetchone()[0]

        # --------------------------------------
        # TASK ANALYTICS
        # --------------------------------------

        task_stats = db.execute("""
            SELECT
                COUNT(*) AS total_tasks,

                SUM(
                    CASE WHEN status = 'done'
                    THEN 1 ELSE 0 END
                ) AS completed_tasks,

                SUM(
                    CASE WHEN status = 'in_progress'
                    THEN 1 ELSE 0 END
                ) AS in_progress_tasks,

                SUM(
                    CASE WHEN status = 'todo'
                    THEN 1 ELSE 0 END
                ) AS pending_tasks

            FROM tasks
        """).fetchone()

        total_tasks = task_stats["total_tasks"] or 0
        completed_tasks = task_stats["completed_tasks"] or 0
        in_progress_tasks = task_stats["in_progress_tasks"] or 0
        pending_tasks = task_stats["pending_tasks"] or 0

        task_completion_rate = (
            round((completed_tasks / total_tasks) * 100)
            if total_tasks else 0
        )

        # --------------------------------------
        # COMMUNITY HEALTH INDICATOR
        # --------------------------------------

        # Prototype scoring model:
        # Active members: 35%
        # Event attendance: 25%
        # Multi-member projects: 20%
        # Task completion: 20%

        member_score = (
            min(active_members / total_members, 1) * 35
            if total_members else 0
        )

        event_score = attendance_rate * 0.25

        project_score = (
            min(multi_member_projects / active_projects, 1) * 20
            if active_projects else 0
        )

        task_score = task_completion_rate * 0.20

        community_health = round(
            member_score
            + event_score
            + project_score
            + task_score
        )

        # --------------------------------------
        # RECENT COMMUNITY ACTIVITY
        # --------------------------------------

        recent_activity = db.execute("""
            SELECT
                a.id,
                a.action_type,
                a.message,
                a.created_at,
                m.name AS member_name,
                c.title AS project_title

            FROM activity_logs a

            LEFT JOIN members m
                ON a.member_id = m.id

            LEFT JOIN collaborations c
                ON a.collaboration_id = c.id

            ORDER BY a.created_at DESC, a.id DESC
            LIMIT 8
        """).fetchall()

    return jsonify({

        # Original dashboard fields
        "members": total_members,
        "open_signals": open_signals,
        "active_collaborations": active_projects,
        "project_updates": total_updates,
        "accepted_connections": accepted_connections,
        "upcoming_events": upcoming_events,

        # Community overview
        "community": {
            "health_score": community_health,
            "active_members_30_days": active_members,
            "returning_members_30_days": returning_members,
            "inactive_members": inactive_members,
            "total_members": total_members
        },

        # Engagement
        "engagement": {
            "accepted_connections": accepted_connections,
            "pending_connections": pending_connections,
            "total_project_memberships": total_project_memberships
        },

        # Events
        "events": {
            "total_events": total_events,
            "upcoming_events": upcoming_events,
            "registrations": registrations,
            "attended": attended,
            "cancelled": cancelled,
            "attendance_rate": attendance_rate,
            "average_rating": average_event_rating
        },

        # Projects
        "projects": {
            "active": active_projects,
            "completed": completed_projects,
            "multi_member_projects": multi_member_projects,
            "updates": total_updates
        },

        # Tasks
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "in_progress": in_progress_tasks,
            "pending": pending_tasks,
            "completion_rate": task_completion_rate
        },

        # Activity feed
        "recent_activity": [
            dict(row) for row in recent_activity
        ]
    })


# ==========================================
# MEMBERS
# ==========================================

@app.route("/api/members", methods=["GET", "POST"])
def members():

    with get_db() as db:

        if request.method == "POST":

            data = request.get_json(silent=True) or {}
            name = str(data.get("name", "")).strip()

            if not name:
                return jsonify({
                    "error": "Name is required"
                }), 400

            db.execute("""
                INSERT INTO members (name, bio, skills, interests)
                VALUES (?, ?, ?, ?)
            """, (
                name,
                str(data.get("bio", "")).strip(),
                str(data.get("skills", "")).strip(),
                str(data.get("interests", "")).strip()
            ))

            member_id = db.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            return jsonify({
                "message": "Welcome to COLLIDE!",
                "member_id": member_id
            }), 201

        rows = db.execute("""
            SELECT id, name, bio, skills, interests
            FROM members
            ORDER BY id DESC
        """).fetchall()

    return jsonify([dict(row) for row in rows])


# ==========================================
# SIGNALS
# ==========================================

@app.route("/api/signals", methods=["GET", "POST"])
def signals():

    with get_db() as db:

        if request.method == "POST":

            data = request.get_json(silent=True) or {}

            member_id = data.get("member_id")
            title = str(data.get("title", "")).strip()
            description = str(data.get("description", "")).strip()
            signal_type = str(data.get("signal_type", "")).strip().lower()
            category = str(data.get("category", "General")).strip()

            if not member_id or not title or not description:
                return jsonify({
                    "error": "Member, title and description are required"
                }), 400

            if signal_type not in ("need", "offer", "building"):
                return jsonify({
                    "error": "Type must be need, offer or building"
                }), 400

            if not valid_member(db, member_id):
                return jsonify({
                    "error": "Member not found"
                }), 404

            db.execute("""
                INSERT INTO signals
                (member_id, title, description, signal_type, category)
                VALUES (?, ?, ?, ?, ?)
            """, (
                member_id, title, description,
                signal_type, category
            ))

            signal_id = db.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            return jsonify({
                "message": "Your signal is live!",
                "signal_id": signal_id
            }), 201

        rows = db.execute("""
            SELECT
                s.id,
                s.title,
                s.description,
                s.signal_type,
                s.category,
                s.status,
                s.created_at,
                m.id AS member_id,
                m.name AS member_name,
                m.skills AS member_skills

            FROM signals s
            JOIN members m ON s.member_id = m.id

            WHERE s.status = 'open'

            ORDER BY s.created_at DESC, s.id DESC
        """).fetchall()

    return jsonify([dict(row) for row in rows])


# ==========================================
# MATCHING ENGINE
# ==========================================

def words(value):
    return {
        word.strip(".,!?;:()[]{}").lower()
        for word in str(value or "").replace(",", " ").split()
        if len(word.strip(".,!?;:()[]{}")) > 2
    }


@app.route("/api/matches/<int:member_id>")
def matches(member_id):

    with get_db() as db:

        current = db.execute(
            "SELECT * FROM members WHERE id = ?",
            (member_id,)
        ).fetchone()

        if not current:
            return jsonify({
                "error": "Member not found"
            }), 404

        current_skills = words(current["skills"])
        current_interests = words(current["interests"])

        candidates = db.execute("""
            SELECT id, name, bio, skills, interests
            FROM members
            WHERE id != ?
        """, (member_id,)).fetchall()

        results = []

        for candidate in candidates:

            candidate_skills = words(candidate["skills"])
            candidate_interests = words(candidate["interests"])

            shared_interests = current_interests & candidate_interests
            complementary_skills = current_skills & candidate_interests
            reverse_complement = candidate_skills & current_interests

            score = (
                len(shared_interests) * 2
                + len(complementary_skills) * 3
                + len(reverse_complement) * 3
            )

            reasons = []

            if shared_interests:
                reasons.append(
                    "Shared interests: "
                    + ", ".join(sorted(shared_interests))
                )

            if complementary_skills:
                reasons.append(
                    "Your skills connect with their interests: "
                    + ", ".join(sorted(complementary_skills))
                )

            if reverse_complement:
                reasons.append(
                    "Their skills connect with your interests: "
                    + ", ".join(sorted(reverse_complement))
                )

            results.append({
                "member": dict(candidate),
                "score": score,
                "reasons": reasons or [
                    "Potential connection worth exploring"
                ]
            })

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return jsonify(results)


# ==========================================
# COLLABORATIONS
# ==========================================

@app.route("/api/collaborations", methods=["GET", "POST"])
def collaborations():

    with get_db() as db:

        if request.method == "POST":

            data = request.get_json(silent=True) or {}

            title = str(data.get("title", "")).strip()
            owner_id = data.get("owner_id")

            if not title or not owner_id:
                return jsonify({
                    "error": "Project title and owner are required"
                }), 400

            owner = valid_member(db, owner_id)

            if not owner:
                return jsonify({
                    "error": "Owner not found"
                }), 404

            db.execute("""
                INSERT INTO collaborations
                (title, description, goal, owner_id, deadline)
                VALUES (?, ?, ?, ?, ?)
            """, (
                title,
                str(data.get("description", "")).strip(),
                str(data.get("goal", "")).strip(),
                owner_id,
                str(data.get("deadline", "")).strip()
            ))

            project_id = db.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            db.execute("""
                INSERT INTO collaboration_members
                (collaboration_id, member_id)
                VALUES (?, ?)
            """, (project_id, owner_id))

            log_activity(
                db,
                project_id,
                owner_id,
                "project_created",
                f"{owner['name']} created the project."
            )

            return jsonify({
                "message": "Collaboration created!",
                "collaboration_id": project_id
            }), 201

        rows = db.execute("""
            SELECT
                c.*,
                m.name AS owner_name,

                (
                    SELECT COUNT(*)
                    FROM collaboration_members cm
                    WHERE cm.collaboration_id = c.id
                ) AS member_count,

                (
                    SELECT COUNT(*)
                    FROM updates u
                    WHERE u.collaboration_id = c.id
                ) AS update_count

            FROM collaborations c
            JOIN members m ON c.owner_id = m.id

            ORDER BY c.created_at DESC
        """).fetchall()

    return jsonify([dict(row) for row in rows])


# ==========================================
# JOIN COLLABORATION
# ==========================================

@app.route("/api/collaborations/<int:project_id>/join", methods=["POST"])
def join_collaboration(project_id):

    data = request.get_json(silent=True) or {}
    member_id = data.get("member_id")

    if not member_id:
        return jsonify({
            "error": "Member ID is required"
        }), 400

    with get_db() as db:

        project = db.execute("""
            SELECT id FROM collaborations
            WHERE id = ? AND status = 'active'
        """, (project_id,)).fetchone()

        member = valid_member(db, member_id)

        if not project or not member:
            return jsonify({
                "error": "Project or member not found"
            }), 404

        existing = db.execute("""
            SELECT 1 FROM collaboration_members
            WHERE collaboration_id = ? AND member_id = ?
        """, (project_id, member_id)).fetchone()

        if not existing:

            db.execute("""
                INSERT INTO collaboration_members
                (collaboration_id, member_id)
                VALUES (?, ?)
            """, (project_id, member_id))

            log_activity(
                db,
                project_id,
                member_id,
                "member_joined",
                f"{member['name']} joined the project."
            )

    return jsonify({
        "message": "You joined the collaboration!"
    })


# ==========================================
# PROJECT UPDATES
# ==========================================

@app.route(
    "/api/collaborations/<int:project_id>/updates",
    methods=["GET", "POST"]
)
def project_updates(project_id):

    with get_db() as db:

        project = db.execute(
            "SELECT id FROM collaborations WHERE id = ?",
            (project_id,)
        ).fetchone()

        if not project:
            return jsonify({
                "error": "Project not found"
            }), 404

        if request.method == "POST":

            data = request.get_json(silent=True) or {}

            member_id = data.get("member_id")
            content = str(data.get("content", "")).strip()

            if not member_id or not content:
                return jsonify({
                    "error": "Member and update content are required"
                }), 400

            member = valid_member(db, member_id)

            if not member:
                return jsonify({
                    "error": "Member not found"
                }), 404

            is_member = db.execute("""
                SELECT 1 FROM collaboration_members
                WHERE collaboration_id = ? AND member_id = ?
            """, (project_id, member_id)).fetchone()

            if not is_member:
                return jsonify({
                    "error": "Join the collaboration before posting updates"
                }), 403

            db.execute("""
                INSERT INTO updates (collaboration_id, member_id, content)
                VALUES (?, ?, ?)
            """, (project_id, member_id, content))

            log_activity(
                db,
                project_id,
                member_id,
                "update_posted",
                f"{member['name']} posted a project update."
            )

            return jsonify({
                "message": "Update posted!"
            }), 201

        rows = db.execute("""
            SELECT u.*, m.name AS member_name
            FROM updates u
            JOIN members m ON u.member_id = m.id
            WHERE u.collaboration_id = ?
            ORDER BY u.created_at DESC
        """, (project_id,)).fetchall()

    return jsonify([dict(row) for row in rows])


# ==========================================
# CONNECTION REQUESTS
# ==========================================

@app.route("/api/requests", methods=["GET", "POST"])
def connection_requests():

    with get_db() as db:

        if request.method == "POST":

            data = request.get_json(silent=True) or {}

            sender_id = data.get("sender_id")
            recipient_id = data.get("recipient_id")
            message = str(data.get("message", "")).strip()

            if not sender_id or not recipient_id or not message:
                return jsonify({
                    "error": "Sender, recipient and message are required"
                }), 400

            if sender_id == recipient_id:
                return jsonify({
                    "error": "You cannot request yourself"
                }), 400

            if len(message) > 1000:
                return jsonify({
                    "error": "Message is too long"
                }), 400

            sender = valid_member(db, sender_id)
            recipient = valid_member(db, recipient_id)

            if not sender or not recipient:
                return jsonify({
                    "error": "Member not found"
                }), 404

            existing = db.execute("""
                SELECT id FROM connection_requests
                WHERE sender_id = ?
                AND recipient_id = ?
                AND status = 'pending'
            """, (sender_id, recipient_id)).fetchone()

            if existing:
                return jsonify({
                    "error": "You already have a pending request"
                }), 409

            db.execute("""
                INSERT INTO connection_requests
                (sender_id, recipient_id, message)
                VALUES (?, ?, ?)
            """, (sender_id, recipient_id, message))

            return jsonify({
                "message": "Collaboration request sent!"
            }), 201

        member_id = request.args.get("member_id", type=int)

        if not member_id:
            return jsonify({
                "error": "Member ID is required"
            }), 400

        rows = db.execute("""
            SELECT
                r.*,
                sender.name AS sender_name,
                recipient.name AS recipient_name

            FROM connection_requests r

            JOIN members sender
                ON r.sender_id = sender.id

            JOIN members recipient
                ON r.recipient_id = recipient.id

            WHERE r.sender_id = ? OR r.recipient_id = ?

            ORDER BY r.created_at DESC
        """, (member_id, member_id)).fetchall()

    return jsonify([dict(row) for row in rows])


@app.route("/api/requests/<int:request_id>", methods=["PATCH"])
def update_connection_request(request_id):

    data = request.get_json(silent=True) or {}

    member_id = data.get("member_id")
    status = str(data.get("status", "")).lower()

    if not member_id or status not in ("accepted", "declined"):
        return jsonify({
            "error": "Valid member ID and status are required"
        }), 400

    with get_db() as db:

        connection = db.execute("""
            SELECT * FROM connection_requests
            WHERE id = ?
        """, (request_id,)).fetchone()

        if not connection:
            return jsonify({
                "error": "Request not found"
            }), 404

        if connection["recipient_id"] != member_id:
            return jsonify({
                "error": "Only the recipient can respond"
            }), 403

        if connection["status"] != "pending":
            return jsonify({
                "error": "This request has already been answered"
            }), 409

        db.execute("""
            UPDATE connection_requests
            SET status = ?
            WHERE id = ?
        """, (status, request_id))

    return jsonify({
        "message": f"Request {status} successfully!"
    })


# ==========================================
# PROJECT TEAM
# ==========================================

@app.route("/api/collaborations/<int:project_id>/members")
def collaboration_team(project_id):

    with get_db() as db:

        project = db.execute(
            "SELECT id FROM collaborations WHERE id = ?",
            (project_id,)
        ).fetchone()

        if not project:
            return jsonify({
                "error": "Project not found"
            }), 404

        rows = db.execute("""
            SELECT
                m.id,
                m.name,
                m.bio,
                m.skills,
                m.interests,

                CASE
                    WHEN m.id = c.owner_id THEN 'Owner'
                    ELSE 'Collaborator'
                END AS role

            FROM collaboration_members cm

            JOIN members m
                ON cm.member_id = m.id

            JOIN collaborations c
                ON cm.collaboration_id = c.id

            WHERE cm.collaboration_id = ?

            ORDER BY
                CASE WHEN m.id = c.owner_id THEN 0 ELSE 1 END,
                m.name ASC
        """, (project_id,)).fetchall()

    return jsonify([dict(row) for row in rows])


# ==========================================
# PROJECT TASKS
# ==========================================

@app.route(
    "/api/collaborations/<int:project_id>/tasks",
    methods=["GET", "POST"]
)
def project_tasks(project_id):

    with get_db() as db:

        project = db.execute(
            "SELECT id FROM collaborations WHERE id = ?",
            (project_id,)
        ).fetchone()

        if not project:
            return jsonify({
                "error": "Project not found"
            }), 404

        if request.method == "POST":

            data = request.get_json(silent=True) or {}

            title = str(data.get("title", "")).strip()
            description = str(data.get("description", "")).strip()
            created_by = data.get("created_by")
            assigned_to = data.get("assigned_to")
            due_date = str(data.get("due_date", "")).strip()

            if not title or not created_by:
                return jsonify({
                    "error": "Task title and creator are required"
                }), 400

            if len(title) > 150:
                return jsonify({
                    "error": "Task title must be under 150 characters"
                }), 400

            creator = valid_member(db, created_by)

            if not creator:
                return jsonify({
                    "error": "Creator not found"
                }), 404

            creator_is_member = db.execute("""
                SELECT 1 FROM collaboration_members
                WHERE collaboration_id = ? AND member_id = ?
            """, (project_id, created_by)).fetchone()

            if not creator_is_member:
                return jsonify({
                    "error": "Join the project before creating tasks"
                }), 403

            if assigned_to is not None:

                assignee_is_member = db.execute("""
                    SELECT 1 FROM collaboration_members
                    WHERE collaboration_id = ? AND member_id = ?
                """, (project_id, assigned_to)).fetchone()

                if not assignee_is_member:
                    return jsonify({
                        "error": "Assigned member must belong to this project"
                    }), 400

            db.execute("""
                INSERT INTO tasks (
                    collaboration_id,
                    title,
                    description,
                    assigned_to,
                    created_by,
                    due_date
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                title,
                description,
                assigned_to,
                created_by,
                due_date
            ))

            task_id = db.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            log_activity(
                db,
                project_id,
                created_by,
                "task_created",
                f"{creator['name']} created task: {title}",
                task_id
            )

            return jsonify({
                "message": "Task created successfully!",
                "task_id": task_id
            }), 201

        rows = db.execute("""
            SELECT
                t.*,
                assigned.name AS assigned_name,
                creator.name AS creator_name

            FROM tasks t

            LEFT JOIN members assigned
                ON t.assigned_to = assigned.id

            JOIN members creator
                ON t.created_by = creator.id

            WHERE t.collaboration_id = ?

            ORDER BY
                CASE t.status
                    WHEN 'in_progress' THEN 1
                    WHEN 'todo' THEN 2
                    WHEN 'done' THEN 3
                END,
                t.created_at DESC
        """, (project_id,)).fetchall()

        total = len(rows)

        completed = sum(
            1 for row in rows
            if row["status"] == "done"
        )

    return jsonify({
        "tasks": [dict(row) for row in rows],
        "total_tasks": total,
        "completed_tasks": completed,
        "progress": round((completed / total) * 100) if total else 0
    })


# ==========================================
# UPDATE TASK
# ==========================================

@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def update_task(task_id):

    data = request.get_json(silent=True) or {}
    member_id = data.get("member_id")

    if not member_id:
        return jsonify({
            "error": "Member ID is required"
        }), 400

    allowed_statuses = ("todo", "in_progress", "done")

    with get_db() as db:

        task = db.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()

        if not task:
            return jsonify({
                "error": "Task not found"
            }), 404

        is_member = db.execute("""
            SELECT 1 FROM collaboration_members
            WHERE collaboration_id = ? AND member_id = ?
        """, (task["collaboration_id"], member_id)).fetchone()

        if not is_member:
            return jsonify({
                "error": "You must belong to this project to update tasks"
            }), 403

        updates = []
        values = []
        activity_changes = []

        if "title" in data:

            title = str(data.get("title", "")).strip()

            if not title or len(title) > 150:
                return jsonify({
                    "error": "Title is required and must be under 150 characters"
                }), 400

            updates.append("title = ?")
            values.append(title)
            activity_changes.append("title")

        if "description" in data:

            updates.append("description = ?")
            values.append(
                str(data.get("description") or "").strip()
            )

            activity_changes.append("description")

        if "status" in data:

            status = str(data.get("status", "")).lower()

            if status not in allowed_statuses:
                return jsonify({
                    "error": "Status must be todo, in_progress or done"
                }), 400

            if status != task["status"]:
                activity_changes.append(
                    f"status changed from {task['status']} to {status}"
                )

            updates.append("status = ?")
            values.append(status)

        if "assigned_to" in data:

            assigned_to = data.get("assigned_to")

            if assigned_to is not None:

                assignee_is_member = db.execute("""
                    SELECT 1 FROM collaboration_members
                    WHERE collaboration_id = ? AND member_id = ?
                """, (
                    task["collaboration_id"],
                    assigned_to
                )).fetchone()

                if not assignee_is_member:
                    return jsonify({
                        "error": "Assigned member must belong to this project"
                    }), 400

            updates.append("assigned_to = ?")
            values.append(assigned_to)
            activity_changes.append("assignee changed")

        if "due_date" in data:

            updates.append("due_date = ?")
            values.append(
                str(data.get("due_date") or "").strip()
            )

            activity_changes.append("due date changed")

        if not updates:
            return jsonify({
                "error": "No valid task changes provided"
            }), 400

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(task_id)

        db.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
            values
        )

        member = valid_member(db, member_id)

        log_activity(
            db,
            task["collaboration_id"],
            member_id,
            "task_updated",
            f"{member['name']} updated task: {', '.join(activity_changes)}",
            task_id
        )

    return jsonify({
        "message": "Task updated successfully!"
    })


# ==========================================
# DELETE TASK
# ==========================================

@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):

    data = request.get_json(silent=True) or {}
    member_id = data.get("member_id")

    if not member_id:
        return jsonify({
            "error": "Member ID is required"
        }), 400

    with get_db() as db:

        task = db.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()

        if not task:
            return jsonify({
                "error": "Task not found"
            }), 404

        is_owner = db.execute("""
            SELECT 1 FROM collaborations
            WHERE id = ? AND owner_id = ?
        """, (
            task["collaboration_id"],
            member_id
        )).fetchone()

        if not is_owner:
            return jsonify({
                "error": "Only the project owner can delete tasks"
            }), 403

        member = valid_member(db, member_id)

        log_activity(
            db,
            task["collaboration_id"],
            member_id,
            "task_deleted",
            f"{member['name']} deleted task: {task['title']}"
        )

        db.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )

    return jsonify({
        "message": "Task deleted successfully!"
    })


# ==========================================
# PROJECT ACTIVITY FEED
# ==========================================

@app.route("/api/collaborations/<int:project_id>/activity")
def project_activity(project_id):

    with get_db() as db:

        project = db.execute(
            "SELECT id FROM collaborations WHERE id = ?",
            (project_id,)
        ).fetchone()

        if not project:
            return jsonify({
                "error": "Project not found"
            }), 404

        rows = db.execute("""
            SELECT
                a.id,
                a.action_type,
                a.message,
                a.created_at,
                a.task_id,
                m.id AS member_id,
                m.name AS member_name

            FROM activity_logs a

            LEFT JOIN members m
                ON a.member_id = m.id

            WHERE a.collaboration_id = ?

            ORDER BY a.created_at DESC, a.id DESC

            LIMIT 100
        """, (project_id,)).fetchall()

    return jsonify([dict(row) for row in rows])


# ==========================================
# PROJECT ANALYTICS
# ==========================================

@app.route("/api/collaborations/<int:project_id>/analytics")
def project_analytics(project_id):

    with get_db() as db:

        project = db.execute(
            "SELECT id FROM collaborations WHERE id = ?",
            (project_id,)
        ).fetchone()

        if not project:
            return jsonify({
                "error": "Project not found"
            }), 404

        task_stats = db.execute("""
            SELECT
                COUNT(*) AS total_tasks,

                SUM(
                    CASE WHEN status = 'done'
                    THEN 1 ELSE 0 END
                ) AS completed_tasks,

                SUM(
                    CASE WHEN status = 'todo'
                    THEN 1 ELSE 0 END
                ) AS todo_tasks,

                SUM(
                    CASE WHEN status = 'in_progress'
                    THEN 1 ELSE 0 END
                ) AS in_progress_tasks

            FROM tasks
            WHERE collaboration_id = ?
        """, (project_id,)).fetchone()

        team_size = db.execute("""
            SELECT COUNT(*)
            FROM collaboration_members
            WHERE collaboration_id = ?
        """, (project_id,)).fetchone()[0]

        update_count = db.execute("""
            SELECT COUNT(*)
            FROM updates
            WHERE collaboration_id = ?
        """, (project_id,)).fetchone()[0]

        member_stats = db.execute("""
            SELECT
                m.id AS member_id,
                m.name AS member_name,
                COUNT(t.id) AS assigned_tasks,

                SUM(
                    CASE WHEN t.status = 'done'
                    THEN 1 ELSE 0 END
                ) AS completed_tasks

            FROM collaboration_members cm

            JOIN members m
                ON cm.member_id = m.id

            LEFT JOIN tasks t
                ON t.assigned_to = m.id
                AND t.collaboration_id = cm.collaboration_id

            WHERE cm.collaboration_id = ?

            GROUP BY m.id, m.name

            ORDER BY completed_tasks DESC, assigned_tasks DESC, m.name
        """, (project_id,)).fetchall()

    total = task_stats["total_tasks"] or 0
    completed = task_stats["completed_tasks"] or 0

    return jsonify({
        "total_tasks": total,
        "completed_tasks": completed,
        "todo_tasks": task_stats["todo_tasks"] or 0,
        "in_progress_tasks": task_stats["in_progress_tasks"] or 0,
        "progress": round((completed / total) * 100) if total else 0,
        "team_size": team_size,
        "updates_count": update_count,

        "member_contributions": [
            {
                "member_id": row["member_id"],
                "member_name": row["member_name"],
                "assigned_tasks": row["assigned_tasks"],
                "completed_tasks": row["completed_tasks"] or 0
            }
            for row in member_stats
        ]
    })


# ==========================================
# EVENTS & EXPERIENCES
# ==========================================

@app.route("/api/events", methods=["GET", "POST"])
def events():

    with get_db() as db:

        if request.method == "POST":

            data = request.get_json(silent=True) or {}

            title = str(data.get("title", "")).strip()
            description = str(data.get("description", "")).strip()
            category = str(data.get("category", "Community")).strip()
            event_date = str(data.get("event_date", "")).strip()
            event_time = str(data.get("event_time", "")).strip()
            venue = str(data.get("venue", "")).strip()
            created_by = data.get("created_by")
            capacity = data.get("capacity", 0)

            if not title or not event_date or not created_by:
                return jsonify({
                    "error": "Title, event date and creator are required"
                }), 400

            if len(title) > 150:
                return jsonify({
                    "error": "Title must be under 150 characters"
                }), 400

            try:
                parsed_date = date.fromisoformat(event_date)

            except ValueError:
                return jsonify({
                    "error": "Event date must use YYYY-MM-DD format"
                }), 400

            if parsed_date < date.today():
                return jsonify({
                    "error": "Event date cannot be in the past"
                }), 400

            try:
                capacity = int(capacity or 0)

            except (TypeError, ValueError):
                return jsonify({
                    "error": "Capacity must be a number"
                }), 400

            if capacity < 0:
                return jsonify({
                    "error": "Capacity cannot be negative"
                }), 400

            creator = valid_member(db, created_by)

            if not creator:
                return jsonify({
                    "error": "Creator not found"
                }), 404

            db.execute("""
                INSERT INTO events (
                    title,
                    description,
                    category,
                    event_date,
                    event_time,
                    venue,
                    capacity,
                    created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                description,
                category,
                event_date,
                event_time,
                venue,
                capacity,
                created_by
            ))

            event_id = db.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            return jsonify({
                "message": "Event created successfully!",
                "event_id": event_id
            }), 201

        member_id = request.args.get("member_id", type=int)
        status_filter = request.args.get("status", "all")

        query = """
            SELECT
                e.*,
                m.name AS creator_name,

                (
                    SELECT COUNT(*)
                    FROM event_attendees ea
                    WHERE ea.event_id = e.id
                    AND ea.attendance_status IN ('registered', 'attended')
                ) AS attendee_count,

                (
                    SELECT COUNT(*)
                    FROM event_attendees ea
                    WHERE ea.event_id = e.id
                    AND ea.attendance_status = 'attended'
                ) AS attended_count
        """

        if member_id:

            query += """,
                (
                    SELECT ea.attendance_status
                    FROM event_attendees ea
                    WHERE ea.event_id = e.id
                    AND ea.member_id = ?
                ) AS my_status
            """

        else:
            query += ", NULL AS my_status"

        query += """
            FROM events e
            JOIN members m ON e.created_by = m.id
            WHERE 1 = 1
        """

        params = []

        if member_id:
            params.append(member_id)

        if status_filter in ("upcoming", "completed", "cancelled"):
            query += " AND e.status = ?"
            params.append(status_filter)

        query += """
            ORDER BY e.event_date ASC, e.event_time ASC, e.id DESC
        """

        rows = db.execute(query, params).fetchall()

    return jsonify([dict(row) for row in rows])


# ==========================================
# SINGLE EVENT DETAILS
# ==========================================

@app.route("/api/events/<int:event_id>")
def event_details(event_id):

    member_id = request.args.get("member_id", type=int)

    with get_db() as db:

        event = db.execute("""
            SELECT
                e.*,
                m.name AS creator_name,

                (
                    SELECT COUNT(*)
                    FROM event_attendees ea
                    WHERE ea.event_id = e.id
                    AND ea.attendance_status IN ('registered', 'attended')
                ) AS attendee_count,

                (
                    SELECT COUNT(*)
                    FROM event_attendees ea
                    WHERE ea.event_id = e.id
                    AND ea.attendance_status = 'attended'
                ) AS attended_count

            FROM events e
            JOIN members m ON e.created_by = m.id

            WHERE e.id = ?
        """, (event_id,)).fetchone()

        if not event:
            return jsonify({
                "error": "Event not found"
            }), 404

        result = dict(event)

        if member_id:

            registration = db.execute("""
                SELECT attendance_status AS my_status
                FROM event_attendees
                WHERE event_id = ? AND member_id = ?
            """, (event_id, member_id)).fetchone()

            result["my_status"] = (
                registration["my_status"]
                if registration else None
            )

    return jsonify(result)


# ==========================================
# RSVP TO EVENT
# ==========================================

@app.route("/api/events/<int:event_id>/rsvp", methods=["POST"])
def rsvp_event(event_id):

    data = request.get_json(silent=True) or {}
    member_id = data.get("member_id")

    if not member_id:
        return jsonify({
            "error": "Member ID is required"
        }), 400

    with get_db() as db:

        event = db.execute("""
            SELECT * FROM events
            WHERE id = ?
        """, (event_id,)).fetchone()

        member = valid_member(db, member_id)

        if not event:
            return jsonify({
                "error": "Event not found"
            }), 404

        if not member:
            return jsonify({
                "error": "Member not found"
            }), 404

        if event["status"] != "upcoming":
            return jsonify({
                "error": "This event is not accepting registrations"
            }), 400

        existing = db.execute("""
            SELECT * FROM event_attendees
            WHERE event_id = ? AND member_id = ?
        """, (event_id, member_id)).fetchone()

        if existing and existing["attendance_status"] in (
            "registered", "attended"
        ):
            return jsonify({
                "error": "You are already registered for this event"
            }), 409

        attendee_count = db.execute("""
            SELECT COUNT(*)
            FROM event_attendees
            WHERE event_id = ?
            AND attendance_status IN ('registered', 'attended')
        """, (event_id,)).fetchone()[0]

        if event["capacity"] > 0 and attendee_count >= event["capacity"]:
            return jsonify({
                "error": "This event is full"
            }), 409

        if existing:

            db.execute("""
                UPDATE event_attendees
                SET
                    attendance_status = 'registered',
                    feedback = '',
                    rating = NULL,
                    registered_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE event_id = ? AND member_id = ?
            """, (event_id, member_id))

        else:

            db.execute("""
                INSERT INTO event_attendees (event_id, member_id)
                VALUES (?, ?)
            """, (event_id, member_id))

    return jsonify({
        "message": "You're registered for this event!"
    }), 201


# ==========================================
# CANCEL EVENT RSVP
# ==========================================

@app.route("/api/events/<int:event_id>/rsvp", methods=["DELETE"])
def cancel_rsvp(event_id):

    data = request.get_json(silent=True) or {}
    member_id = data.get("member_id")

    if not member_id:
        return jsonify({
            "error": "Member ID is required"
        }), 400

    with get_db() as db:

        event = db.execute(
            "SELECT id FROM events WHERE id = ?",
            (event_id,)
        ).fetchone()

        if not event:
            return jsonify({
                "error": "Event not found"
            }), 404

        registration = db.execute("""
            SELECT * FROM event_attendees
            WHERE event_id = ? AND member_id = ?
        """, (event_id, member_id)).fetchone()

        if not registration or registration["attendance_status"] == "cancelled":
            return jsonify({
                "error": "No active RSVP found"
            }), 404

        if registration["attendance_status"] == "attended":
            return jsonify({
                "error": "Attendance has already been recorded"
            }), 400

        db.execute("""
            UPDATE event_attendees
            SET
                attendance_status = 'cancelled',
                updated_at = CURRENT_TIMESTAMP
            WHERE event_id = ? AND member_id = ?
        """, (event_id, member_id))

    return jsonify({
        "message": "Your RSVP has been cancelled."
    })


# ==========================================
# EVENT ATTENDEE LIST
# ==========================================

@app.route("/api/events/<int:event_id>/attendees")
def event_attendees(event_id):

    with get_db() as db:

        event = db.execute(
            "SELECT id FROM events WHERE id = ?",
            (event_id,)
        ).fetchone()

        if not event:
            return jsonify({
                "error": "Event not found"
            }), 404

        rows = db.execute("""
            SELECT
                ea.id,
                ea.member_id,
                m.name,
                m.bio,
                m.skills,
                ea.attendance_status,
                ea.registered_at

            FROM event_attendees ea

            JOIN members m
                ON ea.member_id = m.id

            WHERE ea.event_id = ?
            AND ea.attendance_status IN ('registered', 'attended')

            ORDER BY ea.registered_at ASC
        """, (event_id,)).fetchall()

    return jsonify([dict(row) for row in rows])


# ==========================================
# MARK EVENT ATTENDANCE
# ==========================================

@app.route("/api/events/<int:event_id>/attendance", methods=["PATCH"])
def mark_event_attendance(event_id):

    data = request.get_json(silent=True) or {}

    creator_id = data.get("creator_id")
    member_id = data.get("member_id")
    attended = data.get("attended")

    if not creator_id or not member_id or not isinstance(attended, bool):
        return jsonify({
            "error": "Creator ID, member ID and attended boolean are required"
        }), 400

    with get_db() as db:

        event = db.execute(
            "SELECT * FROM events WHERE id = ?",
            (event_id,)
        ).fetchone()

        if not event:
            return jsonify({
                "error": "Event not found"
            }), 404

        if event["created_by"] != creator_id:
            return jsonify({
                "error": "Only the event creator can mark attendance"
            }), 403

        registration = db.execute("""
            SELECT * FROM event_attendees
            WHERE event_id = ? AND member_id = ?
        """, (event_id, member_id)).fetchone()

        if not registration:
            return jsonify({
                "error": "This member is not registered for the event"
            }), 404

        if registration["attendance_status"] == "cancelled":
            return jsonify({
                "error": "Cancelled registrations cannot be marked present"
            }), 400

        new_status = "attended" if attended else "registered"

        db.execute("""
            UPDATE event_attendees
            SET
                attendance_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE event_id = ? AND member_id = ?
        """, (new_status, event_id, member_id))

    return jsonify({
        "message": "Attendance updated!",
        "attendance_status": new_status
    })


# ==========================================
# EVENT FEEDBACK
# ==========================================

@app.route("/api/events/<int:event_id>/feedback", methods=["POST"])
def event_feedback(event_id):

    data = request.get_json(silent=True) or {}

    member_id = data.get("member_id")
    feedback = str(data.get("feedback", "")).strip()
    rating = data.get("rating")

    if not member_id:
        return jsonify({
            "error": "Member ID is required"
        }), 400

    if len(feedback) > 1000:
        return jsonify({
            "error": "Feedback must be under 1000 characters"
        }), 400

    if rating is not None:

        try:
            rating = int(rating)

        except (TypeError, ValueError):
            return jsonify({
                "error": "Rating must be a number from 1 to 5"
            }), 400

        if rating < 1 or rating > 5:
            return jsonify({
                "error": "Rating must be between 1 and 5"
            }), 400

    with get_db() as db:

        event = db.execute(
            "SELECT id FROM events WHERE id = ?",
            (event_id,)
        ).fetchone()

        if not event:
            return jsonify({
                "error": "Event not found"
            }), 404

        registration = db.execute("""
            SELECT attendance_status
            FROM event_attendees
            WHERE event_id = ? AND member_id = ?
        """, (event_id, member_id)).fetchone()

        if not registration or registration["attendance_status"] != "attended":
            return jsonify({
                "error": "Only attendees can submit event feedback"
            }), 403

        if not feedback and rating is None:
            return jsonify({
                "error": "Please provide feedback or a rating"
            }), 400

        db.execute("""
            UPDATE event_attendees
            SET
                feedback = ?,
                rating = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE event_id = ? AND member_id = ?
        """, (feedback, rating, event_id, member_id))

    return jsonify({
        "message": "Thanks for sharing your feedback!"
    })


# ==========================================
# EVENT ANALYTICS
# ==========================================

@app.route("/api/events/<int:event_id>/analytics")
def event_analytics(event_id):

    with get_db() as db:

        event = db.execute("""
            SELECT e.*, m.name AS creator_name
            FROM events e
            JOIN members m ON e.created_by = m.id
            WHERE e.id = ?
        """, (event_id,)).fetchone()

        if not event:
            return jsonify({
                "error": "Event not found"
            }), 404

        stats = db.execute("""
            SELECT
                COUNT(*) AS total_registrations,

                SUM(
                    CASE WHEN attendance_status = 'attended'
                    THEN 1 ELSE 0 END
                ) AS attended,

                SUM(
                    CASE WHEN attendance_status = 'registered'
                    THEN 1 ELSE 0 END
                ) AS registered,

                SUM(
                    CASE WHEN attendance_status = 'cancelled'
                    THEN 1 ELSE 0 END
                ) AS cancelled,

                AVG(rating) AS average_rating,

                COUNT(rating) AS ratings_count

            FROM event_attendees
            WHERE event_id = ?
        """, (event_id,)).fetchone()

        feedback_rows = db.execute("""
            SELECT
                ea.feedback,
                ea.rating,
                ea.updated_at,
                m.name AS member_name

            FROM event_attendees ea

            JOIN members m
                ON ea.member_id = m.id

            WHERE ea.event_id = ?
            AND (
                ea.feedback != ''
                OR ea.rating IS NOT NULL
            )

            ORDER BY ea.updated_at DESC
        """, (event_id,)).fetchall()

    registered = stats["registered"] or 0
    attended = stats["attended"] or 0

    total_registrations = registered + attended

    attendance_rate = (
        round((attended / total_registrations) * 100)
        if total_registrations else 0
    )

    return jsonify({
        "event_id": event_id,
        "event_title": event["title"],
        "capacity": event["capacity"],
        "total_registrations": total_registrations,
        "attended": attended,
        "registered": registered,
        "cancelled": stats["cancelled"] or 0,
        "attendance_rate": attendance_rate,

        "average_rating": (
            round(stats["average_rating"], 1)
            if stats["average_rating"] is not None
            else None
        ),

        "ratings_count": stats["ratings_count"] or 0,
        "feedback": [dict(row) for row in feedback_rows]
    })


# ==========================================
# RUN APP
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)
