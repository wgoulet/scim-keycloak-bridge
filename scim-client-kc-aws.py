from io import StringIO
import select
import csv
from systemd import journal
from datetime import datetime, timedelta
import json
import pprint
import os
from pubsub import pub
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

def listen_kc_event(event):
    if('operationType' in event.keys()):
        process_event(event)

def process_event(event):
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    token_url = os.environ.get('TOKEN_URL')
    client = BackendApplicationClient(client_id=client_id)
    kcclient = OAuth2Session(client=client)
    token = kcclient.fetch_token(token_url=token_url,client_id=client_id,client_secret=client_secret)
    if((event['operationType'] == 'CREATE') and (event['resourceType'] == 'USER')):
        resp = kcclient.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/{event['resourcePath']}")
        create_user_via_scim(user=resp.json(),kc_client=kcclient)
    elif((event['operationType'] == 'CREATE') and (event['resourceType']) == 'GROUP'):
        resp = kcclient.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/{event['resourcePath']}")
        create_group_via_scim(group=resp.json(),kc_client=kcclient)
    elif((event['operationType'] == 'CREATE') and (event['resourceType']) == 'GROUP_MEMBERSHIP'):
        assign_user_to_group_via_scim(event=event,kc_client=kcclient)

        
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
    

def create_user_via_scim(user,kc_client):
    # create SCIM compliant user object
    # per AWS SCIM docs, The givenName, familyName, userName, and displayName fields are required.

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
    awsuserobj = resp.json()
    pprint.pprint(resp.json())
    # Store the AWS ID value as an attribute for the user; we'll need this
    # to find the user in AWS IAM ID center later for update operations
    userattr = {
        'attributes':{
            "awsid":[awsuserobj['id']]
        } 
    }
    resp = kc_client.put(f"https://keycloak.wgoulet.com/admin/realms/Infra/users/{user['id']}",json=userattr)

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
    

def read_journald_logs(since=None, until=None, unit=None):
    # Read log entries from journald that are created by keycloak. 
    # This code assumes the logs are written to journald in json format
    reader = journal.Reader()
    reader.seek_tail()
    # Poll for events; whenver we get notified that new journald entries have
    # been created, look for entries from keycloak that are generated for admin events
    # and convert them into objects that we can feed into a SCIM client.
    poller = select.poll()
    poller.register(reader,reader.get_events())
    while(True):
        poller.poll()
        for entry in reader:
            if('SYSLOG_IDENTIFIER' in entry.keys()):
                if entry['SYSLOG_IDENTIFIER'] == 'kc.sh':
                    try:
                        obj = json.loads(entry['MESSAGE'])
                        if(obj['loggerName'] == 'org.keycloak.events'):
                            # The fields of interest we need to generate scim events
                            # are encoded as a list of key/value pairs with event details
                            # so we'll read them in and convert them into json objects to make
                            # it easier to extract the fields we'll need to generate SCIM
                            # requests.
                            with StringIO(obj['message']) as input_file:
                                csv_reader = csv.reader(input_file, delimiter=",", quotechar='"')
                                for row in csv_reader:
                                    logobject = {}
                                    for entry in row:
                                        (key,value) = entry.split('=')
                                        logobject[key.strip()] = value.strip()
                                    # Publish an event with the created object when we find a keycloak event of interest
                                    pub.sendMessage('rootTopic',event=logobject)
                    except json.decoder.JSONDecodeError as err:
                        print("Not in json format")
                        print(err.doc)
                        continue

pub.subscribe(listen_kc_event,'rootTopic')
read_journald_logs()