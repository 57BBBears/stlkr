from flask_mail import Mail, Message

mail = Mail()


def send_email(email_to: str, subject: str, html: str):
    msg = Message(subject, recipients=[email_to], html=html)
    mail.send(msg)
