# Running the Aize server as a service

Three units, started at boot and restarted on failure, so the app's server
address keeps working across reboots.

```bash
sudo mkdir -p /opt/aize && sudo chown "$USER" /opt/aize
# put pkg/, valhalla.json, data/tiles/, data/places.db, proxy.py and search_server.py there
sudo cp server/deploy/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aize-valhalla aize-search aize-proxy
```

Check:

```bash
systemctl is-active aize-valhalla aize-search aize-proxy
curl -s localhost:8002/status
```

Order matters only for the first start: Valhalla loads tiles lazily, so the
proxy can come up before it. Memory: Valhalla takes about 300 MB at rest and
500 MB after the first route, which is why the full Malaysia graph fits on a
1 GiB host with the search server beside it.
