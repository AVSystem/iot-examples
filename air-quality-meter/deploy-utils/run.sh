#!/bin/bash
java -Djava.library.path=. -jar ./air-quality-meter.jar --randomize --lifetime 90 -e $DEVICEID -u coap://$SERVER_ADDRESS:5683
