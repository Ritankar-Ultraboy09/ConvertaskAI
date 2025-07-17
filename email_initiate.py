import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import os
from TalkConvertask import Convertask  
from email.mime.application import MIMEApplication

class EmailAgent:
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.from_email = "2205920@kiit.ac.in"
        self.from_password = "wfti riaq hyvg gbey"
    
    def generate_email(self, prompt: str, email_type: str = "professional") -> Optional[dict]:

        
        email_prompt = f"""
You are an expert email writer. Based on the following request, generate a professional email.

Request: {prompt}

Email Type: {email_type}

Return your response as a JSON object with this exact structure:
{{
    "subject": "Your email subject here",
    "body": "Your complete email body here"
}}

Guidelines:
- Make it professional and well-structured
- Include appropriate greetings and sign-offs
- Be clear and actionable
- Use proper email formatting
- Keep it concise but comprehensive
- Use a professional tone appropriate for business communication
"""
        
        
        email_schema = {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["subject", "body"]
        }
        
        result = Convertask(email_prompt, email_schema)
        return result
    
    def send_email(self, to_emails: List[str], subject: str, body: str, is_html: bool = False,  attachments: Optional[List[tuple]] = None) -> bool:
        try:
            if not self.from_email or not self.from_password:
                print("[ERROR] Email credentials not set. Use EMAIL_ADDRESS and EMAIL_PASSWORD env vars.")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ", ".join(to_emails)
            msg['Subject'] = subject
            
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            if attachments:
                for filename, file_bytes in attachments:
                    part = MIMEApplication(file_bytes, Name=filename)
                    part['Content-Disposition'] = f'attachment; filename="{filename}"'
                    msg.attach(part)
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.from_email, self.from_password)
            server.sendmail(self.from_email, to_emails, msg.as_string())
            server.quit()
            
            print(f"[SUCCESS] Email sent to {', '.join(to_emails)}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to send email: {e}")
            return False
    
    def generate_and_send(self, prompt: str, to_emails: List[str], email_type: str = "professional") -> dict:
     
        email_content = self.generate_email(prompt, email_type)
        
        if not email_content:
            return {
                "success": False,
                "error": "Failed to generate email content"
            }
        
        success = self.send_email(
            to_emails=to_emails,
            subject=email_content.get('subject', 'Generated Email'),
            body=email_content.get('body', ''),
            is_html=False
        )
        
        return {
            "success": success,
            "subject": email_content.get('subject'),
            "body": email_content.get('body'),
            "recipients": to_emails
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize email agent
    agent = EmailAgent()
    
    # Test email generation
    test_prompt = "Write a follow-up email to the team about our meeting transcript analysis results. Include key action items and next steps."
    
    email_content = agent.generate_email(test_prompt, "professional")
    print("Generated email content:")
    print(json.dumps(email_content, indent=2))
    
   