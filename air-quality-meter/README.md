# Air Quality Meter  [<img align="right" height="50px" src="https://avsystem.github.io/Anjay-doc/_images/avsystem_logo.png">](http://www.avsystem.com/)

## About
This is a simple Java Application, that uses the Anjay-Java to expose Temperature and Air Quality over 
Lwm2m protocol. 

Air Quality meter selects randomly the city (over 26,000 cities are available) and query OpenWeatherMap 
(https://openweathermap.org/) every 5 minutes to get the actual temperature and air quality. Then every 1s 
adds a random value to that and expose the result via Lwm2m resources. 

Resources:

**/3303/1/5700** - Temperature in Celsius deg

**/3428/1/1** - PM10

**/3428/1/3** - PM25

## Provide Anjay binary that is compiled for your platform

You need to clone Anjay-Java repository and build library for your platform. Then copy it to `anjay-binary` directory.

```
git clone git@github.com:AVSystem/Anjay-java.git
Anjay-java/gradlew :library:build
# Change xxx to bin file - format and name depends on your platform (MacOS - libanjay-jni.dylib, Linux - libanjay-jni.so)
cp Anjay-java/library/build/cmake/xxx anjay-binary/
```

## Build

To build the application run
```
./gradlew :air-quality-meter:build
```

## Run locally

To launch the application build it first and then
Please remember to set **OPEN_WEATHER_API_TOKEN** env variable to your https://openweathermap.org/ api key, 
DEVICEID env variable to your device identifier (for example my_device) and SERVER_ADDRESS env variable to 
Lwm2m server. 

```
java -Djava.library.path=library/build/cmake -jar air-quality-meter/build/libs/air-quality-meter.jar --lifetime 90 -e $DEVICEID -u coap://$SERVER_ADDRESS:5683
```

## Run in K8s cluster

The application can be launched in Kubernetes cluster too. We prepared sample deployment and stateful sets 
yaml which you can use. 

Check `./air-quality-meter/deploy-utils` for more details.

## Build docker image

To build docker image check `./air-quality-meter/deploy-utils/Dockerfile`. 
