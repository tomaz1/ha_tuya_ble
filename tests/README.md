# Tests for Tuya BLE 0.2.2

Run the portable unit suite with Python 3.11 or newer:

```sh
python -m pip install -r tests/requirements.txt
python -m pytest -q tests
```

The suite uses the actual pinned Tuya SDK, cryptography and BLE library. HTTP responses, Home Assistant flow handling/selectors, its Bluetooth inventory and lifecycle services are test doubles. These tests do not simulate a running Home Assistant frontend or prove a real device handshake.

## Home Assistant acceptance checks

1. Upgrade the integration and restart Home Assistant. An existing manual device should retain its entities, UUID and local key and still work. An existing developer-account entry with saved device credentials should also keep working.
2. Add Tuya BLE. Check that User Code is selected by default and above the manual section. Confirm the smaller User Code help and documentation link are visible.
3. Submit a User Code, scan the QR in Smart Life or Tuya Smart, confirm in the app, then Submit. Select the BLE device from the account and confirm its local credentials.
4. Check that local_key and UUID are filled correctly. Verify automatic MAC matching when the device is advertising; otherwise select the nearby device or enter its Bluetooth MAC. Verify the device connects and its entities work.
5. Test an unconfirmed/expired QR, QR regeneration, an empty account and a temporarily unavailable network. Missing local_key or UUID must prevent saving until completed.
6. Add a device manually without signing in. Check duplicate-device prevention.
7. Open Configure, refresh the same device using User Code, and confirm the integration reloads with the new local key while keeping its identity and entities. Also test manual credential edits.
8. Remove an entry while its device is unreachable. Confirm removal finishes and a Home Assistant restart does not recreate it.

Never include real user codes, QR tokens or local keys in test output, issue reports or commits.
