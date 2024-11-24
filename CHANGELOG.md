# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [0.1.0] - 2023-04-22

- Initial release


## [0.1.1] - 2023-04-26

### Added

- Added new product_id for Fingerbot Plus (#1)

### Fixed

- Fixed problem in options flow.

### Changed

- Updated strings.json


## [0.1.2] - 2023-04-26

### Changed

- Changed a way to obtain device credentials from Tuya IOT cloud, possible fix to (#2)

## [0.1.4] - 2023-04-30

### Added

- Added support of CUBETOUCH 1s, thanks @damiano75
- Added new product_ids for Fingerbot.
- Added new product_ids for Fingerbot Plus.
- First attempt to support Smart Lock device.

### Fixed

- Fixed possible disconnect of BLE device.

## [0.1.5] - 2023-06-01

### Added

- Added new product_ids for Fingerbot.
- Added event "fingerbot_button_pressed" which is fired on Fingerbot Plus touch button press.
- First attempt to add support of climate entity.

## [0.1.6] - 2023-06-01

### Added

- Added new product_ids for Fingerbot and Fingerbot Plus.

### Changed

- Updated sources to conform Python 3.11

## [0.1.7] - 2023-06-01

### Added

- Added new product_ids.
- Added full support of BLE TRV provided by @forabi
- Added support of programming mode for Fingerbot Plus, thanks @redphx for information.

### Changed

- Improved connection stability.

## [0.1.8] - 2023-07-09

### Added

- Added support of 'Irrigation computer', thanks to @SanMiggel.
- Added new product_ids for Smart locks, thanks to @drewpo28.

### Changed

- Connection to the device is postponed now. Previously some out of range device might prevents HA from fully booting.
- Improved connection stability.

## [0.1.9] - 2024-11-24

### Added

- Added support for Radiator Valve 'llflaywg', with new category_id 'wkf'

### Changed

- Different warnings in current version of HA.
