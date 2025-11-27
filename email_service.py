"""
Email Service for Face Attendance System
Sends attendance reports via email with Excel attachments
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime


class EmailService:
    """Service for sending emails with attachments"""

    def __init__(self):
        """Initialize email service with SMTP configuration from environment"""
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_email = os.getenv('SMTP_EMAIL')
        self.smtp_password = os.getenv('SMTP_PASSWORD')

        if not self.smtp_email or not self.smtp_password:
            raise ValueError("SMTP email credentials not configured. Set SMTP_EMAIL and SMTP_PASSWORD in .env")

    def send_attendance_report(self, recipient_email, session_data, excel_path, spreadsheet_url=None):
        """
        Send attendance report email with Excel attachment

        Args:
            recipient_email: Email address to send to
            session_data: Dictionary with session information
            excel_path: Path to Excel file to attach
            spreadsheet_url: Optional Google Sheets URL to include

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate recipient email
            if not recipient_email or '@' not in recipient_email:
                print(f"[ERROR] Invalid recipient email: {recipient_email}")
                return False

            # Validate Excel file exists
            if not os.path.exists(excel_path):
                print(f"[ERROR] Excel file not found: {excel_path}")
                return False

            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_email
            msg['To'] = recipient_email
            msg['Subject'] = self._generate_subject(session_data)

            # Create email body
            body = self._generate_email_body(session_data, spreadsheet_url)
            msg.attach(MIMEText(body, 'html'))

            # Attach Excel file
            with open(excel_path, 'rb') as f:
                excel_attachment = MIMEApplication(f.read(), _subtype='xlsx')
                excel_filename = os.path.basename(excel_path)
                excel_attachment.add_header('Content-Disposition', 'attachment', filename=excel_filename)
                msg.attach(excel_attachment)

            # Send email
            print(f"[INFO] Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)

            print(f"[INFO] Attendance report sent successfully to {recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError as error:
            print(f"[ERROR] SMTP authentication failed: {error}")
            print("[INFO] Check your SMTP_EMAIL and SMTP_PASSWORD in .env")
            print("[INFO] For Gmail, make sure you're using an App Password, not your regular password")
            return False

        except smtplib.SMTPException as error:
            print(f"[ERROR] SMTP error occurred: {error}")
            return False

        except Exception as error:
            print(f"[ERROR] Failed to send email: {error}")
            import traceback
            traceback.print_exc()
            return False

    def _generate_subject(self, session_data):
        """
        Generate email subject line

        Args:
            session_data: Session information dictionary

        Returns:
            str: Email subject
        """
        session_name = session_data.get('session_name', 'Attendance')
        date_str = datetime.now().strftime('%Y-%m-%d')
        return f"Attendance Report - {session_name} - {date_str}"

    def _generate_email_body(self, session_data, spreadsheet_url=None):
        """
        Generate HTML email body

        Args:
            session_data: Session information dictionary
            spreadsheet_url: Optional Google Sheets URL

        Returns:
            str: HTML email body
        """
        session_name = session_data.get('session_name', 'N/A')
        course_code = session_data.get('course_code', 'N/A')
        course_name = session_data.get('course_name', 'N/A')
        location = session_data.get('location', 'N/A')
        start_time = session_data.get('start_time', 'N/A')
        end_time = session_data.get('end_time', 'N/A')
        attendance_count = session_data.get('attendance_count', 0)

        # Build Google Sheets link section
        sheets_link_html = ""
        if spreadsheet_url:
            sheets_link_html = f"""
            <p>
                <strong>View Online:</strong><br>
                <a href="{spreadsheet_url}" style="color: #4285f4; text-decoration: none;">
                    Open in Google Sheets
                </a>
            </p>
            """

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4285f4;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 0 0 5px 5px;
                }}
                .info-table {{
                    width: 100%;
                    margin: 15px 0;
                }}
                .info-table td {{
                    padding: 8px;
                    border-bottom: 1px solid #ddd;
                }}
                .info-table td:first-child {{
                    font-weight: bold;
                    width: 150px;
                }}
                .footer {{
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                    color: #666;
                    text-align: center;
                }}
                .badge {{
                    background-color: #34a853;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Attendance Report</h2>
                </div>
                <div class="content">
                    <p>Dear Instructor,</p>
                    <p>
                        The attendance report for your session is now available.
                        Please find the Excel file attached to this email.
                    </p>

                    <table class="info-table">
                        <tr>
                            <td>Session:</td>
                            <td><strong>{session_name}</strong></td>
                        </tr>
                        <tr>
                            <td>Course Code:</td>
                            <td>{course_code}</td>
                        </tr>
                        <tr>
                            <td>Course Name:</td>
                            <td>{course_name}</td>
                        </tr>
                        <tr>
                            <td>Location:</td>
                            <td>{location}</td>
                        </tr>
                        <tr>
                            <td>Start Time:</td>
                            <td>{start_time}</td>
                        </tr>
                        <tr>
                            <td>End Time:</td>
                            <td>{end_time}</td>
                        </tr>
                        <tr>
                            <td>Students Present:</td>
                            <td><span class="badge">{attendance_count}</span></td>
                        </tr>
                    </table>

                    {sheets_link_html}

                    <p>
                        <strong>Attachment:</strong><br>
                        The Excel file contains the complete attendance list with student details,
                        timestamps, and confidence scores.
                    </p>

                    <div class="footer">
                        <p>
                            This is an automated message from the Face Attendance System.<br>
                            Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return html_body


def send_attendance_report_email(recipient_email, session_data, excel_path, spreadsheet_url=None):
    """
    Helper function to send attendance report email

    Args:
        recipient_email: Email address to send to
        session_data: Dictionary with session information
        excel_path: Path to Excel file to attach
        spreadsheet_url: Optional Google Sheets URL

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        email_service = EmailService()
        return email_service.send_attendance_report(
            recipient_email,
            session_data,
            excel_path,
            spreadsheet_url
        )
    except Exception as error:
        print(f"[ERROR] Failed to initialize email service: {error}")
        return False
