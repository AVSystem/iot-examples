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
package com.avsystem.anjay.airqualitymeter.resources.location;

import com.avsystem.anjay.AnjayObject;
import com.avsystem.anjay.AnjayOutputContext;


import java.util.Optional;
import java.util.SortedSet;
import java.util.TreeSet;

/**
 * OMA spec https://raw.githubusercontent.com/OpenMobileAlliance/lwm2m-registry/prod/6.xml
 */
public class Location implements AnjayObject {

    static final int RID_LAT = 0;
    static final int RID_LON = 1;
    static final int OID_LOCATION = 6;

    private Optional<Float> lat;
    private Optional<Float> lon;

    public Location(Float lat, Float lon) {
        this.lat = Optional.ofNullable(lat);
        this.lon = Optional.ofNullable(lon);
    }

    @Override
    public void resourceRead(int iid, int rid, AnjayOutputContext context) throws Exception {
        switch (rid) {
            case RID_LAT:
                context.retFloat(lat.get());
                break;
            case RID_LON:
                context.retFloat(lon.get());
                break;
            default:
                throw new IllegalArgumentException("Unsupported resource " + rid);
        }
    }

    @Override
    public SortedSet<ResourceDef> resources(int iid) {
        TreeSet<ResourceDef> defs = new TreeSet<>();
        defs.add(new ResourceDef(RID_LAT, ResourceKind.R, lat.isPresent()));
        defs.add(new ResourceDef(RID_LON, ResourceKind.R, lon.isPresent()));
        return defs;
    }

    @Override
    public int oid() {
        return OID_LOCATION;
    }

    @Override
    public SortedSet<Integer> instances() {
        TreeSet<Integer> set = new TreeSet<>();
        set.add(1);
        return set;
    }

    @Override
    public void instanceReset(int iid) throws Exception {
        lat = Optional.empty();
        lon = Optional.empty();
    }

}
