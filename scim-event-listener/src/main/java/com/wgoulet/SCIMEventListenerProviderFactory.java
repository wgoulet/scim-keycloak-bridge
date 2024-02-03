package com.wgoulet;

import org.keycloak.Config;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventListenerProviderFactory;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.models.UserModel;
import java.util.Map;
import java.util.concurrent.TimeoutException;
import java.io.IOException;
import java.util.List;
import com.rabbitmq.client.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.wgoulet.DetailDeletedUser;

public class SCIMEventListenerProviderFactory implements EventListenerProviderFactory {
    private final ConnectionFactory factory = new ConnectionFactory();
    private Connection connection;
    private Channel channel;

    @Override
    public EventListenerProvider create(KeycloakSession keycloakSession) {
        return new SCIMEventListenerProvider(keycloakSession);
    }

    @Override
    public void init(Config.Scope scope) {
        String rabbitmqpwd = System.getenv("RABBITMQPWD");
        String rabbitmquname = System.getenv("RABBITMQUNAME");
        String rabbitmqvhost = System.getenv("RABBITMQVHOST");
        String rabbitmqhost = System.getenv("RABBITMQHOST");
        factory.setHost(rabbitmqhost);
        factory.setUsername(rabbitmquname);
        factory.setPassword(rabbitmqpwd);
        factory.setVirtualHost(rabbitmqvhost);
        try {
            connection = factory.newConnection();
            channel = connection.createChannel();
            channel.queueDeclare("scimbridge", false, false, false, null);
        } catch (IOException | TimeoutException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
    }

    @Override
    public void postInit(KeycloakSessionFactory keycloakSessionFactory) {
            keycloakSessionFactory.register(
                    (event) -> {
                            if (event instanceof UserModel.UserRemovedEvent) {
                                UserModel.UserRemovedEvent dEvent = (UserModel.UserRemovedEvent) event;
                                try {
                                    ObjectMapper mapper = new ObjectMapper();
                                    DetailDeletedUser duser = new DetailDeletedUser(dEvent);
                                    byte[] userObj = mapper.writeValueAsBytes(duser);
                                    channel.basicPublish("", "scimbridge", null, userObj);
                                } catch (IOException e) {
                                    // TODO Auto-generated catch block
                                    e.printStackTrace();
                                }
                            }
                    });
    }

    @Override
    public void close() {

    }

    @Override
    public String getId() {
        return "scim-event-listener";
    }
}
