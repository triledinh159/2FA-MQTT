import imaplib
import email
import re
import requests
import time
import csv
import sys
from Crypto.Cipher import AES
import base64
import os
import paho.mqtt.client as mqtt
from paho.mqtt import client as mqtt_client
from Crypto.Util.Padding import pad
client_id = 'tri'
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker")
    else:
        print("Failed to connect, return code %d\n", rc)

def on_publish(client, userdata, mid):
    print("\nMessage Published")

def get_otp(email):
	url = f"<api_url_email>"
	response = requests.get(url)
	data = response.json()
	if response.status_code != 200:
		print("Failed")
	# time.sleep(2)
	#print(data)

def verify(email, otp):
	url = f"<api_url_email_and_otp>"
	response = requests.get(url)
	data = response.json()
	if response.status_code == 200:
		#print(data)
		return data['username'], data['password']



def access_mail(email_user, email_pass):
	# Connect to the Gmail IMAP server
	mail = imaplib.IMAP4_SSL('imap.gmail.com')
	mail.login(email_user, email_pass)
	mail.select('inbox')
	status, data = mail.search(None, 'ALL')
	
	# Get the list of email IDs
	mail_ids = data[0].split()
	latest_code = None
	for mail_id in reversed(mail_ids):
		# Fetch the email by ID
		status, data = mail.fetch(mail_id, '(RFC822)')
		msg = email.message_from_bytes(data[0][1])
		if msg.is_multipart():
			for part in msg.walk():
				if part.get_content_type() == 'text/plain':
					body = part.get_payload(decode=True).decode()
					match = re.search(r'\b\d{6}\b', body)
					if match:
						latest_code = match.group()
						mail.store(mail_id, '+FLAGS', '\\Deleted')
						break
		else:
			body = msg.get_payload(decode=True).decode()
			match = re.search(r'\b\d{6}\b', body)
			if match:
				latest_code = match.group()
				mail.store(mail_id, '+FLAGS', '\\Deleted')
		if latest_code:
			break
	mail.expunge()
	mail.logout()
	
	return latest_code


def read_csv(file_path):
    with open(file_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            return row['aesKey'], row['iv']
    raise Exception("CSV file is empty or invalid format")

def decrypt_data(encrypted_data, key, iv):
    encrypted_data_bytes = bytes.fromhex(encrypted_data)
    key_bytes = bytes.fromhex(key)
    iv_bytes = bytes.fromhex(iv)
    
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    decrypted_data = cipher.decrypt(encrypted_data_bytes)
    
    pad_len = decrypted_data[-1]
    return decrypted_data[:-pad_len].decode('utf-8')

def encrypt_message(message, key, iv):
    key_bytes = bytes.fromhex(key)
    iv_bytes = bytes.fromhex(iv)
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    padded_message = pad(message.encode(), AES.block_size)
    encrypted_message = cipher.encrypt(padded_message)
    encrypted_message_base64 = base64.b64encode(encrypted_message).decode()

    return encrypted_message_base64

def main():
	email_user = '<email_recieve_otp>'
	email_pass = '<app_password>'
	get_otp(email_user)
	time.sleep(2)
	cusername, cpassword = verify(email_user,access_mail(email_user, email_pass))
	if len(sys.argv) != 6:
		print("<key_file_1> <key_file_2> <host> <port> <topic>")
		sys.exit(1)

	csv_file_1 = sys.argv[1]
	csv_file_2 = sys.argv[2]
	host = sys.argv[3]
	port = int(sys.argv[4])
	topic = sys.argv[5]

	aes_key_1, iv_1 = read_csv(csv_file_1)
	username = decrypt_data(cusername, aes_key_1, iv_1)
	password = decrypt_data(cpassword, aes_key_1, iv_1)
	# print(username)
	# print(password)
	aes_key_2, iv_2 = read_csv(csv_file_2)
	try:
		client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1,client_id)

		# Set callbacks
		client.on_connect = on_connect
		#client.on_publish = on_publish

		# Set username and password
		client.username_pw_set(username, password)

		# Connect to the broker
		client.connect(host, port)

		# Start the loop
		client.loop_start()
		while True:
		# Prompt user to input message
			message = input("Enter message to publish: ")
			message = encrypt_message(message, aes_key_2, iv_2)
			client.publish(topic, message)

	except KeyboardInterrupt:
		print("\nSTOP")
	finally:
		client.loop_stop()
		client.disconnect()

if __name__ == "__main__":
	main()