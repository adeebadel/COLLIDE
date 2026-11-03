
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "collide.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                bio TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                interests TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                category TEXT DEFAULT 'General',
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id)
            );

            CREATE TABLE IF NOT EXISTS collaborations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                goal TEXT DEFAULT '',
                owner_id INTEGER NOT NULL,
                status TEXT DEFAULT 'active',
                deadline TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES members(id)
            );

            CREATE TABLE IF NOT EXISTS collaboration_members (
                collaboration_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                PRIMARY KEY (collaboration_id, member_id),
                FOREIGN KEY (collaboration_id)
                    REFERENCES collaborations(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id)
                    REFERENCES members(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collaboration_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collaboration_id)
                    REFERENCES collaborations(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members(id)
            );

            CREATE TABLE IF NOT EXISTS connection_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES members(id),
                FOREIGN KEY (recipient_id) REFERENCES members(id),
                CHECK (sender_id != recipient_id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collaboration_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                assigned_to INTEGER,
                created_by INTEGER NOT NULL,
                due_date TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'todo'
                    CHECK (status IN ('todo', 'in_progress', 'done')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collaboration_id)
                    REFERENCES collaborations(id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_to)
                    REFERENCES members(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by)
                    REFERENCES members(id)
            );

            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collaboration_id INTEGER NOT NULL,
                member_id INTEGER,
                task_id INTEGER,
                action_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (collaboration_id)
                    REFERENCES collaborations(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id)
                    REFERENCES members(id) ON DELETE SET NULL,
                FOREIGN KEY (task_id)
                    REFERENCES tasks(id) ON DELETE SET NULL
            );

            /* EVENTS */

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'Community',
                event_date TEXT NOT NULL,
                event_time TEXT DEFAULT '',
                venue TEXT DEFAULT '',
                capacity INTEGER DEFAULT 0,
                created_by INTEGER NOT NULL,
                status TEXT DEFAULT 'upcoming'
                    CHECK (status IN ('upcoming', 'completed', 'cancelled')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES members(id)
            );

            /* EVENT REGISTRATIONS */

            CREATE TABLE IF NOT EXISTS event_attendees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                attendance_status TEXT DEFAULT 'registered'
                    CHECK (
                        attendance_status IN (
                            'registered',
                            'attended',
                            'cancelled'
                        )
                    ),
                feedback TEXT DEFAULT '',
                rating INTEGER,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_id, member_id),
                FOREIGN KEY (event_id)
                    REFERENCES events(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id)
                    REFERENCES members(id) ON DELETE CASCADE,
                CHECK (rating IS NULL OR rating BETWEEN 1 AND 5)
            );

            /* INDEXES */

            CREATE INDEX IF NOT EXISTS idx_tasks_collaboration
            ON tasks(collaboration_id);

            CREATE INDEX IF NOT EXISTS idx_tasks_assigned
            ON tasks(assigned_to);

            CREATE INDEX IF NOT EXISTS idx_activity_collaboration
            ON activity_logs(collaboration_id);

            CREATE INDEX IF NOT EXISTS idx_activity_created
            ON activity_logs(created_at);

            CREATE INDEX IF NOT EXISTS idx_events_date
            ON events(event_date);

            CREATE INDEX IF NOT EXISTS idx_events_creator
            ON events(created_by);

            CREATE INDEX IF NOT EXISTS idx_attendees_event
            ON event_attendees(event_id);

            CREATE INDEX IF NOT EXISTS idx_attendees_member
            ON event_attendees(member_id);
        """)

        # SEED INITIAL MEMBERS AND DEMO DATA

        count = db.execute(
            "SELECT COUNT(*) FROM members"
        ).fetchone()[0]

        if count == 0:
            members = [
                (
                    "Aarav",
                    "Building products and exploring startups",
                    "Python, Flask, SQL",
                    "AI, startups, productivity"
                ),
                (
                    "Maya",
                    "Designer interested in human experiences",
                    "UI/UX, Figma, branding",
                    "Design, creativity, technology"
                ),
                (
                    "Rohan",
                    "Developer who enjoys solving real problems",
                    "JavaScript, React, Python",
                    "Open source, AI, web"
                ),
                (
                    "Sara",
                    "Content creator and community enthusiast",
                    "Writing, video editing, marketing",
                    "Creators, storytelling, communities"
                ),
                (
                    "Ishaan",
                    "Learning AI and building prototypes",
                    "Python, machine learning, research",
                    "AI, research, entrepreneurship"
                )
            ]

            db.executemany("""
                INSERT INTO members (name, bio, skills, interests)
                VALUES (?, ?, ?, ?)
            """, members)

            signals = [
                (
                    1, "Need a UI designer",
                    "I'm building a productivity tool and need help designing the interface.",
                    "need", "Design"
                ),
                (
                    2, "Can help with product design",
                    "Happy to help early-stage builders with wireframes and user experience.",
                    "offer", "Design"
                ),
                (
                    3, "Looking for AI collaborators",
                    "Want to experiment with a practical AI project.",
                    "need", "AI"
                ),
                (
                    4, "Can help with content",
                    "I can help projects with launch posts, storytelling and videos.",
                    "offer", "Content"
                ),
                (
                    5, "Building an AI prototype",
                    "Looking for someone interested in researching and testing an AI idea.",
                    "building", "AI"
                ),
                (
                    1, "Need feedback on my product",
                    "Looking for honest feedback from people who build digital products.",
                    "need", "Feedback"
                )
            ]

            db.executemany("""
                INSERT INTO signals
                (member_id, title, description, signal_type, category)
                VALUES (?, ?, ?, ?, ?)
            """, signals)

            db.execute("""
                INSERT INTO collaborations
                (title, description, goal, owner_id, deadline)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "Community Discovery Project",
                "Explore how people in a community can find useful collaborators.",
                "Create and test a simple collaboration experience.",
                1,
                "2026-11-30"
            ))

            db.execute("""
                INSERT INTO collaboration_members
                (collaboration_id, member_id)
                VALUES (1, 1)
            """)

            db.execute("""
                INSERT INTO updates
                (collaboration_id, member_id, content)
                VALUES (1, 1, ?)
            """, ("Project created. Looking for collaborators!",))

            db.execute("""
                INSERT INTO activity_logs
                (collaboration_id, member_id, action_type, message)
                VALUES (1, 1, 'project_created', ?)
            """, ("Created the Community Discovery Project",))
