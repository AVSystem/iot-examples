FROM openjdk:11 AS builder

WORKDIR /app
RUN ls
RUN apt-get update
RUN apt-get -y install git build-essential cmake libmbedtls-dev zlib1g-dev
RUN apt-get -y install python3.7

COPY .  .
RUN git submodule update --init
RUN ./gradlew :air-quality-meter:build


FROM openjdk:11
RUN ls
RUN apt-get update
RUN apt-get -y install git build-essential cmake libmbedtls-dev zlib1g-dev
RUN apt-get -y install python3.7
COPY --from=builder /app .
COPY air-quality-meter/deploy-utils/run.sh .
RUN chmod 777 run.sh
RUN ls
CMD ["./run.sh"]

