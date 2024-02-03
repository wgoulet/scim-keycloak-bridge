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



def messagerecv():
    while(True):
        rmqpwd = os.environ.get('RABBITMQPWD')
        rmquname = os.environ.get('RABBITMQUNAME')
        rmqvhost = os.environ.get('RABBITMQVHOST')
        creds = pika.PlainCredentials(rmquname,rmqpwd)
        params = pika.ConnectionParameters(virtual_host=rmqvhost,credentials=creds,host='localhost')
        connection = pika.BlockingConnection(parameters=params)
        channel = connection.channel()
        channel.queue_declare(queue='scimbridge')
        channel.basic_consume(queue='scimbridge',auto_ack=True,on_message_callback=callback)
        channel.start_consuming()
    

def callback(channel,method,properties,body):
    print(f"Got {body}")
    
messagerecv()