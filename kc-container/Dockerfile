# syntax=docker/dockerfile:1.2
FROM quay.io/keycloak/keycloak:latest as builder

# Enable health and metrics support
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true

# Configure a database vendor
ENV KC_DB=postgres

WORKDIR /opt/keycloak

FROM quay.io/keycloak/keycloak:latest
COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY --chown=keycloak:keycloak fullchain.pem /etc/letsencrypt/live/keycloak.wgoulet.com/fullchain.pem 
COPY --chown=keycloak:keycloak privkey.pem /etc/letsencrypt/live/keycloak.wgoulet.com/privkey.pem 
COPY --chown=keycloak:keycloak scim-event-listener.jar /opt/keycloak/providers/scim-event-listener.jar
COPY --chown=keycloak:keycloak infra.realm /opt/keycloak/infra.realm

RUN /opt/keycloak/bin/kc.sh build

# change these values to point to a running postgres instance
# https://stackoverflow.com/questions/31249112/allow-docker-container-to-connect-to-a-local-host-postgres-database
ENV KC_DB=postgres
ENV KC_DB_URL=jdbc:postgresql://172.31.21.234:5432/keycloak
ENV KC_DB_USERNAME=kcuser

# Required env variables needed by scim-event-listener
ENV RABBITMQUNAME=scimbridge
ENV RABBITMQVHOST=scimbridge
ENV RABBITMQHOST=172.31.21.234
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]