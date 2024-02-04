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

def process_event(event):
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    token_url = os.environ.get('TOKEN_URL')
    client = BackendApplicationClient(client_id=client_id)
    kcclient = OAuth2Session(client=client)
    token = kcclient.fetch_token(token_url=token_url,client_id=client_id,client_secret=client_secret)
    if((event['opType'] == 'CREATE') and (event['resourceType']) == 'GROUP'):
        create_group_via_scim(group=json.loads(event['representation']),kc_client=kcclient)
    elif((event['opType'] == 'CREATE') and (event['resourceType']) == 'GROUP_MEMBERSHIP'):
        assign_user_to_group_via_scim(event=event,kc_client=kcclient)
    if(((event['opType'] == 'UPDATE') or (event['opType'] == 'CREATE')) and (event['resourceType'] == 'USER')):
        # only time we will consider creating the user via SCIM is if we see that an attribute
        # has been set for them. If user is created with attributes in one operation via API
        # we'll handle that as well as if the user is created then attributes added later
        check_create_update_user_via_scim(user=json.loads(event['representation']),kc_client=kcclient)

def check_create_update_user_via_scim(user,kc_client):
    # create SCIM compliant user object in AWS IAM ID center if user has appropriate attribute
    # per AWS SCIM docs, The givenName, familyName, userName, and displayName fields are required.
    if('attributes' not in user.keys()):
        pprint.pprint('user not created in scim, missing attributes')
        return
    else:
        pprint.pprint(f"provisioning user {user} via scim")
    attributes = user['attributes']
    # we might be here because the user was just created then updated, or they might exist already
    # and the attributes assigning them to AWS were removed. If they don't have an AWS ID then they should be created
    if(('awsenabled' in attributes) and ('awsid' not in attributes)): 
        if(attributes['awsenabled'][0] == 'true'):
            userobj = {}
            nameobj = {}
            nameobj['givenName'] = user['firstName']
            nameobj['familyName'] = user['lastName']
            userobj['userName'] = user['username']
            userobj['name'] = nameobj
            userobj['displayName'] = user['username']
            userobj['active'] = True
            userobj['externalId'] = user['id']
            emails = []
            emails.append(
                    {
                        "value":user['email'],
                        "type":'work',
                        "primary":True
                    }
                )
            userobj['emails'] = emails

            client_id=os.environ.get('SCIM_TOKEN_CLIENT_ID')
            scim_access_token=os.environ.get('SCIM_ACCESS_TOKEN')
            scim_endpoint=os.environ.get('SCIM_ENDPOINT')
            client = BackendApplicationClient(client_id=client_id)
            scimsession = OAuth2Session(client=client)
            scimsession.access_token=scim_access_token
            scimsession.token=scim_access_token
            resp = scimsession.post(f"{scim_endpoint}Users",json=userobj)
            # We might also be in this state because an admin accidentally deleted the awsid attribute
            # value after the user was enabled in keycloak and provisioned. So if we get a duplicate 
            # record error from SCIM, let's fetch the AWS ID matching our user and update the user
            # record in keycloak with a new awsid attribute
            awsuserobj = resp.json()
            if(('status' in awsuserobj.keys()) and (awsuserobj['status'] == '409')):
                filterexpr = f"filter=externalId eq \"{userobj['externalId']}\""
                resp = scimsession.get(f"{scim_endpoint}Users?{filterexpr}")
                result = resp.json()
                if(result['totalResults'] > 0):
                    for resource in result['Resources']:
                        resp = scimsession.get(f"{scim_endpoint}Users/{resource['id']}")
                        tmpuserobj = resp.json()
                        attributes['awsid'] = tmpuserobj['id']
                        userattr = {
                            'attributes': attributes
                        }
                resp = kc_client.put(f"https://keycloak.wgoulet.com/admin/realms/Infra/users/{user['id']}",json=userattr)
            else:
                pprint.pprint(resp.json())
                # Store the AWS ID value as an attribute for the user; we'll need this
                # to find the user in AWS IAM ID center later for update operations
                attributes['awsid'] = awsuserobj['id']
                userattr = {
                    'attributes': attributes
                }
                resp = kc_client.put(f"https://keycloak.wgoulet.com/admin/realms/Infra/users/{user['id']}",json=userattr)
    elif('awsid' in attributes): 
        if(('awsenabled' not in attributes) or (attributes['awsenabled'][0] != 'true')):
            # remove the user from AWS via scim
            client_id=os.environ.get('SCIM_TOKEN_CLIENT_ID')
            scim_access_token=os.environ.get('SCIM_ACCESS_TOKEN')
            scim_endpoint=os.environ.get('SCIM_ENDPOINT')
            client = BackendApplicationClient(client_id=client_id)
            scimsession = OAuth2Session(client=client)
            scimsession.access_token=scim_access_token
            scimsession.token=scim_access_token
            resp = scimsession.delete(f"{scim_endpoint}Users/{attributes['awsid'][0]}")
            # since we are deleting the user via scim lets clear the awsid attribute from
            # the user's account in kc
            del attributes['awsid']
            userattr = {
                'attributes': attributes
            }
            resp = kc_client.put(f"https://keycloak.wgoulet.com/admin/realms/Infra/users/{user['id']}",json=userattr)
            pprint.pprint(f"User {user['id']} removed from AWS")
    
        
