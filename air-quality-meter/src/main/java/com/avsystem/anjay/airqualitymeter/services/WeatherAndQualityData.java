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

public class WeatherAndQualityData {

    private final Float temperatureInCel;
    private final Float pm10;
    private final Float pm25;

    public WeatherAndQualityData(Float temperatureInCel, Float pm10, Float pm25) {
        this.temperatureInCel = temperatureInCel;
        this.pm10 = pm10;
        this.pm25 = pm25;
    }

    public Float getPm25() {
        return pm25;
    }

    public Float getPm10() {
        return pm10;
    }

    public Float getTemperatureInCel() {
        return temperatureInCel;
    }
}
