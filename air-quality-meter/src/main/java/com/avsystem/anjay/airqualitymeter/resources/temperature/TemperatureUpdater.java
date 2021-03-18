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
package com.avsystem.anjay.airqualitymeter.resources.temperature;

import com.avsystem.anjay.airqualitymeter.services.RandomizerService;
import com.avsystem.anjay.airqualitymeter.services.WeatherAndQualityData;
import com.avsystem.anjay.airqualitymeter.services.WeatherAndQualityService;

import java.util.function.Consumer;

public class TemperatureUpdater implements Consumer<Temperature> {

    private final WeatherAndQualityService service;
    private final boolean shouldRandomizeData;

    public TemperatureUpdater(WeatherAndQualityService service) {
        this(service, false);
    }

    public TemperatureUpdater(WeatherAndQualityService service, boolean shouldRandomizeData) {
        this.service = service;
        this.shouldRandomizeData = shouldRandomizeData;
    }

    @Override
    public void accept(Temperature temperature) {
        if (shouldRandomizeData) {
            WeatherAndQualityData randomized = RandomizerService.randomize(service.getData());
            temperature.setTemp(randomized.getTemperatureInCel());
        } else {
            temperature.setTemp(service.getData().getTemperatureInCel());
        }
    }
}
