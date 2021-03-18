package com.avsystem.anjay.airqualitymeter;

import com.avsystem.anjay.AnjayObject;

import java.util.Optional;
import java.util.function.Consumer;

public class ObjectManager<T extends AnjayObject> {

    private final T object;
    private final Optional<Consumer<T>> objectUpdater;

    public ObjectManager(T object) {
        this(object, null);
    }

    public ObjectManager(T object, Consumer<T> objectUpdater) {
        this.object = object;
        this.objectUpdater = Optional.ofNullable(objectUpdater);
    }

    public T getObject() {
        return object;
    }

    public void updateObject() {
        this.objectUpdater.ifPresent(e -> e.accept(object));
    }
}
