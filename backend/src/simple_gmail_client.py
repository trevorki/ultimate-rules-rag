import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
import traceback


class SimpleGmailClient:
    def __init__(self):
        load_dotenv()
        self.email = os.getenv('GMAIL_USER_EMAIL')
        self.password = os.getenv('GMAIL_APP_PASSWORD')
        self.imap = None
        self.smtp = None

    def _connect_imap(self):
        if not self.imap:
            self.imap = imaplib.IMAP4_SSL("imap.gmail.com")
            self.imap.login(self.email, self.password)

    def _disconnect_imap(self):
        if self.imap:
            self.imap.close()
            self.imap.logout()
            self.imap = None

    def _connect_smtp(self):
        if not self.smtp:
            self.smtp = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            self.smtp.login(self.email, self.password)

    def _disconnect_smtp(self):
        if self.smtp:
            self.smtp.quit()
            self.smtp = None

    def send_email(self, to_addr, subject, body, reply_to=None):
        try:
            print(f"****Attempting to send email to {to_addr}")
            print(f"****Using GMAIL_USER: {self.email}")  # Don't log the password!
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.email
            msg['To'] = to_addr
            if reply_to:
                msg['Reply-To'] = reply_to

            print("****Created email message")
            
            self._connect_smtp()
            print("****SMTP connection established")
            
            self.smtp.send_message(msg)
            print("****Message sent")
            
            self.smtp.quit()
            print("****SMTP connection closed")
            
            return True
            
        except Exception as e:
            print(f"****Error in send_email: {str(e)}")
            print(f"****Full traceback: {traceback.format_exc()}")
            if self.smtp:
                try:
                    self.smtp.quit()
                except:
                    pass
            return False

    def fetch_emails(self, num_emails=5, unread_only=True):
        try:
            self._connect_imap()
            self.imap.select("INBOX")
            
            # Search criteria: ALL or UNSEEN
            search_criterion = "UNSEEN" if unread_only else "ALL"
            _, messages = self.imap.search(None, search_criterion)
            messages = messages[0].split()
            
            # Return empty list if no messages found
            if not messages:
                return []
            
            emails = []
            # Process the most recent n emails
            for i in range(min(num_emails, len(messages))):
                _, msg = self.imap.fetch(messages[-(i+1)], '(RFC822)')
                email_body = msg[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Get email body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = email_message.get_payload(decode=True).decode()
                
                emails.append({
                    'subject': email_message['subject'],
                    'from': email_message['from'],
                    'date': email_message['date'],
                    'body': body,
                    'id': messages[-(i+1)].decode()
                })
            return emails
        finally:
            self._disconnect_imap()

    def send_validation_email(self, email_address, base_url, token):
        """
        Send an email validation message to a user.
        
        Args:
            email_address (str): The recipient's email address
            base_url (str): The base URL for verification (e.g., 'https://yourapp.com/verify')
            token (str): The verification token
        """
        subject = "Please Verify Your Email Address"
        
        # Create verification link
        verification_link = f"{base_url.rstrip('/')}/verify?token={token}"
        
        
        body = f"""Hello,
        
        Thank you for registering! Please verify your email address by clicking the link below:

        {verification_link}

        This link will expire in 24 hours.

        If you didn't request this verification, you can safely ignore this email.

        Best regards,
        The Ultimate Rules Chat Team
        """.replace("    ", " ")
        
        try:
            self.send_email(
                to_addr=email_address,
                subject=subject,
                body=body,
                reply_to="noreply@ultimateruleschat.com"
            )
            return True
        except Exception as e:
            print(f"Failed to send validation email: {e}")
            import traceback
            print(traceback.format_exc())
            return False
        finally:
            self._disconnect_smtp()

    def send_forgot_password_email(self, email_address: str, base_url: str, token: str) -> bool:
        """Send a password reset email to the user."""
        try:
            print(f"****Sending password reset email to {email_address}")
            subject = "Reset Your Password"
            
            # Create reset link
            reset_link = f"{base_url.rstrip('/')}/reset-password?token={token}"
            print(f"****Reset link generated: {reset_link}")
            
            body = f"""
Hello,

We received a request to reset your password. Click the link below to set a new password:

{reset_link}

This link will expire in 1 hour.

If you didn't request this password reset, you can safely ignore this email.

Best regards,
The Ultimate Rules Chat Team
"""
            print("****Email body created")
            
            success = self.send_email(
                to_addr=email_address,
                subject=subject,
                body=body,
                reply_to="noreply@ultimateruleschat.com"
            )
            
            if success:
                print(f"****Successfully sent password reset email to {email_address}")
            else:
                print(f"****Failed to send password reset email to {email_address}")
            
            return success
            
        except Exception as e:
            print(f"****Error sending password reset email: {str(e)}")
            print(f"****Full traceback: {traceback.format_exc()}")
            return False

# Usage example:
if __name__ == "__main__":
    import json
    client = SimpleGmailClient()
    
    # # Send an email
    # print(f"Sending email")
    # client.send_email(
    #     "trevorkinsey@gmail.com",
    #     "Test Email",
    #     "This is a test email sent using SMTP!"
    # )
    
    # # Read latest emails
    # print(f"Reading latest emails")
    # latest_emails = client.fetch_emails(3, unread_only = False)
    # print(json.dumps(latest_emails, indent=4))

    # send validation email
    print(f"Sending validation email")
    client.send_validation_email(
        "trevorkinsey@gmail.com",
        "https://ultimateruleschat.com",
        "1234567890"
    )
