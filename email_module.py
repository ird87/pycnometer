import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib



def send(to, subject, body, attachment):

    try:
        fromname = 'pycnometer'
        fromemail = 'ird87.post.ru@gmail.com'
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = fromname
        message["To"] = to
        with open(attachment, "rb") as opened:
            openedfile = opened.read()

        attachedfile = MIMEApplication(openedfile, _subtype = "pdf")
        attachedfile.add_header('content-disposition', 'attachment', filename = attachment)
        message.attach(attachedfile)


        mailserver = smtplib.SMTP('smtp.gmail.com', 587)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.ehlo()  #again
        mailserver.login('email', 'pass')
        mailserver.sendmail(fromname, to, message.as_string())
        mailserver.quit()
    finally:
        print("Недоступен сервер SMPT")