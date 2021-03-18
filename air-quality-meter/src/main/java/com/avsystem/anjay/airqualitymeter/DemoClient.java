/*
 * Copyright 2020 AVSystem <avsystem@avsystem.com>
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.avsystem.anjay.airqualitymeter;

import com.avsystem.anjay.*;
import com.avsystem.anjay.AnjayFirmwareUpdate.InitialState;
import com.avsystem.anjay.AnjayFirmwareUpdate.Result;
import com.avsystem.anjay.airqualitymeter.resources.airquality.AirQuality;
import com.avsystem.anjay.airqualitymeter.resources.airquality.AirQualityUpdater;
import com.avsystem.anjay.airqualitymeter.resources.device.Device;
import com.avsystem.anjay.airqualitymeter.resources.temperature.Temperature;
import com.avsystem.anjay.airqualitymeter.resources.temperature.TemperatureUpdater;
import com.avsystem.anjay.airqualitymeter.services.Location;
import com.avsystem.anjay.airqualitymeter.services.OpenWeatherMapService;
import com.avsystem.anjay.airqualitymeter.services.SensorLocationService;
import com.avsystem.anjay.airqualitymeter.services.WeatherAndQualityService;

import java.io.*;
import java.nio.channels.SelectableChannel;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.security.cert.Certificate;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.time.Duration;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.logging.Level;
import java.util.logging.Logger;

public final class DemoClient implements Runnable {

    private final Anjay.Configuration config;
    private final DemoArgs args;
    private AnjaySecurityObject securityObject;
    private AnjayServerObject serverObject;

    private final ScheduledExecutorService updateExecutor = Executors.newSingleThreadScheduledExecutor();

    private final Location location = SensorLocationService.getLocation();
    private final WeatherAndQualityService service = new OpenWeatherMapService(
            System.getenv(OpenWeatherMapService.API_KEY_ENV),
            location.getLat().doubleValue(),
            location.getLon().doubleValue());

    private final List<ObjectManager<?>> objectManagers;


    public DemoClient(DemoArgs commandlineArgs) {
        this.args = commandlineArgs;
        this.config = new Anjay.Configuration();
        this.config.endpointName = this.args.endpointName;
        this.config.inBufferSize = 4000;
        this.config.outBufferSize = 4000;
        this.config.msgCacheSize = 4000;
        this.objectManagers = List.of(
                new ObjectManager<>(new AirQuality(), new AirQualityUpdater(service, commandlineArgs.shouldRandomizeData)),
                new ObjectManager<>(new Temperature(), new TemperatureUpdater(service, commandlineArgs.shouldRandomizeData)),
                new ObjectManager<>(new Device(System.getenv("DEVICEID") + "-" + location.getCity())),
                new ObjectManager<>(new com.avsystem.anjay.airqualitymeter.resources.location.Location(location.getLat(), location.getLon()))
        );
    }

    @Override
    public void run() {

        try (Anjay anjay = new Anjay(this.config)) {
            this.securityObject = AnjaySecurityObject.install(anjay);
            this.serverObject = AnjayServerObject.install(anjay);
            AnjayAttrStorage attrStorage = AnjayAttrStorage.install(anjay);

            for (ObjectManager<?> manager : objectManagers) {
                anjay.registerObject(manager.getObject());
                this.updateExecutor.scheduleAtFixedRate(() -> {
                    try {
                        manager.updateObject();
                    } catch (Exception e) {
                        Logger.getAnonymousLogger().log(Level.INFO, "Exception during updating object " + manager.getObject().oid(), e);
                    }
                }, 1, 1, TimeUnit.SECONDS);
            }

            this.configureDefaultServer();

            Logger.getAnonymousLogger().log(Level.INFO, "*** DEMO STARTUP FINISHED ***");

            try (Selector selector = Selector.open()) {
                final long maxWaitMs = 1000L;
                while (true) {
                    List<SelectableChannel> sockets = anjay.getSockets();

                    for (SelectionKey key : selector.keys()) {
                        if (!sockets.contains(key.channel())) {
                            key.cancel();
                        }
                    }
                    for (SelectableChannel socket : sockets) {
                        if (socket.keyFor(selector) == null) {
                            socket.register(selector, SelectionKey.OP_READ);
                        }
                    }
                    long waitTimeMs = anjay.timeToNext().map(Duration::toMillis).orElse(maxWaitMs);
                    if (waitTimeMs > maxWaitMs) {
                        waitTimeMs = maxWaitMs;
                    }
                    if (waitTimeMs <= 0) {
                        selector.selectNow();
                    } else {
                        selector.select(waitTimeMs);
                    }
                    for (Iterator<SelectionKey> it = selector.selectedKeys().iterator();
                         it.hasNext(); ) {
                        anjay.serve(it.next().channel());
                        it.remove();
                    }
                    anjay.schedRun();

                }
            }
        } catch (Throwable t) {
            System.out.println("Unhandled exception happened during main loop: " + t);
            t.printStackTrace();
        }
    }

    private void configureDefaultServer() throws Exception {
        this.securityObject.purge();
        this.serverObject.purge();
        AnjaySecurityObject.Instance securityInstance = new AnjaySecurityObject.Instance();
        securityInstance.ssid = 1;
        securityInstance.serverUri = Optional.of(this.args.serverUri);

        if (this.args.securityMode == AnjaySecurityObject.SecurityMode.PSK
                || this.args.securityMode == AnjaySecurityObject.SecurityMode.CERTIFICATE) {
            securityInstance.publicCertOrPskIdentity = Optional.of(this.args.identityOrCert);
            securityInstance.privateCertOrPskKey = Optional.of(this.args.pskOrPrivKey);
        } else if (this.args.securityMode != AnjaySecurityObject.SecurityMode.NOSEC) {
            throw new RuntimeException("Unsupported security mode " + this.args.securityMode);
        }
        securityInstance.securityMode = this.args.securityMode;

        this.securityObject.addInstance(securityInstance);

        AnjayServerObject.Instance serverInstance = new AnjayServerObject.Instance();
        serverInstance.ssid = 1;
        serverInstance.lifetime = this.args.lifetime;
        serverInstance.binding = "U";
        this.serverObject.addInstance(serverInstance);
    }
}
