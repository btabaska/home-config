# Nest SDM OAuth checklist

> Step-by-step recipe for wiring Google Nest into Home Assistant via the Smart Device Management (SDM) API — kept as a reference procedure, not a currently-deployed integration.
_Source: `foss-setup/configs/homeassistant/nest-sdm-oauth-checklist.md` · migrated + validated 2026-07-14._

!!! warning "Status: not deployed (SDM path dropped)"
    As of 2026-07-14 there are **no Nest entities and no `climate.*` entities** on the live Home Assistant (`http://192.168.10.50:8123`, running **2026.6.4**). The SDM cloud path has been **dropped** for this homelab — the plan is to replace the Nest thermostat with an **ecobee via `homekit_controller`** (local), hardware not yet installed. This checklist is retained as a reference in case SDM is ever revisited; the ~US $5 Device Access fee is optional and not needed for the current setup.

The old "Works with Nest" program is dead. Nest in Home Assistant now goes through
Google's **Smart Device Management (SDM) API**. This is the single most fiddly
integration in the whole homelab: it requires a Google Cloud project, a one-time
**US $5** Device Access registration fee, an OAuth client, and a Pub/Sub topic for
push events. It is **cloud-routed** (commands go Google cloud → device), so it is
NOT fully local. Budget ~45–60 min and do it in one sitting.

!!! note
    The Nest Pub/Sub setup process changed on **2025-01-23**. Make sure you are on a
    current Home Assistant version before starting (live is **2026.6.4**). Steps below
    reflect the 2026 flow.

Authoritative docs (read these alongside this checklist):

- HA Nest integration: <https://www.home-assistant.io/integrations/nest/>
- Google Device Access "Get Started": <https://developers.google.com/nest/device-access/get-started>
- Device Access registration: <https://developers.google.com/nest/device-access/registration>

---

## 0. Prerequisites (do not skip)

- [ ] **Personal Google account** (`@gmail.com`). Google **Workspace** accounts and
      accounts in the **Advanced Protection Program** CANNOT use the SDM API. Use the
      same Google account that owns the Nest devices throughout every step.
- [ ] Nest device(s) already set up and working in the **Google Home app**.
- [ ] Confirm your device is supported before paying the $5:
      <https://developers.google.com/nest/device-access/supported-devices>
- [ ] Home Assistant reachable over **HTTPS** at a public/known URL, OR use the
      My Home Assistant redirect (`https://my.home-assistant.io/redirect/oauth`).
      This HA has **no `external_url` configured**, so the My Home Assistant redirect
      is the relevant path. The OAuth redirect URI must match exactly later.
- [ ] Password manager open — you will store: Cloud Project ID, OAuth Client ID,
      OAuth Client Secret, Device Access Project ID, Pub/Sub Topic name.

---

## 1. Google Cloud project + enable APIs  [Cloud Console]

URL: <https://console.cloud.google.com/>

- [ ] Create a new project (e.g. `home-assistant-nest`) or pick an existing one.
- [ ] Note the **Cloud Project ID** (looks like `home-assistant-nest-123456`).
- [ ] Enable the **Smart Device Management API**:
      <https://console.cloud.google.com/apis/library/smartdevicemanagement.googleapis.com>
- [ ] Enable the **Cloud Pub/Sub API**:
      <https://console.cloud.google.com/apis/library/pubsub.googleapis.com>

---

## 2. OAuth consent screen  [Cloud Console]

URL: <https://console.cloud.google.com/apis/credentials/consent>

