package com.wgoulet;

import java.io.IOException;
import java.util.concurrent.TimeoutException;

import org.jboss.logging.Logger;
import org.keycloak.events.Event;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventType;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.events.admin.OperationType;
import org.keycloak.events.admin.ResourceType;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmProvider;
import org.keycloak.models.UserModel;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.rabbitmq.client.*;

public class SCIMEventListenerProvider implements EventListenerProvider {

    private static final Logger log = Logger.getLogger(SCIMEventListenerProvider.class);

    private final KeycloakSession session;
    private final RealmProvider model;
    private Channel channel;

    public SCIMEventListenerProvider(KeycloakSession session) {
        this.session = session;
        this.model = session.realms();
        String rabbitmqpwd = System.getenv("RABBITMQPWD");
        String rabbitmquname = System.getenv("RABBITMQUNAME");
        String rabbitmqvhost = System.getenv("RABBITMQVHOST");
        String rabbitmqhost = System.getenv("RABBITMQHOST");
        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost(rabbitmqhost);
        Connection connection;
            factory.setUsername(rabbitmquname);
            factory.setPassword(rabbitmqpwd);
            factory.setVirtualHost(rabbitmqvhost);
            try {
                connection = factory.newConnection();
                this.channel = connection.createChannel();
                channel.queueDeclare("scimbridge", false, false, false, null);
            } catch (IOException | TimeoutException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            }
    }

    @Override
    public void onEvent(Event event) {

    }

    @Override
    public void onEvent(AdminEvent adminEvent, boolean b) {
        try {
            DetailAdminEvent dEvent = new DetailAdminEvent(adminEvent);
            ObjectMapper mapper = new ObjectMapper();
            String sendString = mapper.writeValueAsString(dEvent.getEventRepresentation());
            // We won't log delete events here because we don't have any context
            // about the user/group to provide. Deletions are handled in the provider factory
            // instead.
            if(adminEvent.getOperationType() != OperationType.DELETE) {
                channel.basicPublish("", "scimbridge", null,sendString.getBytes());
            }
            // On the other hand, group membership leave events are standard AdminEvents so send those along
            if((adminEvent.getResourceType() == ResourceType.GROUP_MEMBERSHIP) && 
                (adminEvent.getOperationType() == OperationType.DELETE)){
                channel.basicPublish("", "scimbridge", null,sendString.getBytes());
            }
        } catch (IOException e) {
            // TODO Auto-generated catch block
            System.out.println("Fatal error!");
            e.printStackTrace();
        }
    }

    @Override
    public void close() {

    }
}
