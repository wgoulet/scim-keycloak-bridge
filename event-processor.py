from io import StringIO
import select
import csv
from systemd import journal
from datetime import datetime, timedelta
import json

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
    logobjects = []
    while(True):
        poller.poll()
        #event = reader.get_next()
        for entry in reader:
            if('SYSLOG_IDENTIFIER' in entry.keys()):
                #print(entry['SYSLOG_IDENTIFIER'])
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
                                        logobject[key] = value
                                    logobjects.append(logobject)
                    except json.decoder.JSONDecodeError as err:
                        err
                        print("Not in json format")
                        print(err.doc)
                        continue
        logobjects
read_journald_logs()