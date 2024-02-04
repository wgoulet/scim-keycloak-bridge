package com.wgoulet;

import org.keycloak.models.UserModel;
import java.util.Map;
import java.util.List;

public class DetailDeletedUser {
    private UserModel.UserRemovedEvent dEvent;
    private final String opType = "DELETE";
    private final String resourceType = "USER";
    public String getResourceType() {
        return resourceType;
    }

    public String getOpType() {
        return opType;
    }

    public DetailDeletedUser() {
    }

    public DetailDeletedUser(UserModel.UserRemovedEvent dEvent) {
        this.dEvent = dEvent;
    }

    public String getUserName() {
        return dEvent.getUser().getUsername();
    }

    public Map<String,List<String>> getAttributes() {
        return dEvent.getUser().getAttributes();
    }

    public String getUserId() {
        return dEvent.getUser().getId();
    }

}
