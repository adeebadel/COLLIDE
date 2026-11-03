# COLLIDE
### Community Connection & Collaboration Engine

**Good things happen when people collide.**

[Live Demo](https://collide-1wao.onrender.com/) · [GitHub Repository](https://github.com/adeebadel/COLLIDE)

## Overview

COLLIDE is an independent community platform prototype exploring how communities can turn individual interests, skills, needs and ideas into meaningful connections and collaborative projects.

The central question behind COLLIDE:

**What if a community didn't just help people meet, but helped them build something together?**

## The Problem

Communities can have members, events and conversations but still struggle to turn those interactions into meaningful collaboration.

People may have skills others need, ideas waiting for collaborators, or opportunities to contribute — but those connections aren't always visible.

## The Solution

COLLIDE introduces a structured interaction system where members can:

- Share what they need, offer or want to build.
- Discover people with complementary interests and skills.
- Send and manage connection requests.
- Create collaborative projects.
- Join project teams and track tasks.
- Share progress updates.
- Organise events and manage registrations.
- Track attendance, feedback and community engagement.

## Core Features

### 1. Community Intelligence Dashboard
A central overview of community activity, engagement, projects, tasks and events.

### 2. Signals
A space for members to communicate what they need, offer or want to build.

### 3. People Matching
Discover potential collaborators through shared or complementary interests.

### 4. Connection Requests
Turn potential matches into intentional connections.

### 5. Collaborative Projects
Create projects, build teams, assign tasks and share progress.

### 6. Events & Experiences
Create events, manage registrations, track attendance and collect feedback.

## Technology Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite
- **Deployment:** Render
- **Version Control:** Git & GitHub

## Project Structure

```text
COLLIDE/
├── app.py
├── database.py
├── requirements.txt
├── .gitignore
├── templates/
│   └── index.html
└── static/
    ├── app.js
    ├── events.js
    └── style.css
```

## Running Locally

Clone the repository:

```bash
git clone https://github.com/adeebadel/COLLIDE.git
cd COLLIDE
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Current Status

COLLIDE is a deployed, independently developed prototype.

It is an experiment in designing better systems for community engagement and collaboration, not an established community platform with verified real-world outcomes.

**Prototype limitation:** The current deployment uses SQLite on Render's temporary filesystem. Data persistence across service restarts and redeployments is not guaranteed. Authentication and production-grade access controls are also not yet implemented.

## Vision

The goal is to explore how thoughtful systems can help people move from:

**Discover → Connect → Collaborate → Build**

Because a strong community isn't just about how many people join. It's about what people make possible together.

---

*Built as an independent community systems experiment.*
