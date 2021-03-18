#!/bin/bash
java -Djava.library.path=library/build/cmake -jar air-quality-meter/build/libs/air-quality-meter.jar --randomize=true --lifetime 90 -e $DEVICEID -u coap://$SERVER_ADDRESS:5683
