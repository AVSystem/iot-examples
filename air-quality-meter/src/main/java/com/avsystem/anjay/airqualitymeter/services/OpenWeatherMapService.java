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

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.base.Preconditions;
import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;

public class OpenWeatherMapService implements WeatherAndQualityService {

    public static final String API_KEY_ENV = "OPEN_WEATHER_API_TOKEN";
    private final String CACHE_KEY = "CACHE_KEY";
    private final HttpClient client = HttpClient.newHttpClient();
    private final ObjectMapper mapper = new ObjectMapper();

    private final LoadingCache<String, WeatherAndQualityData> cache = CacheBuilder.newBuilder()
            .expireAfterWrite(5, TimeUnit.MINUTES)
            .build(new CacheLoader<>() {
                @Override
                public WeatherAndQualityData load(String key) {
                    try {
                        return loadData();
                    } catch (Exception e) {
                        Logger.getAnonymousLogger()
                                .log(Level.WARNING, "Cannot get data from open weather map ", e);
                        return new WeatherAndQualityData(0f,0f,0f);
                    }
                }
            });
    private final URI weatherUri;
    private final URI airPollutionUri;

    public OpenWeatherMapService(String apiToken, Double lat, Double lon) {
        Preconditions.checkNotNull(apiToken, "You need to set env variable " + API_KEY_ENV);
        this.weatherUri = URI.create("http://api.openweathermap.org/data/2.5/weather?lat=" + lat + "&lon=" + lon + "&appid=" + apiToken);
        this.airPollutionUri = URI.create("http://api.openweathermap.org/data/2.5/air_pollution?lat=" + lat + "&lon=" + lon + "&appid=" + apiToken);
    }

    public WeatherAndQualityData getData() {
        try {
            return cache.get(CACHE_KEY);
        } catch (ExecutionException e) {
            Logger.getAnonymousLogger()
                    .log(Level.WARNING, "Cannot get data from cache ", e);
            return new WeatherAndQualityData(0f,0f,0f);
        }
    }

    private WeatherAndQualityData loadData() throws IOException, InterruptedException {
        HttpRequest weatherReq = HttpRequest.newBuilder()
                .uri(weatherUri)
                .timeout(Duration.ofSeconds(10))
                .GET()
                .build();

        HttpRequest airPollutionReq = HttpRequest.newBuilder()
                .uri(airPollutionUri)
                .timeout(Duration.ofSeconds(10))
                .GET()
                .build();

        HttpResponse<String> weatherResponse = client.send(weatherReq, HttpResponse.BodyHandlers.ofString());
        HttpResponse<String> airPollutionResponse = client.send(airPollutionReq, HttpResponse.BodyHandlers.ofString());

        float temperature = (float) (mapper.readTree(weatherResponse.body()).get("main").get("temp").asDouble() - 273.15);
        JsonNode airPollutionTree = mapper.readTree(airPollutionResponse.body());

        Logger.getAnonymousLogger().log(Level.INFO, "Data: " + weatherResponse.body());
        Logger.getAnonymousLogger().log(Level.INFO, "Data: " + airPollutionResponse.body());

        float pm25 = (float) airPollutionTree.get("list").get(0).get("components").get("pm2_5").asDouble();
        float pm10 = (float) airPollutionTree.get("list").get(0).get("components").get("pm10").asDouble();

        return new WeatherAndQualityData(temperature, pm10, pm25);
    }
}

