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
package com.avsystem.anjay.airqualitymeter.resources.device;

import com.avsystem.anjay.AnjayObject;
import com.avsystem.anjay.AnjayOutputContext;

import java.util.Optional;
import java.util.SortedSet;
import java.util.TreeSet;

/**
 * OMA spec https://raw.githubusercontent.com/OpenMobileAlliance/lwm2m-registry/prod/version_history/3-1_0.xml
 */
public class Device implements AnjayObject {

    static final int RID_MODEL_NUMBER = 1;
    static final int OID_DEVICE = 3;

    private Optional<String> modelNumber;

    public Device(String modelNumber) {
        this.modelNumber = Optional.ofNullable(modelNumber);
    }

    @Override
    public SortedSet<ResourceDef> resources(int iid) {
        TreeSet<ResourceDef> defs = new TreeSet<>();
        defs.add(new ResourceDef(RID_MODEL_NUMBER, ResourceKind.R, modelNumber.isPresent()));
        return defs;
    }

    @Override
    public void resourceRead(int iid, int rid, AnjayOutputContext context) throws Exception {
        switch (rid) {
            case RID_MODEL_NUMBER:
                context.retString(modelNumber.get());
                break;
            default:
                throw new IllegalArgumentException("Unsupported resource " + rid);
        }
    }

    @Override
    public int oid() {
        return OID_DEVICE;
    }

    @Override
    public SortedSet<Integer> instances() {
        TreeSet<Integer> set = new TreeSet<>();
        set.add(1);
        return set;
    }

    @Override
    public void instanceReset(int iid) throws Exception {
        modelNumber = Optional.empty();
    }

}
