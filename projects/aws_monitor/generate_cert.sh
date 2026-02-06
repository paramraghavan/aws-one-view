#!/bin/bash
# Generate self-signed SSL certificate for development

echo "Generating self-signed SSL certificate for development..."

# Create certs directory if it doesn't exist
mkdir -p certs

# Generate private key and certificate
openssl req -x509 -newkey rsa:4096 -nodes \
    -out certs/cert.pem \
    -keyout certs/key.pem \
    -days 365 \
    -subj "/C=US/ST=State/L=City/O=Development/CN=localhost"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Certificate generated successfully!"
    echo ""
    echo "Files created:"
    echo "  - certs/cert.pem (certificate)"
    echo "  - certs/key.pem (private key)"
    echo ""
    echo "To use HTTPS in development, run:"
    echo "  python main.py --ssl"
    echo ""
    echo "Then access: https://localhost:5000"
    echo ""
    echo "⚠️  Your browser will show a security warning because this is a self-signed certificate."
    echo "    Click 'Advanced' and 'Proceed to localhost' to continue."
else
    echo "❌ Error generating certificate"
    exit 1
fi
