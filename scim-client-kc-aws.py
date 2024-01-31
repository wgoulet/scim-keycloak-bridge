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
from threading import Thread

# TODO: Consider implementing a job that will sweep through all users
# and make sure that their attributes assigning them to AWS are set correctly
# spefically handling the case where AWS IDs are removed from KC user attributes

def reconciliation_job(args):
    # Setup connections to keycloak and AWS
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    token_url = os.environ.get('TOKEN_URL')
    client = BackendApplicationClient(client_id=client_id)
    kcclient = OAuth2Session(client=client)
    token = kcclient.fetch_token(token_url=token_url,client_id=client_id,client_secret=client_secret)
    scim_client_id=os.environ.get('SCIM_TOKEN_CLIENT_ID')
    scim_access_token=os.environ.get('SCIM_ACCESS_TOKEN')
    scim_endpoint=os.environ.get('SCIM_ENDPOINT')
    scim_client = BackendApplicationClient(client_id=scim_client_id)
    scimsession = OAuth2Session(client=scim_client)
    scimsession.access_token=scim_access_token
    scimsession.token=scim_access_token
    while(True):
        pprint.pprint(f"Executing cleanup job!")
        listusers = []
        time.sleep(1)
        # Get list of KC users and for each one, query AWS to see if the kc id matches the external ID
        # AND if the user does NOT have the awsenabled and awsid attributes set, delete the user from 
        # AWS. 
        resp = kcclient.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/users")
        users = resp.json()
        for user in users:
            if('attributes' in user.keys()):
                attributes = user['attributes']
                if(('awsid' not in attributes) or  
                    (('awsenabled' not in attributes) or (attributes['awsenabled'][0] != 'true'))):
                    id = user['id']
                    listusers.append(id)
            else: # Handle case where user has no attributes at all
                    id = user['id']
                    listusers.append(id)
                    
        for id in listusers:
            filterexpr = f"filter=externalId eq \"{id}\""
            resp = scimsession.get(f"{scim_endpoint}Users?{filterexpr}")
            result = resp.json()
            if(result['totalResults'] > 0):
                for resource in result['Resources']:
                    pprint.pprint(f"Will delete user {resource['userName']} from AWS via scim!")
                    resp = scimsession.delete(f"{scim_endpoint}Users/{resource['id']}")


def process_event(event):
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    token_url = os.environ.get('TOKEN_URL')
    client = BackendApplicationClient(client_id=client_id)
    kcclient = OAuth2Session(client=client)
    token = kcclient.fetch_token(token_url=token_url,client_id=client_id,client_secret=client_secret)
    if((event['operationType'] == 'CREATE') and (event['resourceType']) == 'GROUP'):
        resp = kcclient.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/{event['resourcePath']}")
        create_group_via_scim(group=resp.json(),kc_client=kcclient)
    elif((event['operationType'] == 'CREATE') and (event['resourceType']) == 'GROUP_MEMBERSHIP'):
        assign_user_to_group_via_scim(event=event,kc_client=kcclient)
    if(((event['operationType'] == 'UPDATE') or (event['operationType'] == 'CREATE')) and (event['resourceType'] == 'USER')):
        # only time we will consider creating the user via SCIM is if we see that an attribute
        # has been set for them. If user is created with attributes in one operation via API
        # we'll handle that as well as if the user is created then attributes added later
        resp = kcclient.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/{event['resourcePath']}")
        check_create_user_via_scim(user=resp.json(),kc_client=kcclient)

def check_create_user_via_scim(user,kc_client):
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
            awsuserobj = resp.json()
            pprint.pprint(resp.json())
            # Store the AWS ID value as an attribute for the user; we'll need this
            # to find the user in AWS IAM ID center later for update operations
            attributes['awsid'] = awsuserobj['id']
            userattr = {
                'attributes': attributes
            }
            resp = kc_client.put(f"https://keycloak.wgoulet.com/admin/realms/Infra/users/{user['id']}",json=userattr)
            user
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
                                if('operationType' in logobject.keys()):
                                    process_event(logobject)
                    except json.decoder.JSONDecodeError as err:
                        print("Not in json format")
                        print(err.doc)
                        continue

t = Thread(target=reconciliation_job,args=("run",))
t.start()
read_journald_logs()