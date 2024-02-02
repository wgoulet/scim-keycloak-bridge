package com.wgoulet;

import org.jboss.logging.Logger;
import org.keycloak.events.Event;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmProvider;

public class SCIMEventListenerProvider implements EventListenerProvider {

    private static final Logger log = Logger.getLogger(SCIMEventListenerProvider.class);

    private final KeycloakSession session;
    private final RealmProvider model;

    public SCIMEventListenerProvider(KeycloakSession session) {
        this.session = session;
        this.model = session.realms();
    }

    @Override
    public void onEvent(Event event) {

    }

    @Override
    public void onEvent(AdminEvent adminEvent, boolean b) {
        System.out.println("About to log event!");
        System.out.println(adminEvent.getRepresentation());
        System.out.println("Event logged!!");

    }

    @Override
    public void close() {

    }
}
