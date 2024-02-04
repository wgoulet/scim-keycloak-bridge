package com.wgoulet;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.events.admin.OperationType;

import java.util.HashMap;
import java.util.Map;

public class DetailAdminEvent {
    private Map<String,String> eventRepresentation;
    public Map<String,String> getEventRepresentation() {
        return eventRepresentation;
    }
    public DetailAdminEvent(AdminEvent event) {
        this.eventRepresentation = new HashMap<>();
        this.eventRepresentation.put("representation",event.getRepresentation());
        this.eventRepresentation.put("opType",event.getOperationType().name());
        this.eventRepresentation.put("resourceType",event.getResourceTypeAsString());
        this.eventRepresentation.put("resourcePath",event.getResourcePath());
    }
}
