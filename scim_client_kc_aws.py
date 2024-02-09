
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
    if(((event['opType'] == 'CREATE') or (event['opType'] == 'UPDATE')) and (event['resourceType']) == 'GROUP'):
        return check_create_update_group_via_scim(optype=event['opType'],group=json.loads(event['representation']),kc_client=kcclient)
    #elif((event['opType'] == 'CREATE') and (event['resourceType']) == 'GROUP_MEMBERSHIP'):
    elif((event['resourceType']) == 'GROUP_MEMBERSHIP'):
        return update_user_group_rel_via_scim(event=event,kc_client=kcclient)
    if(((event['opType'] == 'UPDATE') or (event['opType'] == 'CREATE')) and (event['resourceType'] == 'USER')):
        # only time we will consider creating the user via SCIM is if we see that an attribute
        # has been set for them. If user is created with attributes in one operation via API
        # we'll handle that as well as if the user is created then attributes added later
        return check_create_update_user_via_scim(user=json.loads(event['representation']),kc_client=kcclient)
    if((event['opType']) == 'DELETE' and (event['resourceType'] == 'GROUP')):
        group_obj = {}
        group_obj['id'] = event['id']
        group_obj['attributes'] = event['attributes']
        return delete_group_via_scim(groupobj=group_obj,kc_client=kcclient)
    if((event['opType']) == 'DELETE' and (event['resourceType'] == 'USER')):
        user_obj = {}
        user_obj['id'] = event['userId']
        user_obj['attributes'] = event['attributes']
        return delete_user_via_scim(userobj=user_obj,kc_client=kcclient)

def delete_group_via_scim(groupobj,kc_client):
    client_id=os.environ.get('SCIM_TOKEN_CLIENT_ID')
    scim_access_token=os.environ.get('SCIM_ACCESS_TOKEN')
    scim_endpoint=os.environ.get('SCIM_ENDPOINT')
    client = BackendApplicationClient(client_id=client_id)
    scimsession = OAuth2Session(client=client)
    scimsession.access_token=scim_access_token
    scimsession.token=scim_access_token
    # Check if group contains an awsid first; if so use it to 
    # delete the group
    if('awsid' in groupobj['attributes']):
        awsid = groupobj['attributes']['awsid'][0]
        resp = scimsession.delete(f"{scim_endpoint}Groups/{awsid}")
        return resp
    
def delete_user_via_scim(userobj,kc_client):
    client_id=os.environ.get('SCIM_TOKEN_CLIENT_ID')
    scim_access_token=os.environ.get('SCIM_ACCESS_TOKEN')
    scim_endpoint=os.environ.get('SCIM_ENDPOINT')
    client = BackendApplicationClient(client_id=client_id)
    scimsession = OAuth2Session(client=client)
    scimsession.access_token=scim_access_token
    scimsession.token=scim_access_token
    # Check if user contains an awsid first; if so use it to 
    # delete the user
    if('awsid' in userobj['attributes']):
        awsid = userobj['attributes']['awsid']
        resp = scimsession.delete(f"{scim_endpoint}Users/{awsid}")
        return resp
    else:
        return f"Unable to delete user {userobj['id']} missing attribute"

def check_create_update_user_via_scim(user,kc_client):
    # create SCIM compliant user object in AWS IAM ID center if user has appropriate attribute
    # per AWS SCIM docs, The givenName, familyName, userName, and displayName fields are required.
    if('attributes' not in user.keys()):
        result = f"User {user['username']} not created in scim, missing attributes"
        pprint.pprint(result)
        return result
    else:
        pprint.pprint(f"provisioning user {user} via scim")
    kc_base_url = os.environ.get('KC_BASE_URL')
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
                resp = kc_client.put(f"{kc_base_url}/admin/realms/Infra/users/{user['id']}",json=userattr)
                return resp
            else:
                pprint.pprint(resp.json())
                # Store the AWS ID value as an attribute for the user; we'll need this
                # to find the user in AWS IAM ID center later for update operations
                attributes['awsid'] = awsuserobj['id']
                userattr = {
                    'attributes': attributes
                }
                resp = kc_client.put(f"{kc_base_url}/admin/realms/Infra/users/{user['id']}",json=userattr)
                return resp
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
            resp = kc_client.put(f"{kc_base_url}/admin/realms/Infra/users/{user['id']}",json=userattr)
            pprint.pprint(f"User {user['id']} removed from AWS")
            return resp
    
        
