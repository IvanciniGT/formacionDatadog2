# ---- build ----
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src ./src
RUN mvn -q -B package -DskipTests

# ---- run ----
FROM eclipse-temurin:21-jre
WORKDIR /app
# Source Code Integration: the tracer stamps every span with the repo and the exact commit, so
# a stack trace in APM or Error Tracking links straight to the line in GitLab. The pipeline
# passes them as build args; a local build without them just has no links.
ARG DD_GIT_REPOSITORY_URL=""
ARG DD_GIT_COMMIT_SHA=""
ENV DD_GIT_REPOSITORY_URL=${DD_GIT_REPOSITORY_URL} DD_GIT_COMMIT_SHA=${DD_GIT_COMMIT_SHA}
# The Java tracer. One jar, no code changes: that is the whole point of APM auto-instrumentation.
ADD https://dtdg.co/latest-java-tracer /app/dd-java-agent.jar
COPY --from=build /src/target/shop-api.jar /app/shop-api.jar
EXPOSE 8081
# Everything else (service, env, version, agent host...) comes from DD_* environment variables.
ENTRYPOINT ["java", "-javaagent:/app/dd-java-agent.jar", "-jar", "/app/shop-api.jar"]
