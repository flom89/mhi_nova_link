# Troubleshooting & FAQ

This page covers the most common problems encountered during setup or operation of **MHI Nova Link**, and how to resolve them.

> **Deutsch:** Diese Seite beschreibt häufige Probleme bei Installation und Betrieb von MHI Nova Link sowie deren Lösungen.

---

## Connection Problems

### Cannot connect to the gateway

**Symptom:** The integration shows the error `cannot_connect` during setup, or entities become unavailable after a while.

**Causes & solutions:**

| Possible cause | Solution |
|---|---|
| Wrong IP address or hostname | Verify the gateway address in your router's DHCP list |
| Gateway not reachable on the local network | Ping the gateway from another device on the same network |
| HTTPS port blocked | Confirm that port 443 (or the gateway's HTTPS port) is not blocked by a firewall |
| Gateway powered off or restarting | Check the physical device and its status LEDs |

---

### TLS certificate validation failed

**Symptom:** Error `invalid_ssl_fingerprint` or `TLS certificate validation failed` in Home Assistant logs.

**Causes & solutions:**

1. **No fingerprint configured and auto-detection failed:**
   - The gateway uses a self-signed certificate. Open the integration options (**Settings → Devices & Services → MHI Nova Link → Configure**) and either clear the fingerprint field to retry auto-detection, or enter the correct SHA256 fingerprint manually.

2. **Fingerprint configured but wrong:**
   - The gateway certificate has been renewed or replaced. Retrieve the new fingerprint from the gateway's web interface or via browser certificate details, then update it in the integration options.

3. **Fingerprint format invalid:**
   - The error `invalid_ssl_fingerprint_format` means the fingerprint string is not a valid hexadecimal SHA256 value. It must be 64 hex characters (with or without colons), e.g.:
     ```
     AA:BB:CC:DD:EE:FF:...  (with colons)
     aabbccddeeff...        (without colons)
     ```

---

### Authentication error

**Symptom:** Error `invalid_auth` during setup or after a credential change.

**Solutions:**
- Verify the username and password for the CompTrol gateway user account.
- Ensure the account has not been locked or deleted on the gateway.
- Update the credentials via **Settings → Devices & Services → MHI Nova Link → Configure**.

---

## Entity Problems

### No entities or incomplete data after setup

**Symptom:** The integration loads without errors, but entities are missing or show `unavailable`.

**Solutions:**
- Check the user permissions on the CompTrol 4Web NOVA RC gateway — the account may not have read access to all zones.
- Reload the integration: **Settings → Devices & Services → MHI Nova Link → ⋮ → Reload**.
- Check Home Assistant logs for coordinator errors (`Settings → System → Logs`).

---

### Time-series sensors show no data or stale values

**Symptom:** Sensors prefixed with `TS_` (e.g. `TS_Compressor frequency`) remain `unknown` or do not update.

**Explanation:** Time-series data is fetched separately at a longer interval (default 60 s) and is cached per zone. The data is sourced from the gateway's historical dataset and may inherently lag behind real-time values.

**Solutions:**
- Reduce `time_series_poll_interval` in the integration options if more frequent updates are needed.
- Verify that the relevant time-series dataset IDs are available and populated on the gateway.

---

### Compressor frequency shows incorrect values

**Symptom:** Compressor frequency values appear ten times too high.

**Note:** This was a known bug (raw values were not divided by 10). It is fixed in the current version. Update MHI Nova Link via HACS or manually.

---

## Configuration Problems

### Integration already configured

**Symptom:** Error `already_configured` when trying to add the integration a second time.

**Explanation:** The integration uses the gateway hostname/IP as a unique ID. Each gateway can only be configured once.

**Solution:** If you need to change the gateway address, remove the existing integration entry first and then re-add it with the new address.

---

### Environment variable for poll interval not respected

**Symptom:** Changing `NOVA_RC_UPDATE_INTERVAL_SECONDS` has no effect.

**Note:** Options set via the UI (`poll_interval` in the integration options) take precedence over environment variables. Remove the UI option value or set it to the desired value directly in the integration options.

---

## Logging & Diagnostics

Enable debug logging for the integration to get detailed output in the Home Assistant log:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.mhi_nova_link: debug
```

After restarting Home Assistant, check **Settings → System → Logs** for detailed messages from `custom_components.mhi_nova_link`.

---

## Reporting Issues

If none of the solutions above resolve your problem:

1. Collect the relevant log output (debug level).
2. Open an issue at [github.com/flom89/mhi_nova_link/issues](https://github.com/flom89/mhi_nova_link/issues).
3. Include: Home Assistant version, MHI Nova Link version, gateway firmware version, and the log excerpt.

For security-related issues, use the [GitHub Security Advisory](https://github.com/flom89/mhi_nova_link/security/advisories/new) — do **not** file a public issue.