def update_user_group_rel_via_scim(event,kc_client):
    kc_base_url = os.environ.get('KC_BASE_URL')
    client_id=os.environ.get('SCIM_TOKEN_CLIENT_ID')
    scim_access_token=os.environ.get('SCIM_ACCESS_TOKEN')
    scim_endpoint=os.environ.get('SCIM_ENDPOINT')
    client = BackendApplicationClient(client_id=client_id)
    scimsession = OAuth2Session(client=client)
    scimsession.access_token=scim_access_token
    scimsession.token=scim_access_token
    (ulabel,userId,glabel,groupId) = event['resourcePath'].split('/')  
    resp = kc_client.get(f"{kc_base_url}/admin/realms/Infra/users/{userId}")
    userinfo = resp.json()
    resp = kc_client.get(f"{kc_base_url}/admin/realms/Infra/groups/{groupId}")
    groupinfo = resp.json()
    userinfo
    groupinfo
    if(event['opType'] == 'CREATE'):
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
    elif(event['opType'] == 'DELETE'):
        patchop = {
            'schemas':["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            'Operations':[
                {
                    'op':'REMOVE',
                    'path':"members",
                    'value':[
                        {'value':userinfo['attributes']['awsid'][0]}
                    ]
                }
            ]
        }
    resp = scimsession.patch(f"{scim_endpoint}Groups/{groupinfo['attributes']['awsid'][0]}",json=patchop)
    return resp
    
def check_create_update_group_via_scim(optype,group,kc_client):
        # create SCIM compliant group object if we have the awsenabled attribute
        # set on the group.
        # per AWS SCIM docs, The displayName fields are required.
        if('awsenabled' not in group['attributes']):
            result = f"Group {group['name']} not created in scim, missing attribute"
            pprint.pprint(result)
            return result
        elif(group['attributes']['awsenabled'][0] != 'true'):
            return
        # To avoid an infinite loop, if we see that the group in question already
        # has an AWS ID, we know it has been provisioned so stop. Otherwise we'll
        # keep updating the group here, triggering an update event and firing this event
        # again
        elif('awsid' in group['attributes']):
            return f"Not processing {group['name']} since awsid attribute already found"
        groupobj = {}
        groupobj['externalId'] = group['id']
        groupobj['displayName'] = group['name']
        attributes = group['attributes']
        kc_base_url = os.environ.get('KC_BASE_URL')
        client_id=os.environ.get('SCIM_TOKEN_CLIENT_ID')
        scim_access_token=os.environ.get('SCIM_ACCESS_TOKEN')
        scim_endpoint=os.environ.get('SCIM_ENDPOINT')
        client = BackendApplicationClient(client_id=client_id)
        scimsession = OAuth2Session(client=client)
        scimsession.access_token=scim_access_token
        scimsession.token=scim_access_token
        resp = scimsession.post(f"{scim_endpoint}Groups",json=groupobj)
        awsgroupobj = resp.json()
        if(('status' in awsgroupobj.keys()) and (awsgroupobj['status'] == '409')):
            filterexpr = f"filter=externalId eq \"{groupobj['externalId']}\""
            resp = scimsession.get(f"{scim_endpoint}Groups?{filterexpr}")
            result = resp.json()
            if(result['totalResults'] > 0):
                for resource in result['Resources']:
                    resp = scimsession.get(f"{scim_endpoint}Groups/{resource['id']}")
                    tmpgroupobj = resp.json()
                    # Store the AWS ID value as an attribute for the group; we'll need this
                    # to find the group in AWS IAM ID center later for update operations
                    attributes['awsid'] = [tmpgroupobj['id']]
                group['attributes'] = attributes
                resp = kc_client.put(f"{kc_base_url}/admin/realms/Infra/groups/{group['id']}",json=group)
                return resp
        else:
            pprint.pprint(resp.json())
            awsgroupobj = resp.json()
            attributes['awsid'] = [awsgroupobj['id']]
            group['attributes'] = attributes
            resp = kc_client.put(f"{kc_base_url}/admin/realms/Infra/groups/{group['id']}",json=group)
            return resp

def main():
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
            op = devent['opType']
            process_event(devent)
    except Exception as err:
        print(f"Exception {err} when processing {body}")
    
if __name__ == "__main__":
    main()