def assign_user_to_group_via_scim(event,kc_client):
    client_id=os.environ.get('SCIM_TOKEN_CLIENT_ID')
    scim_access_token=os.environ.get('SCIM_ACCESS_TOKEN')
    scim_endpoint=os.environ.get('SCIM_ENDPOINT')
    client = BackendApplicationClient(client_id=client_id)
    scimsession = OAuth2Session(client=client)
    scimsession.access_token=scim_access_token
    scimsession.token=scim_access_token
    (ulabel,userId,glabel,groupId) = event['resourcePath'].split('/')  
    resp = kc_client.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/users/{userId}")
    userinfo = resp.json()
    resp = kc_client.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/groups/{groupId}")
    groupinfo = resp.json()
    userinfo
    groupinfo
    patchop = {
        'schemas':["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        'Operations':[
            {
                'op':'add',
                'path':"members",
                'value':[
                    {'value':userinfo['attributes']['awsid'][0]}
                ]
            }
        ]
    }
    resp = scimsession.patch(f"{scim_endpoint}Groups/{groupinfo['attributes']['awsid'][0]}",json=patchop)
    resp
    
def create_group_via_scim(group,kc_client):
        # create SCIM compliant group object
        # per AWS SCIM docs, The displayName fields are required.

        groupobj = {}
        groupobj['externalId'] = group['id']
        groupobj['displayName'] = group['name']

        client_id=os.environ.get('SCIM_TOKEN_CLIENT_ID')
        scim_access_token=os.environ.get('SCIM_ACCESS_TOKEN')
        scim_endpoint=os.environ.get('SCIM_ENDPOINT')
        client = BackendApplicationClient(client_id=client_id)
        scimsession = OAuth2Session(client=client)
        scimsession.access_token=scim_access_token
        scimsession.token=scim_access_token
        resp = scimsession.post(f"{scim_endpoint}Groups",json=groupobj)
        awsgroupobj = resp.json()
        pprint.pprint(resp.json())
        # Store the AWS ID value as an attribute for the user; we'll need this
        # to find the user in AWS IAM ID center later for update operations
        groupattr = {
            'name':group['name'],
            'attributes':{
                "awsid":[awsgroupobj['id']]
            } 
        }
        resp = kc_client.put(f"https://keycloak.wgoulet.com/admin/realms/Infra/groups/{group['id']}",json=groupattr)
        resp
    

def read_mqueue():
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
    # decode into json objects
    try:
        body
        devent = json.loads(body.decode("utf-8"))
        if('opType' in devent): 
            if(devent['opType'] != 'DELETE'):
                op = devent['opType']
                representation = json.loads(devent['representation'])
                print(op)
                print(representation)
                process_event(devent)
            else: 
                username = devent['userName']
                attributes = devent['attributes']
                op = devent['opType']
                userId = devent['userId']
                print(op)
                print(username)
                print(userId)
                print(attributes)
                process_event(devent)
    except:
        print(f"Error processing {body}")
    
read_mqueue()