# FrontDesk Pro Native Mobile Apps (Starter)

This directory now contains the native-app starter surface for iOS and Android delivery.

## What is included
- Expo app scaffold metadata (`app.json`)
- Shared API bootstrap config (`src/config.ts`)
- Minimal entry app (`App.tsx`)

## Build notes
- Native binaries are not produced in this repository environment because mobile SDK toolchains are not installed.
- This starter is committed so implementation can continue immediately on a machine with Expo/EAS tooling.

## Next implementation tasks
1. Add auth/session flow mirroring web login.
2. Add jobs dispatch and technician quick actions screens.
3. Add reminder queue and lead recovery screens.
4. Configure EAS build profiles and app store metadata.
