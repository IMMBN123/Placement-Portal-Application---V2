# Placement-Portal-Application---V2

A modern, API-driven campus recruitment platform built with Flask and Vue.js.

The Placement Portal Application (V2) streamlines the hiring process for educational institutes by connecting the Institute (Admin), Companies, and Students in a single, dynamic web app. Transitioning from a manual, server-rendered V1, this updated version provides a fast, Single Page Application (SPA) experience.

Key Highlights:

Tech Stack: Flask (Backend API), Vue.js via CDN + Bootstrap 5 (Frontend), SQLite (Database), and Redis + Celery (Background Tasks).

Admin Role: Controls platform integrity, approves companies/drives, and monitors system-wide analytics.

Company Role: Hosts placement drives, reviews student applications, and updates recruitment statuses.

Student Role: Builds their profile, browses eligible placement drives, applies, and tracks their progress.

Advanced Features: Automated daily reminders, monthly scheduled reports, and background CSV exports without slowing down the UI.

# How to Run :

1. Download all the packages in requirements.txt to your environment.
2. Start your celery server either with docker(preferred) or your local shell.
    * If docker: run `docker run -d -p 6379:6379 --name local-redis redis` while keeping the Docker engine running.
    * For local shell: `sudo apt update`
                       `sudo apt install redis-server`
                       `redis-server`
3. Run run.py and head to the webpage.
