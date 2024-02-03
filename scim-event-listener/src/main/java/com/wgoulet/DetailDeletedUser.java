package com.wgoulet;

import org.keycloak.models.UserModel;
import java.util.Map;
import java.util.List;

public class DetailDeletedUser {
    private UserModel.UserRemovedEvent dEvent;
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

}
