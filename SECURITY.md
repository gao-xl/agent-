# Security Policy

## Supported versions

The current `main` branch is the supported development version.

## Reporting a vulnerability

Do not open public issues for vulnerabilities involving authentication, exposed secrets, device-control bypasses, unsafe default actions, or privacy leakage. Contact the maintainers privately through the repository's security advisory feature after it is enabled.

## Safety requirements

- Every hardware action must pass Safety Core.
- Loss of connection, process shutdown, and an emergency stop must stop outstanding work.
- Sensor data is informational; it cannot authorize or escalate a device action.
- Providers must minimize data collection and never log secrets or raw sensitive media by default.
