import scim_client_kc_aws
import pytest
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
from dotenv import load_dotenv


@pytest.fixture(scope="module")
def setup_connections():
    load_dotenv()
    connections = {}
    client_id=os.environ.get('SCIM_TOKEN_CLIENT_ID')
    scim_access_token=os.environ.get('SCIM_ACCESS_TOKEN')
    scim_endpoint=os.environ.get('SCIM_ENDPOINT')
    client = BackendApplicationClient(client_id=client_id)
    scimsession = OAuth2Session(client=client)
    scimsession.access_token=scim_access_token
    scimsession.token=scim_access_token
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    token_url = os.environ.get('TOKEN_URL')
    client = BackendApplicationClient(client_id=client_id)
    kcclient = OAuth2Session(client=client)
    token = kcclient.fetch_token(token_url=token_url,client_id=client_id,client_secret=client_secret)
    connections = {"kc_client":kcclient,"scim_client":scimsession,"scim_endpoint":scim_endpoint}
    return connections

def test_check_create_update_group_via_scim(setup_connections):
    connections = setup_connections
    kc_client = connections['kc_client']
    scim_client = connections['scim_client']
    scim_endpoint = connections['scim_endpoint']
    # Create a group in KC
    groupobj = {}
    groupobj['name'] = "pytestgroup"
    attributes = {"awsenabled":["true"]}
    groupobj['attributes'] = attributes
    resp = kc_client.post("https://keycloak.wgoulet.com/admin/realms/Infra/groups",json=groupobj)
    # Fetch full group details to send to SCIM method
    resp = kc_client.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/groups?search={groupobj['name']}&briefRepresentation=false")
    groupobj = resp.json()
    # Provision group
    scim_client_kc_aws.check_create_update_group_via_scim(optype="CREATE",group=groupobj[0],kc_client=kc_client)
    
    # Make sure group is actually provisioned
    # we'll do this by using the AWS ID that stored on the group object to fetch the group from AWS SCIM
    resp = kc_client.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/groups/{groupobj[0]['id']}")
    awsid = resp.json()['attributes']['awsid'][0]
    resp = scim_client.get(f"{scim_endpoint}Groups/{awsid}")
    assert resp.status_code == 200
    assert resp.json()['displayName'] == "pytestgroup"

    # Delete group from AWS then KC
    resp = scim_client.delete(f"{scim_endpoint}Groups/{awsid}")
    assert resp.status_code == 204
    resp = kc_client.delete(f"https://keycloak.wgoulet.com/admin/realms/Infra/groups/{groupobj[0]['id']}")
    assert resp.status_code == 204

def test_delete_group_via_scim(setup_connections):
    connections = setup_connections
    kc_client = connections['kc_client']
    scim_client = connections['scim_client']
    scim_endpoint = connections['scim_endpoint']
    groupobj = {}
    groupobj['name'] = "pytest"
    attributes = {"awsenabled":["true"]}
    groupobj['attributes'] = attributes
    resp = kc_client.post("https://keycloak.wgoulet.com/admin/realms/Infra/groups",json=groupobj)
    resp
    # Fetch full group details to send to SCIM method
    resp = kc_client.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/groups?search={groupobj['name']}&briefRepresentation=false")
    groupobj = resp.json()
    # Provision group
    groupobj
    scim_client_kc_aws.check_create_update_group_via_scim(optype='CREATE',group=groupobj[0],kc_client=kc_client)

    # Make sure group is actually provisioned
    resp = kc_client.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/groups/{groupobj[0]['id']}")
    awsid = resp.json()['attributes']['awsid'][0]
    resp = scim_client.get(f"{scim_endpoint}Groups/{awsid}")
    assert resp.status_code == 200
    assert resp.json()['displayName'] == "pytest" 
    
    # Delete group in SCIM
    resp = scim_client_kc_aws.delete_group_via_scim(groupobj=groupobj[0],kc_client=kc_client)

    # Verify group no longer found in AWS
    resp = scim_client.get(f"{scim_endpoint}Groups/{awsid}")
    assert resp.status_code == 404

    # delete group in KC
    resp = kc_client.delete(f"https://keycloak.wgoulet.com/admin/realms/Infra/groups/{groupobj[0]['id']}")
    assert resp.status_code == 204

def test_delete_user_via_scim(setup_connections):
    connections = setup_connections
    kc_client = connections['kc_client']
    scim_client = connections['scim_client']
    scim_endpoint = connections['scim_endpoint']
    userobj = {}
    userobj['username'] = "pytest@test.com"
    userobj['email'] = "pytest@test.com"
    userobj['firstName'] = "py"
    userobj['lastName'] = "test"
    attributes = {"awsenabled":["true"]}
    userobj['attributes'] = attributes
    resp = kc_client.post("https://keycloak.wgoulet.com/admin/realms/Infra/users",json=userobj)
    resp
    # Fetch full user details to send to SCIM method
    resp = kc_client.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/users?search={userobj['username']}&briefRepresentation=false")
    userobj = resp.json()
    # Provision user
    userobj
    scim_client_kc_aws.check_create_update_user_via_scim(user=userobj[0],kc_client=kc_client)

    # Make sure user is actually provisioned
    resp = kc_client.get(f"https://keycloak.wgoulet.com/admin/realms/Infra/users/{userobj[0]['id']}")
    awsid = resp.json()['attributes']['awsid'][0]
    resp = scim_client.get(f"{scim_endpoint}Users/{awsid}")
    assert resp.status_code == 200
    assert resp.json()['displayName'] == "pytest@test.com" 
    
    # Delete user in SCIM
    resp = scim_client_kc_aws.delete_user_via_scim(userobj=userobj[0],kc_client=kc_client)

    # Verify user no longer found in AWS
    resp = scim_client.get(f"{scim_endpoint}Users/{awsid}")
    assert resp.status_code == 404

    # delete user in KC
    resp = kc_client.delete(f"https://keycloak.wgoulet.com/admin/realms/Infra/users/{userobj[0]['id']}")
    assert resp.status_code == 204