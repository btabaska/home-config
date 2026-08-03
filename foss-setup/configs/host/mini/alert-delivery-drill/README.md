# alert-delivery-drill — synthetic "page reached a device" test (fix-63 / SM39)

mini host units are manual + doc-only (not ansible-managed; see
`configs/host/mini/`). This weekly timer runs
`/opt/verification/bin/alert-delivery-drill.sh`.

## What it proves

Every alerting check proves ntfy publishes succeed *server-side*, but nothing
proved the **last mile** — a logged-out phone app or a broken iOS upstream relay
is indistinguishable from a healthy one. The drill publishes a timestamped
message to a dedicated **`alert-drill`** topic (same self-hosted-ntfy → ntfy.sh
iOS-relay → device path as real alerts). Freshness of the send is verified by
`alert-delivery-drill-fresh`; **receipt is an operator human-confirm**.

## Deploy (on mini)

```bash
sudo install -m644 alert-delivery-drill.service alert-delivery-drill.timer \
  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now alert-delivery-drill.timer
# fire once now:
sudo systemctl start alert-delivery-drill.service
```

## Operator follow-up (human, weekly)

- The phone `phone` user already has read access to all topics, so subscribing
  the ntfy app to `alert-drill` on the self-hosted server is enough.
- When the Monday drill lands, you've confirmed device delivery for the week.
- **Closed-loop upgrade (optional):** an iOS Shortcut "when a notification on
  `alert-drill` arrives → GET a Healthchecks dead-man URL" would make receipt
  machine-verifiable. Create a Healthchecks check `alert-delivery-received`
  (period 8d, grace 1d) and point the Shortcut at its ping URL; then a missed
  weekly receipt pages automatically.