- [ ] User type: **External** → Create.
- [ ] Fill App name, User support email, Developer contact email.
- [ ] Add your own Google account under **Test users** (if the app stays in Testing).
- [ ] **CRITICAL: set the publishing status to "In production" / Production.**
      If it stays in "Testing", OAuth refresh tokens expire after **7 days** and the
      integration silently dies a week later. Production = tokens persist.
      (You do NOT need Google's app verification for personal use.)

---

## 3. OAuth Client ID (Web application)  [Cloud Console]

URL: <https://console.cloud.google.com/apis/credentials>

- [ ] **Create Credentials → OAuth client ID**.
- [ ] Application type: **Web application**.
- [ ] Under **Authorized redirect URIs**, add EXACTLY:
      `https://my.home-assistant.io/redirect/oauth`
      (If you do NOT use My Home Assistant, use your own:
      `https://<your-ha-external-url>/auth/external/callback`)
- [ ] Create, then copy the **Client ID** and **Client Secret** to the password manager.
- [ ] Common failure: `Error 400: redirect_uri_mismatch` later = this URI doesn't
      exactly match. Fix it here.

---

## 4. Device Access project + pay $5  [Device Access Console]

URL: <https://console.nest.google.com/device-access/>

- [ ] Click **Go to the Device Access Console**, accept Terms of Service, **pay the
      one-time US $5** fee.
- [ ] **Create project**, give it a name.
- [ ] When prompted, paste the **OAuth Client ID** from step 3.
- [ ] Leave **Enable Events** UNCHECKED for now (you need the Pub/Sub topic first;
      you'll come back in step 6).
- [ ] Copy the resulting **Device Access Project ID** (a UUID like
      `32c4c2bc-fe0d-461b-b51c-f3885afff2f0`) to the password manager. HA needs this.

Project list: <https://console.nest.google.com/device-access/project-list>

---

## 5. Create a Pub/Sub topic + grant publisher  [Cloud Console]

URL: <https://console.cloud.google.com/cloudpubsub/topic/list>

- [ ] **Create Topic** (e.g. Topic ID `home-assistant-nest`). Leave defaults.
- [ ] The full **Topic Name** is `projects/<cloud-project-id>/topics/home-assistant-nest`.
      Save it.
- [ ] On the topic, **Add Principal** and grant the **Pub/Sub Publisher** role to:
      `sdm-publisher@googlegroups.com`
      (this lets Google's SDM service publish device events to your topic).

---

## 6. Enable events on the Device Access project  [Device Access Console]

URL: <https://console.nest.google.com/device-access/>

- [ ] Open your Device Access project.
- [ ] Next to **Pub/Sub topic**, choose **…** → **Enable events with Pub/Sub topic**.
- [ ] Paste the full Topic Name from step 5 and validate.

---

## 7. Add Application Credentials in Home Assistant  [Home Assistant]

- [ ] Settings → Devices & Services → (three-dot menu, top right) →
      **Application Credentials** → **Add credential**.
- [ ] Integration: **Nest**. Enter the OAuth **Client ID** and **Client Secret** from step 3.

---

## 8. Add the Nest integration  [Home Assistant]

- [ ] Settings → Devices & Services → **+ Add Integration** → search **Nest**.
- [ ] Enter your **Device Access Project ID** (from step 4) and the **Cloud Pub/Sub
      Subscriber** info / Topic name when prompted.
- [ ] Follow the OAuth flow: you'll be sent to Google, sign in with the SAME account,
      choose the Nest devices to authorize (the **Partner Connections** screen),
      grant access, and you'll be redirected back to HA.
- [ ] Devices and entities (thermostat, camera, etc.) should appear.

---

## Troubleshooting (from the field)

- **Tokens die after 7 days** → OAuth consent screen was left in "Testing". Set to
  Production (step 2), remove + re-add Application Credentials.
- **`redirect_uri_mismatch`** → the redirect URI in step 3 doesn't match. Add
  `https://my.home-assistant.io/redirect/oauth` exactly.
- **"Can't link to [Project]"** → Client ID mismatch between Cloud Console, Device
  Access project, and HA Application Credentials. Verify all three use the same ID.
- **No devices show up** → permission issue; manage at
  <https://nestservices.google.com/partnerconnections> and re-authorize.
- **`RESOURCE_EXHAUSTED` / Rate limited** → too many API calls (e.g. 5 qpm for
  `devices.list`); reduce polling / wait.
- Enable HA debug logging for `homeassistant.components.nest` to see the OAuth and
  Pub/Sub flow.

## Reminder

This integration is **cloud-routed**. If Google ever pulls SDM access, Nest control
breaks. For a fully-local thermostat, use Zigbee/Z-Wave or an ecobee-class device
(HomeKit-controller) — which is the direction this homelab has chosen, superseding
the SDM path above.

---
[← Home Assistant reference](index.md)
