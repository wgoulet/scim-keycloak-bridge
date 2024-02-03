package com.wgoulet;

import java.io.IOException;
import java.util.concurrent.TimeoutException;

import org.jboss.logging.Logger;
import org.keycloak.events.Event;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventType;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.events.admin.OperationType;
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
            if(adminEvent.getOperationType() != OperationType.DELETE) {
                channel.basicPublish("", "scimbridge", null,sendString.getBytes());
            }
            else {
                channel.basicPublish("", "scimbridge", null, "User is being deleted".getBytes());
            }
            System.out.println("About to log event!");
            System.out.println(adminEvent.getRepresentation());
            System.out.println("Event logged!!");
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
