from io import StringIO
import select
import csv
from systemd import journal
from datetime import datetime, timedelta
import json
import pprint
import os
import time
from pubsub import pub
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
import pika
from threading import Thread



def messagesend(channel,message):
#    rmqpwd = os.environ.get('RABBITMQPWD')
#    rmquname = os.environ.get('RABBITMQUNAME')
#    rmqvhost = os.environ.get('RABBITMQVHOST')
#    creds = pika.PlainCredentials(rmquname,rmqpwd)
#    params = pika.ConnectionParameters(virtual_host=rmqvhost,credentials=creds,host='localhost')
#    connection = pika.BlockingConnection(parameters=params)
#    channel = connection.channel()
#    channel.queue_declare(queue='scimbridge')
    resp = channel.basic_publish(exchange='',routing_key='scimbridge',body=message)
    resp
    
    
rmqpwd = os.environ.get('RABBITMQPWD')
rmquname = os.environ.get('RABBITMQUNAME')
rmqvhost = os.environ.get('RABBITMQVHOST')
creds = pika.PlainCredentials(rmquname,rmqpwd)
params = pika.ConnectionParameters(virtual_host=rmqvhost,credentials=creds,host='localhost')
connection = pika.BlockingConnection(parameters=params)
channel = connection.channel()
channel.queue_declare(queue='scimbridge')

message = "hello world"
while(True):
    print(f"Sending message {message}")
    messagesend(channel=channel,message=message)
    time.sleep(10)
