#!/bin/bash
# Generate self-signed TLS certificate for LAN use.
# Run once before first deployment.
# Certificate is valid for 10 years (clinic internal use only).

set -e
CERT_DIR="$(dirname "$0")/certs"
mkdir -p "$CERT_DIR"

echo "Generating self-signed certificate for joyvet.local / 192.168.1.100…"

openssl req -x509 -nodes -days 3650 \
  -newkey rsa:2048 \
  -keyout "$CERT_DIR/joyvet.key" \
  -out    "$CERT_DIR/joyvet.crt" \
  -subj "/CN=joyvet.local/O=JoyVet Care/C=ID" \
  -addext "subjectAltName=DNS:joyvet.local,DNS:localhost,IP:192.168.1.100,IP:127.0.0.1"

chmod 600 "$CERT_DIR/joyvet.key"
echo "✓ Certificate generated at $CERT_DIR"
echo ""
echo "Next step: install joyvet.crt on all clinic devices as a trusted CA."
echo "  macOS:   double-click joyvet.crt → Keychain → Trust Always"
echo "  Windows: double-click joyvet.crt → Install → Trusted Root CAs"
echo "  Android: Settings → Security → Install certificate"
