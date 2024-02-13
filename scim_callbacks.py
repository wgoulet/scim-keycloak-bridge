# These functions are callback functions executed in response to lifecycle events
# performed by scim_client_kc_aws.py. Replace the default null implementations
# with your own implementation if you want to perform additional processing in downstream
# AWS IAM Identity Center after the operation is complete. Main use case for the call backs
# is to assign users/groups specific SSO permission sets after the provisioning operation
# is complete.

import boto3
import os

def create_update_user(userobj: dict, attributes: list):
    # Comment out this line to activate this callback
    return None
    # In this example assume that AWS Python SDK is using ec2 instance
    # roles auth and that ec2 IAM role has sufficient permissions to list
    # and update permission sets/assignments
    awsacctid = os.environ.get('AWS_ACCOUNT_ID')
    awsiamidcarn = os.environ.get('AWS_IAM_IDC_ARN')
    awsiamidcregion = os.environ.get('AWS_IAM_IDC_REGION')
    ssocli = boto3.client('sso-admin',region_name=awsiamidcregion)
    resp = ssocli.list_permission_sets(
        InstanceArn = awsiamidcarn
    )
    # In this example, we will decide which permission to assign
    # the user based on value of an attribute called 'awsadmin'
    for ps in resp['PermissionSets']:
        psdetails = ssocli.describe_permission_set(
            InstanceArn = awsiamidcarn,
            PermissionSetArn = ps
        )
        psdetails
        for attr in attributes:
            if(attr == 'awsssopermset'):
                if(attributes[attr][0] == psdetails['PermissionSet']['Name']):
                    resp = ssocli.create_account_assignment(
                        InstanceArn = awsiamidcarn,
                        PermissionSetArn = ps,
                        PrincipalId = attributes['awsid'],
                        PrincipalType = 'USER',
                        TargetId = awsacctid,
                        TargetType = 'AWS_ACCOUNT'
                    )