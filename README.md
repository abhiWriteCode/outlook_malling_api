# Outlook Malling API
This repo consists APIs (written in Python) to send mails through Microsoft Outlook
- Attach small or large files to Outlook messages


May ref https://learn.microsoft.com/en-us/graph/outlook-large-attachments?tabs=http


API usages:
```python
>>> mail_acct = Mailer(receiver_email="receiver.email@address.com")
>>> assert mail_acct.new_message(mail_subject="This is Subject", mail_body="This is <b>mail body</b>") == True
>>> assert mail_acct.add_attachment(file_name="file1.xlsx") == True
>>> assert mail_acct.add_attachment(file_name='file2.jpg') == True
>>> assert mail_acct.send_mail() == True
```
