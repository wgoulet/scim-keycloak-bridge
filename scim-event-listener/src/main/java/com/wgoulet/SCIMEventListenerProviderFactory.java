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
        factory.setHost("localhost");
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
                            System.out.println("Got an event, going to do something");
                            if (event instanceof UserModel.UserRemovedEvent) {
                                UserModel.UserRemovedEvent dEvent = (UserModel.UserRemovedEvent) event;
                                System.out.println("Got delete event, going to delete this user");
                                System.out.println(dEvent.getUser().getEmail());
                                try {
                                    ObjectMapper mapper = new ObjectMapper();
                                    DetailDeletedUser duser = new DetailDeletedUser(dEvent);
                                    byte[] userObj = mapper.writeValueAsBytes(duser);
                                    //byte[] userObj = mapper.writeValueAsBytes(dEvent.getUser());
                                    channel.basicPublish("", "scimbridge", null, "Publishing delete event below".getBytes());
                                    channel.basicPublish("", "scimbridge", null, userObj);
                                } catch (IOException e) {
                                    // TODO Auto-generated catch block
                                    e.printStackTrace();
                                }
                                Map<String, List<String>> attributes = dEvent.getUser().getAttributes();
                                for (Map.Entry<String, List<String>> entry : attributes.entrySet()) {
                                    System.out.println("Key = " + entry.getKey());
                                    for (String val : entry.getValue()) {
                                        System.out.println(val);
                                    }
                                }
                                System.out.println("Done logging info about user!");
                                // TODO YOUR LOGIC WITH `dEvent.getUser()`
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
