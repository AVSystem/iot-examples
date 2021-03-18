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
package com.avsystem.anjay.airqualitymeter.services;

import java.io.BufferedInputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.Scanner;
import java.util.logging.Level;
import java.util.logging.Logger;

public class SensorLocationService {

    public static Location getLocation() {
        Random random = new Random();
        try {
            Scanner scanner = new Scanner(new BufferedInputStream(SensorLocationService.class.getResourceAsStream("/cities.csv")));
            List<Location> locations = new ArrayList<>();
            while (scanner.hasNext()) {
                try {
                    String line = scanner.nextLine();
                    String[] split = line.split(",");
                    Location loc = new Location(Float.parseFloat(split[1]), Float.parseFloat(split[2]), split[0]);
                    locations.add(loc);
                } catch (Exception a) {
                    // ignore
                }
            }
            Logger.getAnonymousLogger().log(Level.INFO, "Loaded " + locations.size() + " cities.");
            Location location = locations.get(random.nextInt(locations.size()));
            Logger.getAnonymousLogger().log(Level.INFO, "Selected city = " + location.getCity());
            return location;
        } catch (Exception e) {
            Logger.getAnonymousLogger()
                    .log(Level.WARNING, "File with cities not found ", e);
            return new Location(0f,0f, "default-city");
        }
    }
}
