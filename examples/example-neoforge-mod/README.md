# Qyrenith public NeoForge example

A tiny, neutral, redistributable NeoForge 1.21.1 example used to exercise Qyrenith's audit, Reality Map, build, metadata, and validation gates.

## Build

Requirements: JDK 21 and network access for the first Gradle/NeoForge dependency download.

```sh
./gradlew build
```

The resulting JAR is written to `build/libs/`.

## Why this project exists

This is deliberately not a gameplay showcase. It is a small, auditable control-plane fixture: one mod class, one metadata file, and the standard NeoForge build path.
