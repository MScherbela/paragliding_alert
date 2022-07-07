import logging
from flask_mail import Message
import utils

def send_email(mail_object, receiver, subject, content):
    msg = Message()
    msg.subject = subject
    msg.body = content
    msg.recipients = [receiver]
    logging.info(f"Sending e-mail to: {receiver}")
    mail_object.send(msg)

def send_paragliding_alert(mail_object, mail_adress, flyable_locations):
    content = "Hi,\n\nit might be possible to fly!\n\n"
    for loc in flyable_locations:
        content += loc['name'] + ": " + ", ".join([utils.WEEKDAYS[d.weekday()] for d in loc['days']]) + "\n"
    content += "\nhttps://paragliding.scherbela.com/\n\n"
    content += "Good luck,\nParagliding-Bot"
    send_email(mail_object, mail_adress, "Paragliding alert", content)