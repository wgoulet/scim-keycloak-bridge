package com.wgoulet;
import org.keycloak.models.UserModel;
import org.keycloak.models.UserModel.UserRemovedEvent;

public class DetailDeletedUser {
    public DetailDeletedUser() {
        this.dEvent = null;
        this.userModel = null;
    }

    UserModel.UserRemovedEvent dEvent;
    UserModel userModel;
    public DetailDeletedUser(UserRemovedEvent dEvent, UserModel userModel) {
        this.dEvent = dEvent;
        this.userModel = userModel;
    }

    public UserModel getUserModel() {
        return userModel;
    }

    public void setUserModel(UserModel userModel) {
        this.userModel = userModel;
    }

    public UserModel.UserRemovedEvent getdEvent() {
        return dEvent;
    }

    public void setdEvent(UserModel.UserRemovedEvent dEvent) {
        this.dEvent = dEvent;
    }


}
