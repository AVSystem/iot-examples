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

import com.avsystem.anjay.AnjayObject;
import com.avsystem.anjay.AnjayOutputContext;

import java.util.Optional;
import java.util.SortedSet;
import java.util.TreeSet;

/**
 * OMA spec https://raw.githubusercontent.com/OpenMobileAlliance/lwm2m-registry/prod/version_history/3303-1_0.xml
 */
public class Temperature implements AnjayObject {

    static final int RID_TEMPERATURE = 5700;
    static final int RID_UNIT = 5701;
    static final int OID_TEMPERATURE = 3303;

    private Optional<Float> temp = Optional.empty();
    private Optional<String> unit = Optional.empty();

    public void setTemp(Float temp) {
        this.temp = Optional.of(temp);
    }

    public void setUnit(String unit) {
        this.unit = Optional.of(unit);
    }

    @Override
    public SortedSet<ResourceDef> resources(int iid) {
        TreeSet<ResourceDef> defs = new TreeSet<>();
        defs.add(new ResourceDef(RID_TEMPERATURE, ResourceKind.R, temp.isPresent()));
        defs.add(new ResourceDef(RID_UNIT, ResourceKind.R, unit.isPresent()));
        return defs;
    }

    @Override
    public void resourceRead(int iid, int rid, AnjayOutputContext context) throws Exception {
        switch (rid) {
            case RID_TEMPERATURE:
                context.retFloat(temp.get());
                break;
            case RID_UNIT:
                context.retString(unit.get());
                break;
            default:
                throw new IllegalArgumentException("Unsupported resource " + rid);
        }

    }

    @Override
    public int oid() {
        return OID_TEMPERATURE;
    }

    @Override
    public void instanceReset(int iid) throws Exception {
        temp = Optional.empty();
        unit = Optional.empty();
    }

    @Override
    public SortedSet<Integer> instances() {
        TreeSet<Integer> treeSet = new TreeSet<>();
        treeSet.add(1);
        return treeSet;
    }
}
