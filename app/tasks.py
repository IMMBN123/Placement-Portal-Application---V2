import requests
from flask import render_template, current_app
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import csv
import uuid
import glob
from datetime import date, timedelta, datetime
from celery import shared_task
from sqlalchemy import not_, func
from app.models import db, user, company, student, placement_drive, application
from sqlalchemy.orm import aliased

@shared_task(name="send_daily_deadline_reminders")
def send_daily_deadline_reminders():
    now = date.today()
    tomorrow = now + timedelta(days=1)
    
    closing_drives = placement_drive.query.join(company).join(user).filter(
        placement_drive.deadline >= now,
        placement_drive.deadline <= tomorrow,
        placement_drive.is_approved == True,
        placement_drive.is_active == True,
        user.is_active == True
    ).all()

    if not closing_drives:
        return "No drives closing in the next 24 hours."

    reminders_sent = 0

    for drive in closing_drives:
        applied_students = db.session.query(application.student_id).filter_by(placement_drive_id=drive.id).subquery()
        
        eligible_unapplied_students = student.query.join(user).filter(
            student.cgpa >= drive.min_cgpa,
            ~student.user_id.in_(applied_students),
            user.is_active == True
        ).all()

        for each_student in eligible_unapplied_students:

            student_user = user.query.get(each_student.user_id) 
            
            deadline = drive.deadline
            message_text = f"<users/{student_user.email}> 🔔 *Deadline Reminder:* Hello {each_student.full_name}, the deadline to apply for *{drive.job_title}* at *{drive.company.company_name}* closes at {deadline} 11:59 PM. Apply on the portal now!"
            
            webhook_url = "https://chat.googleapis.com/v1/spaces/AAQAouxGB2w/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7j_bO1Fnc3e09c1s0hJ0WlDtJ34AN6dUT_1ZYcyeLzg"
    
            send_google_chat_webhook(message_text, webhook_url)
            reminders_sent += 1

    return f"Sent {reminders_sent} reminders for {len(closing_drives)} closing drives."

@shared_task(name="send_daily_interview_reminders")
def send_daily_interview_reminders():
    now = datetime.now()
    after48 = now + timedelta(days=2)
    
    upcoming_interviews = application.query.join(student).join(user).filter(
        application.status == 'Shortlisted',
        application.interview_at >= now,
        application.interview_at <= after48,
        user.is_active == True
    ).all()

    if not upcoming_interviews:
        return "No interviews in next 48 hours."

    reminders_sent = 0

    for interview in upcoming_interviews:
            
            formatted_date = interview.interview_at.strftime("%Y-%m-%d %I:%M %p")
            
            message_text = f"<users/{interview.student.user.email}> 🔔 *Interview Reminder:* Hello *{interview.student.full_name}*, your interview for the post of *{interview.placement_drive.job_title}* in *{interview.placement_drive.company.company_name}* has a schedule of {formatted_date}."
            
            webhook_url = "https://chat.googleapis.com/v1/spaces/AAQAouxGB2w/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7j_bO1Fnc3e09c1s0hJ0WlDtJ34AN6dUT_1ZYcyeLzg"
    
            send_google_chat_webhook(message_text, webhook_url)
            reminders_sent += 1

    return f"Sent {reminders_sent} reminders for {len(upcoming_interviews)} upcoming interviews."


def send_google_chat_webhook(message_text, url):
    WEBHOOK_URL = url
        
    payload = {"text": message_text}
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send webhook: {e}")

@shared_task(name="send_monthly_admin_report")
def send_monthly_activity_report():
    today = date.today()
    first_day_of_current_month = today.replace(day=1)
    last_day_of_prev_month = first_day_of_current_month - timedelta(days=1)
    first_day_of_prev_month = last_day_of_prev_month.replace(day=1)

    drives_conducted = placement_drive.query.join(company).join(user).filter(
        placement_drive.created_at >= first_day_of_prev_month,
        placement_drive.created_at <= last_day_of_prev_month,
        placement_drive.is_approved == True,
        user.is_active == True
    ).count()

    student_user = aliased(user, name="student_user")
    company_user = aliased(user, name="company_user")

    applications= application.query\
        .join(student, application.student_id == student.user_id)\
        .join(student_user, student.user_id == student_user.id)\
        .join(placement_drive, application.placement_drive_id == placement_drive.id)\
        .join(company, placement_drive.company_id == company.user_id)\
        .join(company_user, company.user_id == company_user.id)\
        .filter(
        placement_drive.created_at >= first_day_of_prev_month,
        placement_drive.created_at <= last_day_of_prev_month,
        company_user.is_active == True,
        student_user.is_active == True
    ).all()

    total_applied = len(applications)
    total_selected = sum(1 for app in applications if app.status == 'Accepted')

    admin = user.query.filter_by(role='admin').first()
    if not admin:
        return "No admin found to send report to."

    html_content = render_template(
        'admin_report.html',
        month_name=first_day_of_prev_month.strftime("%B"),
        year=first_day_of_prev_month.year,
        drives_count=drives_conducted,
        applied_count=total_applied,
        selected_count=total_selected
    )

    sender_email = os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("MAIL_PASSWORD")
    smtp_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("MAIL_PORT", 587))

    msg = MIMEMultipart("alternative")
    msg['Subject'] = f"Monthly Placement Report - {first_day_of_prev_month.strftime('%B %Y')}"
    msg['From'] = sender_email
    msg['To'] = admin.email

    part = MIMEText(html_content, "html")
    msg.attach(part)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, admin.email, msg.as_string())
        server.quit()
        return "Monthly report sent successfully!"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

