# Keycloack - AWS Identity Center SCIM Client

SCIM client to allow Keycloak users/groups to be provisioned to AWS IAM Identity Center

## Description

This project implements a basic SCIM client that listens to Keycloak events related to user/group creation, modification and deletion. When it detects those events, it generates a SCIM request against an AWS IAM Identity Center instance to update user/group assignments. This allows you to enforce lifecycle management operations in AWS IAM Identity Center in response to lifecycle operations in your Keycloak IdP.

## Getting Started

### Dependencies

* Python3.9 or greater
* Keycloak server instance (tested on v 23.0.4)
* AWS IAM Identity Center

### Installing

* Clone this repo to a suitable location on your Keycloak server instance
* Configure your Keycloak server to start with debug logging enabled for Keycloak events (necessary as the client polls for log events to look for changes)

### Executing program

* Create a virtualenv for the program
* Launch it with the python interpreter installed in the virtualenv
```
code blocks for commands
```

## Help

Any advise for common problems or issues.
```
command to run if program contains helper info
```

## Authors

Contributors names and contact info
Walter Goulet


## Version History

* 0.1
    * Initial Release

## License

This project is licensed under the MIT License - see the LICENSE.md file for details

## Acknowledgments
