import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD

    def send_password_reset_email(self, email: str, reset_link: str):
        """
        Send password reset email with the reset link
        """
        if not self.smtp_host or not self.smtp_user or not self.smtp_password:
            logger.error("SMTP credentials not configured. Cannot send email.")
            logger.info(f"PASSWORD RESET LINK for {email}: {reset_link}")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Password Reset Request - WhatsApp Platform"
            msg['From'] = self.smtp_user
            msg['To'] = email

            # HTML email body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2563eb;">Password Reset Request</h2>
                    <p>Hello,</p>
                    <p>You recently requested to reset your password for your WhatsApp Platform account.</p>
                    <p>Click the link below to reset your password:</p>
                    <p>
                        <a href="{reset_link}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="background-color: #f3f4f6; padding: 10px; word-break: break-all; font-size: 14px;">{reset_link}</p>
                    <p><strong>This link will expire in 30 minutes.</strong></p>
                    <p>If you did not request a password reset, please ignore this email.</p>
                    <p>Thank you,<br>WhatsApp Platform Team</p>
                </div>
            </body>
            </html>
            """

            # Plain text email body
            text_body = f"""
            Password Reset Request
            
            Hello,
            
            You recently requested to reset your password for your WhatsApp Platform account.
            
            Click the link below to reset your password:
            {reset_link}
            
            This link will expire in 30 minutes.
            
            If you did not request a password reset, please ignore this email.
            
            Thank you,
            WhatsApp Platform Team
            """

            # Attach both plain text and HTML versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Password reset email sent successfully to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            logger.info(f"PASSWORD RESET LINK for {email}: {reset_link}")
            return False


email_service = EmailService()
