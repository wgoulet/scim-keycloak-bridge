# Keycloack - AWS Identity Center SCIM Integration

Keycloak Event Listener provider and SCIM client to allow Keycloak users/groups to be provisioned to AWS IAM Identity Center.

## Description

This project implements a Keycloak event listener and a basic SCIM client that listens to Keycloak events related to user/group creation, modification and deletion. When it detects those events, it generates a SCIM request against an AWS IAM Identity Center instance to update user/group assignments. This allows you to enforce lifecycle management operations in AWS IAM Identity Center in response to lifecycle operations in your Keycloak IdP.

## Architecture

To keep the system as realtime as possible (create/modify/delete users/groups in AWS should occur as soon as possible when those operations are performed in KeyCloak), the system relies on events that are generated by KeyCloak for user/group lifecycle events. This is done by a custom EventListener SPI that is deployed in Keycloack as an additional event logging provider (scim-event-listener). The scim-event-listener listens for admin events as well as registers itself as an event handler for deletion transactions. Events that are received are then published to a RabbitMQ message queue where the events are then consumed by a Python program that performs the actual SCIM operations.

This architecture was designed to decouple application logic from the EventListener provider so that it doesn't need to be aware of the 3rd party applications (in this case AWS) that is being provisioned to from Keycloak.

## Getting Started

### Dependencies

* Python3.9 or greater
* Keycloak server instance (tested on v 23.0.4)
* RabbitMQ instance
* AWS IAM Identity Center

### Installing

For the beta release, installation is manual.

#### Prerequisities

Install RabbitMQ for your Linux distribution; the beta was tested on Aamazon Linux 2023: https://www.rabbitmq.com/install-rpm.html

Install and configure Keycloak; the beta was tested on a bare metal OpenJDK installation: https://www.keycloak.org/getting-started/getting-started-zip

Configure Keycloak as an external SAML identity provider with AWS, see https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-identity-source-idp.html.

#### Installing the scim-event-listener
* Clone this repo on your server running Keycloak 23.0.4 or greater (tested on Amazon Linux 2023)
* Download the scim-event-listener from the releases link: https://github.com/wgoulet/scim-keycloak-bridge/releases/download/v0.0.1-beta/scim-event-listener.jar (or alternatively, build it from source)
* Copy scim-event-listener.jar to the /providers directory where Keycloak is installed (e.g. if keycloak is installed in /usr/local/, the path might be /usr/local/keycloak-23.0.4/providers)
* Setup environment variables that will contain URLs/tokens/credentials for accessing the Keycloak instance, AWS IAM Identity Center and the rabbitmq instance that events will be published to. See example-environment-file; suggest including this file in an ```EnvironmentFile``` directive in the systemd unit file used to define the keycloak service (if your Keycloak installation creates a systemd service or if you create one manually.)
* Activate the provider by executing the ```kc.sh build``` command.
* Restart the Keycloak instance.
* Log into Keycloak as an administrator. For each realm you want to enable the provider on, navigate to Realm settings, select Events, select the Event Listener tab and select 'scim-event-provider' to enable it.

#### Installing the scim_client_kc_aws.py program
* Create a service user that will run the program.
* From the location where the repo was cloned, create a virtualenv.
* Activate the virtualenv, then install the dependencies ```pip3 -install requirements.txt```
* Note the path to the virtualenv
* Export necessary environment variables; see example-environment-file.
* Execute the script with the virtualenv environment ```/path/to/virtualenv/bin/python scim_client_kc_aws.py```
* Alternatiely, to run the script automatically, consider the approach described here: https://github.com/torfsen/python-systemd-tutorial/tree/master. If you do elect to run the script via systemd, you can also define an ```EnvironmentFile``` directive that includes the required environment variable definitions; see example-environment-file. See the example scim_client_kc_aws_py.service file.

#### Testing the setup

Python unit tests are included in the test_scim_aws_client.py script. To run the tests, create a .env file that contains the environment variable definitions as defined in example-environment-file. The beta release uses the pytest framework; you can execute the tests with ```pytest``` from within the virtualenv. The tests create and destroy users/groups in Keycloak and AWS IAM Identity Center.

### Usage

The SCIM client uses attributes associated with users and groups to determine if it should take action (provision/deprovision/change user/groups). To set a user or group up to be provisioned in AWS, add this attribute to the user/group in Keycloak:
```
awsenabled
```

and give it a value of 'true'. When the SCIM client receives an event from the SCIM Event Listener, it will check if this attribute is present and if it is, will create the usr/group in AWS and store the AWS ID for the user/group in a new attribute called 'awsid'.

Supported operations include:
- Removing user/groups from AWS by deleting the 'awsenabled' attribute
- Adding/removing AWS provisioned users from AWS provisioned groups
- Automatically removing users/groups provisioned to AWS when the users/groups are deleted from Keycloak.

## Help

File issues in the Github issue tracker; I appreciate any feedback and welcome ideas for improving this project.

## Authors

Contributors names and contact info
Walter Goulet


## Version History

* 0.1
    * Initial Release

## License

This project is licensed under the MIT License - see the LICENSE.md file for details

