# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [0.2.2] - 2026-09-12

**Sources and acknowledgements:** See [Sources used for 0.2.2](#sources-used-for-022) at the end of this changelog for the ideas, reference code and SDK used in this release.

### Added

- Added a read-only Child lock state diagnostic sensor for the llflaywg radiator valve, using DP 12 shared with the existing configuration switch.
- Added User Code sign-in through the official Tuya device-sharing SDK, followed by a QR code scanned and confirmed in Smart Life or Tuya Smart.
- Added account device selection and retrieval of local key, UUID, device ID, category, product ID and optional device metadata.
- Added Bluetooth UUID matching to find the device address, with nearby-device selection and manual completion when Tuya does not provide all required BLE information.
- Added User Code location help and a link to the official Home Assistant instructions below the User Code field.
- Added QR regeneration, retryable login/device-list errors and validation that prevents saving incomplete local credentials or replacing an existing entry with a different device.

### Changed

- Removed the redundant strings.json file. Custom integration translations are maintained in translations/en.json, with explicit English text as required by the [Home Assistant custom integration localization documentation](https://developers.home-assistant.io/docs/internationalization/custom_integration/).
- Made User Code the default setup method and placed it above the existing manual section.
- Removed the Tuya Developer Platform login section and the old developer-account SDK. The maintainer's developer-account trial/subscription expired; using the app account avoids requiring a separate developer project and renewing its IoT service subscription.
- Kept manual setup and local BLE operation. Only device credentials are saved; QR and account access/refresh tokens remain in memory during setup.
- Migrated existing entries to retain local credentials and remove developer-account secrets. Entries without complete local credentials can recover through User Code or manual setup.
- Updated the manifest version to 0.2.2 and replaced the obsolete developer SDK dependencies with the device-sharing SDK and an explicit BLE encryption dependency.

### Fixed

- Restore the Open 100% label for the llflaywg radiator valve mode, using the original repository translation. Scope the valve_mode translation key to that product while preserving the dry HVAC value and DP 1 value 3 for existing automations and device commands.
- Replace the remaining deprecated CONCENTRATION_PARTS_PER_MILLION import and usage in the CO2 alarm threshold number entity with UnitOfRatio.PARTS_PER_MILLION.
- Align English translations with the actual entity keys, including the binary battery sensor, lid display button, temperature calibration and battery percentage. Add missing reminder, lock alarm, volume, display, motor thrust and valve/window state labels without changing entity identifiers or datapoint mappings.
- Replace all unresolved translation references in strings.json and translations/en.json with explicit English labels and states, including Battery, Signal strength, Brightness, Switch, Charging, Not charging, Low, Normal, Carbon dioxide, Humidity, Moisture and Temperature.
- Preserve the Bluetooth MAC from the discovery card when adding an app-account device and the advertisement UUID cannot be decoded. Prefer an exact UUID match and never use the discovery fallback when a decoded UUID conflicts.
- Use the latest available advertisement when checking a discovered device, and distinguish a missing Bluetooth MAC from an invalid address in the confirmation form.
- Restored the BLE library exports after integration lifecycle code had been placed in the internal library initializer.
- Reload the integration when credentials change and bound device shutdown during unload so an unreachable BLE device does not block removal indefinitely.

## [0.2.1] - 2026-09-12

### Added

- Added manual device setup using Bluetooth MAC address, UUID, local key, device ID, category and product ID.
- Added options to edit stored device credentials and switch between manual setup and Tuya Developer Platform.
- Added optional device name, product name and model fields for manual setup.

### Changed

- Updated setup and options forms with separate manual and cloud sections and clearer field descriptions.
- Disabled verbose debug logging by default.
- Ordered changelog releases from newest to oldest.

### Fixed

- Added validation messages for invalid MAC addresses and missing manual or cloud credentials.
- Added a clearer error message when cloud device credentials cannot be retrieved, with guidance to check the subscription or use manual setup.

## [0.2.0] - 2025-08-07

### Added

- Added full support for Radiator Valve 'llflaywg', with new category_id 'wkf'

## [0.1.9] - 2024-11-24

### Added

- Added support for Radiator Valve 'llflaywg', with new category_id 'wkf' (only get temperature, set temperature and child lock)

### Changed

- Different warnings in current version of HA.

## [0.1.8] - 2023-07-09

### Added

- Added support of 'Irrigation computer', thanks to @SanMiggel.
- Added new product_ids for Smart locks, thanks to @drewpo28.

### Changed

- Connection to the device is postponed now. Previously some out of range device might prevents HA from fully booting.
- Improved connection stability.

## [0.1.7] - 2023-06-01

### Added

- Added new product_ids.
- Added full support of BLE TRV provided by @forabi
- Added support of programming mode for Fingerbot Plus, thanks @redphx for information.

### Changed

- Improved connection stability.

## [0.1.6] - 2023-06-01

### Added

- Added new product_ids for Fingerbot and Fingerbot Plus.

### Changed

- Updated sources to conform Python 3.11

## [0.1.5] - 2023-06-01

### Added

- Added new product_ids for Fingerbot.
- Added event "fingerbot_button_pressed" which is fired on Fingerbot Plus touch button press.
- First attempt to add support of climate entity.

## [0.1.4] - 2023-04-30

### Added

- Added support of CUBETOUCH 1s, thanks @damiano75
- Added new product_ids for Fingerbot.
- Added new product_ids for Fingerbot Plus.
- First attempt to support Smart Lock device.

### Fixed

- Fixed possible disconnect of BLE device.

## [0.1.2] - 2023-04-26

### Changed

- Changed a way to obtain device credentials from Tuya IOT cloud, possible fix to (#2)

## [0.1.1] - 2023-04-26

### Added

- Added new product_id for Fingerbot Plus (#1)

### Fixed

- Fixed problem in options flow.

### Changed

- Updated strings.json

## [0.1.0] - 2023-04-22

- Initial release

## Sources used for 0.2.2

### Ideas and background

- [Tuya Home Assistant repository](https://github.com/tuya/tuya-home-assistant): background on moving away from developer-platform projects and expired IoT service subscriptions toward app-account authorization.
- [Vineet Choudhary's tuya-local-key project](https://github.com/vineetchoudhary/tuya-local-key) and its [Home Assistant Community announcement](https://community.home-assistant.io/t/get-tuya-local-key-via-smartlife-tuyasmart-qr-login-no-tuya-iot-developer-account/1018805): the user-provided inspiration for obtaining local keys through Smart Life / Tuya Smart User Code and QR login without a developer account.

### Reference code and SDK

- [Home Assistant Core Tuya config_flow.py (2026.9.0)](https://github.com/home-assistant/core/blob/2026.9.0/homeassistant/components/tuya/config_flow.py): reference for the User Code → QR → app confirmation sequence, LoginControl calls, QR payload format and native QrCodeSelector used by the new BLE configuration flow.
- [Home Assistant Core Tuya const.py (2026.9.0)](https://github.com/home-assistant/core/blob/2026.9.0/homeassistant/components/tuya/const.py): the public application registration values `HA_3y9q4ak7g4ephrvke` and `haauthorize` used for device-sharing authorization.
- [Tuya device-sharing SDK](https://github.com/tuya/tuya-device-sharing-sdk), installed as `tuya-device-sharing-sdk==0.2.15`: the implementation directly uses `LoginControl`, `CustomerApi` and `CustomerTokenInfo` for authentication and authenticated requests. The SDK's home/device repositories informed the endpoints used to retrieve device records, including `local_key` and UUID.
- [tuya-local-key / tuya_devices.py](https://github.com/vineetchoudhary/tuya-local-key/blob/main/tuya_devices.py): reference for the QR login result, token fields and retrieval of app-account device credentials through the official SDK. This integration implements its own Home Assistant flow and local credential storage; it does not copy that project's CLI, web server or session-file persistence.
- Existing code in this repository: the working manual credential format and BLE advertisement UUID decoding were reused as the basis for credential storage and Bluetooth address matching. The BLE library exports were restored from the repository's earlier working initializer.

### User-facing instructions

- [Official Home Assistant Tuya documentation — Obtaining User Code for sign-in](https://www.home-assistant.io/integrations/tuya/#obtaining-user-code-for-sign-in): source for the app navigation instructions shown below the User Code field: **Me → Settings → Account and Security → User Code**.

### Additional translation review sources

- [briis/ha_tuya_ble English translations](https://github.com/briis/ha_tuya_ble/blob/main/custom_components/tuya_ble/translations/en.json), [jpmreis/ha_tuya_ble English translations](https://github.com/jpmreis/ha_tuya_ble/blob/main/custom_components/tuya_ble/translations/en.json) and [markusg1234/ha_tuya_ble English translations](https://github.com/markusg1234/ha_tuya_ble/blob/main/custom_components/tuya_ble/translations/en.json): compared entity labels and states with their corresponding strings.json files on 2026-09-13. All three use Battery for both the percentage sensor and the binary battery condition.
- [Home Assistant binary sensor device classes](https://www.home-assistant.io/integrations/binary_sensor/#device-class): battery on means low and off means normal; battery_charging on means charging and off means not charging.
- [Home Assistant backend localization](https://developers.home-assistant.io/docs/internationalization/core/): translation references in source strings and entity/state translation structure. Display labels were also checked against this repository's actual entity keys and option values.

- [Original tomaz1/ha_tuya_ble English climate translation](https://github.com/tomaz1/ha_tuya_ble/blob/main/custom_components/tuya_ble/translations/en.json): restored the valve_mode state label dry → Open 100% for the llflaywg radiator valve.
