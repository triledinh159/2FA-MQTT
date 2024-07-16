import json
import boto3
import time

client = boto3.client('dynamodb')

def lambda_handler(event, context):
    email = event['queryStringParameters']['email']
    otp_from_user = event['queryStringParameters']['otp']
    
    response = client.get_item(
        TableName='mqtt',
        Key={
            'email': {
                'S': email
            }
        }
    )
    
    if 'Item' not in response:
        return {
            "statusCode": 200,
            "body": json.dumps("No such OTP was shared")
        }

    item = response['Item']
    latest_stored_otp_value = str(item.get('OTP', {}).get('N'))
    expiration_time = int(item.get('EXPIRATION_TIME', {}).get('N'))
    
    if expiration_time < int(time.time()):
        return {
            "statusCode": 200,
            "body": json.dumps("Time Over")
        }
    else:
        if latest_stored_otp_value == otp_from_user:
            # OTP is verified, now retrieve username and password if they exist
            username = item.get('Username', {}).get('S')
            password = item.get('Password', {}).get('S')
            
            if username and password:
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": "Verified",
                        "username": username,
                        "password": password
                    })
                }
            else:
                return {
                    "statusCode": 200,
                    "body": json.dumps("Username or password not found")
                }
        else:
            return {
                "statusCode": 200,
                "body": json.dumps("Wrong OTP")
            }
