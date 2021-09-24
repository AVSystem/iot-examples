FROM openjdk:11 AS anjay-binary-builder
WORKDIR /app
RUN apt-get update
RUN apt-get -y install git build-essential cmake libmbedtls-dev zlib1g-dev
#RUN apt-get -y install python3.7
RUN git clone --depth 1 --branch 2.8.0.1 https://github.com/AVSystem/Anjay-java.git
RUN git -C ./Anjay-java submodule update --init --recursive
RUN Anjay-java/gradlew -p Anjay-java :library:build


FROM openjdk:11 AS builder
WORKDIR /app
COPY .  .
RUN ./gradlew build


FROM openjdk:11
WORKDIR /app
RUN ls
RUN apt-get update
RUN apt-get -y install git build-essential cmake libmbedtls-dev zlib1g-dev xxd
#RUN apt-get -y install python3.7
COPY --from=anjay-binary-builder /app/Anjay-java/library/build/cmake/libanjay-jni.so ./
COPY --from=builder /app/build/libs/air-quality-meter.jar ./
COPY deploy-utils/run.sh ./
RUN chmod 777 run.sh
RUN ls
CMD ["./run.sh"]

