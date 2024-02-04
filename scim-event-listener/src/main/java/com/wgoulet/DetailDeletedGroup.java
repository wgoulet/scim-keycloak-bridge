package com.wgoulet;
import org.keycloak.models.GroupModel;
import org.keycloak.models.GroupModel.GroupRemovedEvent;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.models.UserModel;
import java.util.Map;
import java.util.List;

public class DetailDeletedGroup {
    private GroupModel.GroupRemovedEvent dEvent;
    private final String opType = "DELETE";
    private final String resourceType = "GROUP";

    public String getResourceType() {
        return resourceType;
    }

    public String getOpType() {
        return opType;
    }

    public DetailDeletedGroup(GroupRemovedEvent dEvent) {
        this.dEvent = dEvent;
    }

    public String getGroupName()
    {
        return dEvent.getGroup().getName();
    }

    public Map<String, List<String>> getAttributes() {
        return dEvent.getGroup().getAttributes();
    }

    public String getId() {
        return dEvent.getGroup().getId();
    }
}
