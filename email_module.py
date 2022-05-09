import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib



def send(to, subject, body, attachment):

    try:
        smpt_server = 'smtp.gmail.com'
        email_adress = "pycnometer.00@gmail.com"
        email_pass = "2p5BKuLNd9WbdiR"

        fromname = 'pycnometer'
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = fromname
        message["To"] = to
        with open(attachment, "rb") as opened:
            openedfile = opened.read()

        attachedfile = MIMEApplication(openedfile, _subtype = "pdf")
        attachedfile.add_header('content-disposition', 'attachment', filename = attachment)
        message.attach(attachedfile)
        message.attach(MIMEText(body, 'plain'))


        mailserver = smtplib.SMTP(smpt_server, 587)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.ehlo()  #again
        mailserver.login(email_adress, email_pass)
        mailserver.sendmail(fromname, to, message.as_string())
        mailserver.quit()
    except Exception:
        print("Недоступен сервер SMPT")