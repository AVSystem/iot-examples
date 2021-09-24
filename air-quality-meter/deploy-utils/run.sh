#!/bin/bash
java -Djava.library.path=. -jar ./air-quality-meter.jar --randomize --lifetime 90 -s psk -i $(echo -n "$IDENTITY" | xxd -p) -k $(echo -n "$KEY" | xxd -p) -e $DEVICEID -u $SERVER_PROTOCOL://$SERVER_ADDRESS:$SERVER_PORT