@shared_task(name="send_monthly_company_report") 
def send_company_report():
    today = date.today()
    first_day_of_current_month = today.replace(day=1)
    last_day_of_prev_month = first_day_of_current_month - timedelta(days=1)
    first_day_of_prev_month = last_day_of_prev_month.replace(day=1)
    
    all_companies = company.query.join(user).filter(
        company.is_approved == True,
        company.is_rejected == False,
        user.is_active == True
    ).all()

    if not all_companies:
        return "No active companies found."

    sender_email = os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("MAIL_PASSWORD")
    smtp_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("MAIL_PORT", 587))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
    except Exception as e:
        return f"CRITICAL ERROR: Failed to connect to email server. {str(e)}"

    emails_sent = 0

    for comp in all_companies:
        drives = placement_drive.query.filter_by(company_id=comp.user_id,).all()
        
        roles_data = []
        comp_total_apps = 0
        comp_total_shortlisted = 0
        comp_total_hired = 0

        for drive in drives:
            apps = application.query.filter(
                application.placement_drive_id == drive.id,
                application.applied_at >= first_day_of_prev_month,
                application.applied_at <= last_day_of_prev_month
            ).all()

            if not apps:
                continue

            role_total = len(apps)
            role_shortlisted = sum(1 for a in apps if a.status.lower() == 'shortlisted')
            role_hired = sum(1 for a in apps if a.status.lower() == 'accepted')

            comp_total_apps += role_total
            comp_total_shortlisted += role_shortlisted
            comp_total_hired += role_hired

            roles_data.append({
                "id": drive.id,
                "title": drive.job_title,
                "applied": role_total,
                "interviews": role_shortlisted,
                "selected": role_hired
            })

        html_content = render_template(
            'company_report.html',
            company_name=comp.company_name,
            month_name=first_day_of_prev_month.strftime("%B"),
            year=first_day_of_prev_month.year,
            total_applications=comp_total_apps,
            total_shortlisted=comp_total_shortlisted,
            total_hired=comp_total_hired,
            roles_data=roles_data
        )

        msg = MIMEMultipart("alternative")
        msg['Subject'] = f"Monthly Placement Analytics - {first_day_of_prev_month.strftime('%B %Y')}"
        msg['From'] = sender_email
        msg['To'] = comp.user.email 

        part = MIMEText(html_content, "html")
        msg.attach(part)

        try:
            server.sendmail(sender_email, comp.user.email, msg.as_string())
            emails_sent += 1
        except Exception as e:
            print(f"Failed to send report to {comp.company_name}: {str(e)}")

    server.quit()
    
    return f"Monthly report job complete. Sent {emails_sent} emails to companies."
    
@shared_task()
def export_student_applications_csv(student_id):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    search_pattern = os.path.join(upload_folder, f"export_{student_id}_*.csv")
    
    for old_file in glob.glob(search_pattern):
        try:
            os.remove(old_file)
        except OSError:
            pass

    applications = application.query.filter_by(student_id=student_id).all()
    
    filename = f"export_{student_id}_{uuid.uuid4().hex[:8]}.csv"
    
    filepath = os.path.join(upload_folder, filename)
    
    with open(filepath, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Student ID', 'Company Name', 'Drive Title', 'Application Status', 'Date'])
        
        for app in applications:
            writer.writerow([
                app.student_id,
                app.placement_drive.company.company_name,
                app.placement_drive.job_title,
                app.status,
                app.applied_at
            ])
            
    return {"filename": filename}

@shared_task()
def export_company_drives_csv(company_id):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    search_pattern = os.path.join(upload_folder, f"export_{company_id}_*.csv")
    
    for old_file in glob.glob(search_pattern):
        try:
            os.remove(old_file)
        except OSError:
            pass

    drives = placement_drive.query.filter_by(company_id=company_id).all()
    
    filename = f"export_{company_id}_{uuid.uuid4().hex[:8]}.csv"
    
    filepath = os.path.join(upload_folder, filename)
    
    with open(filepath, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Drive ID', 'Drive Title', 'Package (LPA)', '#Applcations', 'Status'])
        
        app_counts = dict(
            db.session.query(
                application.placement_drive_id, 
                func.count(application.id)
            ).group_by(application.placement_drive_id).all()
        )

        for drive in drives:
            apps_count = app_counts.get(drive.id, 0)
            
            if not drive.is_approved and not drive.is_rejected:
                status = 'Pending'
            elif not drive.is_approved and drive.is_rejected:
                status = 'Rejected'
            else:
                status = 'Active' if drive.is_active else 'Closed'
                
            writer.writerow([
                drive.id,
                drive.job_title,
                drive.package_lpa,
                apps_count,
                status
            ])
            
    return {"filename": filename}