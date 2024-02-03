package com.wgoulet.utils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.wgoulet.DetailAdminEvent;
import com.wgoulet.DetailDeletedUser;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.keycloak.Config;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventListenerProviderFactory;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.models.UserModel;
import org.keycloak.provider.ProviderEvent;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.events.admin.OperationType;


public class RabbitMQTest {
    @Test
    @DisplayName("1+1=2")
    void addsTwoNumbers() {
        assertEquals(2,1+1,"shoud be equal!!");
        AdminEvent evt = new AdminEvent();
        evt.setRepresentation("{\"id\":\"23174ea4-d158-4317-bbc3-6989a715d41b\",\"createdTimestamp\":1706985372867,\"username\":\"t@t.com\",\"enabled\":true,\"totp\":false,\"emailVerified\":false,\"firstName\":\"t\",\"lastName\":\"t\",\"email\":\"t@t.com\",\"attributes\":{\"awsenabled\":[\"true\"]},\"disableableCredentialTypes\":[],\"requiredActions\":[],\"notBefore\":0,\"access\":{\"manageGroupMembership\":true,\"view\":true,\"mapRoles\":true,\"impersonate\":true,\"manage\":true},\"userProfileMetadata\":{\"attributes\":[{\"name\":\"username\",\"displayName\":\"username\",\"required\":true,\"readOnly\":true,\"validators\":{}},{\"name\":\"email\",\"displayName\":\"email\",\"required\":true,\"readOnly\":false,\"validators\":{\"email\":{\"ignore.empty.value\":true}}}],\"groups\":[]}}");
        System.out.println(evt.getRepresentation());
        evt.setOperationType(OperationType.CREATE);
        DetailAdminEvent devt = new DetailAdminEvent(evt);
        ObjectMapper mapper = new ObjectMapper();
        
        try {
            String strrep = mapper.writeValueAsString(devt.getEventRepresentation());
            System.out.println(strrep);
        } catch (JsonProcessingException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
    }

    static String param(String key, String value) {
        return "\"" + key + "\"" + " : " + "\"" + value + "\"";
    }
}
