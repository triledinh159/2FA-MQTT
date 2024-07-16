import json
import boto3
import time
from random import randint
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

client_dynamo=boto3.resource('dynamodb')

table=client_dynamo.Table('mqtt')

db_client=boto3.client('dynamodb')

default_ttl = 1200

def send_email(email, otp):
    # Email details
    sender_email = "<sender_email>"
    receiver_email = email
    subject = "OTP"
    body_text = "Hello this is: " + str(otp)

    # Gmail SMTP server details
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = sender_email
    smtp_password = "<app_passwd>"  # Replace with your app-specific password

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))

    # Send the email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return {'status': 'Email sent successfully!'}
    except Exception as e:
        return {'status': 'Failed to send email', 'error': str(e)}


        
        
def lambda_handler(event, context):
    email_id=event['queryStringParameters']['email']
    otp_value=randint(100000, 999999)
    
    
    data = db_client.get_item(
        TableName='mqtt',
        Key={
            'email': {
            'S': email_id
            }
        }
    )
    
    if len(data) != 2: 
         return False
    else: 
        df=data["Item"]["OTP"]["N"]
        
        resp = table.update_item(
        Key={'email': email_id},
        UpdateExpression="SET OTP= :n",
        ExpressionAttributeValues={':n': otp_value},
        ReturnValues="UPDATED_NEW")
        
        extime=int(time.time()) + default_ttl
        ext=data["Item"]["EXPIRATION_TIME"]["N"]
        resp = table.update_item(
        Key={'email': email_id},
        UpdateExpression="SET EXPIRATION_TIME= :n",
        ExpressionAttributeValues={':n': extime},
        ReturnValues="UPDATED_NEW")
        
    #     return "New"

    
    # return "A verification code is sent to the email address you provided."
    send_email(email_id, otp_value)