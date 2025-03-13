import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content

from app.core.config import SENDGRID_API_KEY, EMAIL_SENDER, ENVIRONMENT

def send_checklist_report(recipient_email, subject, html_content):
    """
    Send an email with a checklist report using SendGrid.
    
    Args:
        recipient_email (str): The email address of the recipient
        subject (str): The email subject
        html_content (str): The HTML content of the email
    
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    # Don't send emails in test environment
    if ENVIRONMENT == "test":
        return True
    
    # If no SendGrid API key, log instead of sending in dev environment
    if not SENDGRID_API_KEY and ENVIRONMENT == "dev":
        print(f"[DEV] Would send email to {recipient_email}:")
        print(f"Subject: {subject}")
        print(f"Content: {html_content}")
        return True
    
    # Prepare the email
    message = Mail(
        from_email=EMAIL_SENDER,
        to_emails=recipient_email,
        subject=subject,
        html_content=Content("text/html", html_content)
    )
    
    try:
        # Send the email
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code >= 200 and response.status_code < 300
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def generate_checklist_report_html(checklist, run, run_items):
    """
    Generate HTML content for a checklist report email.
    
    Args:
        checklist: The Checklist model instance
        run: The ChecklistRun model instance
        run_items: List of ChecklistRunItem model instances
    
    Returns:
        str: HTML content for the email
    """
    completed_count = sum(1 for item in run_items if item.completed)
    total_count = len(run_items)
    
    # Start with the header
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; }}
            .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .item {{ margin-bottom: 10px; }}
            .completed {{ color: #28a745; }}
            .not-completed {{ color: #dc3545; }}
            .notes {{ font-style: italic; color: #6c757d; margin-left: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{checklist.title}</h1>
            <div class="summary">
                <p><strong>Category:</strong> {checklist.category or 'Not specified'}</p>
                <p><strong>Completion Date:</strong> {run.completed_at.strftime('%Y-%m-%d %H:%M') if run.completed_at else 'Not completed'}</p>
                <p><strong>Completion Status:</strong> {completed_count}/{total_count} items completed</p>
                {f'<p><strong>Notes:</strong> {run.notes}</p>' if run.notes else ''}
            </div>
            <h2>Checklist Items</h2>
    """
    
    # Add each item
    for run_item in run_items:
        item = run_item.item
        status_class = "completed" if run_item.completed else "not-completed"
        status_text = "✓ Completed" if run_item.completed else "✗ Not Completed"
        required_text = "Required" if item.is_required else "Optional"
        
        html += f"""
            <div class="item">
                <p><strong>{item.text}</strong> ({required_text}) - <span class="{status_class}">{status_text}</span></p>
                {f'<p class="notes">Notes: {run_item.notes}</p>' if run_item.notes else ''}
            </div>
        """
    
    # Close the HTML
    html += """
        </div>
    </body>
    </html>
    """
    
    return html 