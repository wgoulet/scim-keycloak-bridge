package com.wgoulet;

import org.keycloak.Config;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventListenerProviderFactory;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.models.UserModel;
import java.util.Map;
import java.util.List;

public class SCIMEventListenerProviderFactory implements EventListenerProviderFactory {
    @Override
    public EventListenerProvider create(KeycloakSession keycloakSession) {
        return new SCIMEventListenerProvider(keycloakSession);
    }

    @Override
    public void init(Config.Scope scope) {

    }

    @Override
    public void postInit(KeycloakSessionFactory keycloakSessionFactory) {
        keycloakSessionFactory.register(
            (event) -> {
                if (event instanceof UserModel.UserRemovedEvent) {
                    UserModel.UserRemovedEvent dEvent = (UserModel.UserRemovedEvent) event;
                    System.out.println("Got delete event, going to delete this user");
                    System.out.println(dEvent.getUser().getEmail());

                    Map<String,List<String>> attributes = dEvent.getUser().getAttributes();
                    for (Map.Entry<String,List<String>> entry : attributes.entrySet())  
                    {
                        System.out.println("Key = " + entry.getKey());  
                        for(String val : entry.getValue()){
                            System.out.println(val);
                        }
                    }
                    System.out.println("Done logging info about user!");
                    //TODO YOUR LOGIC WITH `dEvent.getUser()`
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
