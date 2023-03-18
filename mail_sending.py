import requests
import json
import os
from typing import Optional
import base64

from app_logger import Logger


# log_fmt = '%(asctime)s : [%(levelname)s] : %(pathname)s : %(funcName)s : %(message)s'
logger = Logger.get_singleton_logger()


class BigFile(object):
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.file_size = os.path.getsize(file_name)
        self.buffer_size = 2 * 1024 * 1024  # 2 MB
        self.upload_url = None

    def to_bytes(self):
        streamed_bytes = []
        with open(self.file_name, 'rb') as f:
            for chunk in self._read_bytes(f):
                streamed_bytes.append(chunk)
        return streamed_bytes

    def _read_bytes(self, file):
        while True:
            binary = file.read(self.buffer_size)
            if self.buffer_size > len(binary):
                yield binary
                break
            yield binary


class Mailer(object):
    """
    Mailer
    """

    def __init__(self, receiver_email: str):
        self.sender_email = os.environ['SENDER_EMAIL']
        self.receiver_email = receiver_email
        self.mail_id = None
        self.auth_token = Mailer._load_auth_token()
        self.headers = {}

        if self.auth_token is not None:
            self.headers = {
                'Authorization': f"Bearer {self.auth_token}",
                'Content-type': 'application/json'
            }

    def new_message(self, mail_subject: str, mail_body: str) -> bool:
        """
        https://docs.microsoft.com/en-us/graph/api/user-post-messages?view=graph-rest-1.0&tabs=http
        """
        url = f"https://graph.microsoft.com/v1.0/users/{self.sender_email}/messages"
        data = {
            "subject": mail_subject,
            "importance": "Normal",
            "body": {
                "contentType": "HTML",
                "content": mail_body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": self.receiver_email
                    }
                }
            ]
        }

        logger.debug('Creating draft message')

        response = requests.post(url=url, headers=self.headers,
                                 data=json.dumps(data).encode(encoding="utf-8"))

        if response.status_code == 201:
            logger.debug('Successfully created draft message')
            self.mail_id = response.json()['id']
            return True
        else:
            logger.error('Failed to create draft message')
            return False

    def send_mail(self) -> bool:
        """
        https://docs.microsoft.com/en-us/graph/api/message-send?view=graph-rest-1.0&tabs=http
        """
        url = f"https://graph.microsoft.com/v1.0/users/{self.sender_email}/messages/{self.mail_id}/send"

        logger.debug('Sending the mail')
        response = requests.post(url=url, headers=self.headers)

        if response.status_code == 202:
            logger.debug('Successfully send the mail')
            return True
        else:
            logger.error('Failed to send the mail!')
            return False

    def add_attachment(self, file_name: str) -> bool:
        if not os.path.exists(file_name):
            logger.error(f'{file_name} is not found!')
            return False

        file_size = os.path.getsize(file_name) / (1024 * 1024)

        if file_size < 3:  # if less than 3 MB
            return self.upload_small_attachment(file_name)
        elif 3 <= file_size <= 36:
            return self.upload_big_attachment(file_name)
        else:
            logger.error("File size is too  big to upload")
            return False

    def upload_small_attachment(self, file_name: str) -> Optional[bool]:
        """
        https://docs.microsoft.com/en-us/graph/api/message-post-attachments?view=graph-rest-1.0&tabs=http
        """

        url = f"https://graph.microsoft.com/v1.0/users/{self.sender_email}/messages/{self.mail_id}/attachments"
        with open(file_name, 'rb') as file:
            content_bytes = base64.b64encode(file.read()).decode("ascii")

        data = {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": file_name,
            "contentBytes": content_bytes
        }

        logger.debug('Uploading attachment')
        response = requests.post(url=url, headers=self.headers,
                                 data=json.dumps(data).encode(encoding="utf-8"))
        if response.status_code == 201:
            logger.debug(f'Successfully uploaded {file_name}')
            return True
        else:
            logger.error(f'Uploading failed for {file_name}')
            return False

    def upload_big_attachment(self, file_name: str) -> Optional[bool]:
        """
        https://docs.microsoft.com/en-us/graph/outlook-large-attachments?tabs=http
        """
        attachment = BigFile(file_name=file_name)

        logger.debug('Creating upload session')
        is_session_created = self._create_upload_session(attachment)
        if is_session_created:
            logger.debug(f'Successfully created a upload session for {file_name}')

        logger.debug('Uploading range of bytes of the file')
        is_file_uploaded = Mailer._start_upload_byte_by_byte(attachment)
        if is_file_uploaded:
            logger.debug(f'Successfully uploaded byte streams of {file_name}')

        success = is_session_created and is_file_uploaded
        if not success:
            logger.error(f'Uploading failed for {file_name}')

        return success

    def _create_upload_session(self, attachment: BigFile) -> bool:
        """
        https://docs.microsoft.com/en-us/graph/outlook-large-attachments?tabs=http#example-create-an-upload-session-for-a-message
        """
        url = f"https://graph.microsoft.com/v1.0/users/{self.sender_email}/messages/{self.mail_id}/attachments/createUploadSession"
        data = {
            "AttachmentItem": {
                "attachmentType": "file",
                "name": attachment.file_name,
                "size": attachment.file_size
            }
        }
        response = requests.post(url=url, headers=self.headers,
                                 data=json.dumps(data).encode(encoding="utf-8"))
        if response.status_code == 201:
            attachment.upload_url = response.json()['uploadUrl']
            return True

        return False

    @staticmethod
    def _load_auth_token() -> str:
        if TOKEN:
        	token = TOKEN.get('access_token')
			return token
        else:
            logger.error('Access token not found!')

    @staticmethod
    def _start_upload_byte_by_byte(attachment: BigFile) -> bool:
        upload_url = attachment.upload_url
        file_size = attachment.file_size
        buffer_size = attachment.buffer_size
        streamed_bytes = attachment.to_bytes()

        for chunk, idx in zip(streamed_bytes, range(0, file_size, buffer_size)):
            start_index = idx
            end_index = idx + len(chunk) - 1

            temp_headers = {
                "Content-Type": "application/octet-stream",
                "Content-Length": f"{len(chunk)}",
                "Content-Range": f'bytes {start_index}-{end_index}/{file_size}'
            }
            response = requests.put(url=upload_url, headers=temp_headers,
                                    data=chunk)
            logger.debug(f"{response.status_code}")

        return True if response.status_code == 201 else False


"""
## Step 1:
mail_acct = Mailer(receiver_email="receiver.email@address.com")
## Step 2:
assert mail_acct.new_message(mail_subject="This is Subject", mail_body="This is <b>mail body</b>") == True
## Step 3:
assert mail_acct.add_attachment(file_name="file1.xlsx") == True
assert mail_acct.add_attachment(file_name='file2.jpg') == True
## Step 4:
assert mail_acct.send_mail() == True
"""
