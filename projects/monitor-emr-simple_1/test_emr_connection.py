#!/usr/bin/env python3
"""
EMR Connectivity Test Script
Tests network connectivity to EMR clusters and diagnoses common issues
"""

import requests
import socket
import os
import sys
import yaml
import subprocess
from urllib.parse import urlparse
import json


def print_header(title):
    """Print a formatted header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_status(message, status="INFO"):
    """Print a status message"""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "END": "\033[0m"
    }
    print(f"{colors.get(status, '')}{status}: {message}{colors['END']}")


def test_dns_resolution(hostname):
    """Test DNS resolution"""
    try:
        ip_address = socket.gethostbyname(hostname)
        print_status(f"DNS resolution successful: {hostname} -> {ip_address}", "SUCCESS")
        return True
    except socket.gaierror as e:
        print_status(f"DNS resolution failed for {hostname}: {e}", "ERROR")
        return False


def test_port_connectivity(hostname, port):
    """Test TCP port connectivity"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        sock.close()

        if result == 0:
            print_status(f"Port {port} is open on {hostname}", "SUCCESS")
            return True
        else:
            print_status(f"Port {port} is closed on {hostname}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Port test failed for {hostname}:{port} - {e}", "ERROR")
        return False


def test_http_endpoint(url, use_proxy=False):
    """Test HTTP endpoint connectivity"""
    try:
        proxies = {}
        if use_proxy:
            http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
            https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
            if http_proxy:
                proxies['http'] = http_proxy
            if https_proxy:
                proxies['https'] = https_proxy

            if proxies:
                print_status(f"Using proxy: {proxies}", "INFO")
            else:
                print_status("No proxy configuration found in environment", "WARNING")

        response = requests.get(url, timeout=30, proxies=proxies if use_proxy else None)
        response.raise_for_status()

        print_status(f"HTTP request successful: {response.status_code}", "SUCCESS")
        print_status(f"Response size: {len(response.content)} bytes", "INFO")

        # Try to parse JSON if possible
        try:
            data = response.json()
            if isinstance(data, dict) and len(data) > 0:
                print_status("Valid JSON response received", "SUCCESS")
            return True
        except:
            print_status("Response is not JSON (might be HTML)", "WARNING")
            return True

    except requests.exceptions.ProxyError as e:
        print_status(f"Proxy error: {e}", "ERROR")
        return False
    except requests.exceptions.SSLError as e:
        print_status(f"SSL error: {e}", "ERROR")
        return False
    except requests.exceptions.Timeout as e:
        print_status(f"Timeout error: {e}", "ERROR")
        return False
    except requests.exceptions.ConnectionError as e:
        print_status(f"Connection error: {e}", "ERROR")
        return False
    except requests.exceptions.HTTPError as e:
        print_status(f"HTTP error: {response.status_code} - {e}", "ERROR")
        return False
    except Exception as e:
        print_status(f"Unexpected error: {e}", "ERROR")
        return False


def check_proxy_environment():
    """Check proxy environment variables"""
    proxy_vars = ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'NO_PROXY', 'no_proxy']

    print_header("PROXY ENVIRONMENT CHECK")
    found_proxy = False

    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print_status(f"{var}={value}", "INFO")
            found_proxy = True

    if not found_proxy:
        print_status("No proxy environment variables found", "WARNING")
        print_status("If you're behind a corporate proxy, set these variables:", "INFO")
        print_status("  export HTTP_PROXY=http://proxy:port", "INFO")
        print_status("  export HTTPS_PROXY=https://proxy:port", "INFO")


def test_cluster_connectivity(cluster_config):
    """Test connectivity to a single cluster"""
    cluster_name = cluster_config.get('name', 'Unknown')
    yarn_url = cluster_config.get('yarn_url', '')
    spark_url = cluster_config.get('spark_url', '')

    print_header(f"TESTING CLUSTER: {cluster_name}")

    # Test YARN connectivity
    if yarn_url:
        print("\n--- Testing YARN ResourceManager ---")
        parsed = urlparse(yarn_url)
        hostname = parsed.hostname
        port = parsed.port or (80 if parsed.scheme == 'http' else 443)

        # DNS test
        dns_ok = test_dns_resolution(hostname)

        # Port test
        port_ok = test_port_connectivity(hostname, port)

        # HTTP endpoint tests
        endpoints = [
            '/ws/v1/cluster/info',
            '/ws/v1/cluster/metrics',
            '/ws/v1/cluster/nodes'
        ]

        for endpoint in endpoints:
            url = yarn_url + endpoint
            print(f"\nTesting: {url}")

            # Test without proxy
            print("  Without proxy:")
            success_direct = test_http_endpoint(url, use_proxy=False)

            # Test with proxy if environment variables exist
            if os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy'):
                print("  With proxy:")
                success_proxy = test_http_endpoint(url, use_proxy=True)
            else:
                success_proxy = None

            if not success_direct and success_proxy is False:
                print_status("Both direct and proxy connections failed", "ERROR")

    # Test Spark connectivity
    if spark_url:
        print("\n--- Testing Spark History Server ---")
        parsed = urlparse(spark_url)
        hostname = parsed.hostname
        port = parsed.port or (80 if parsed.scheme == 'http' else 443)

        # DNS test
        dns_ok = test_dns_resolution(hostname)

        # Port test
        port_ok = test_port_connectivity(hostname, port)

        # HTTP endpoint test
        url = spark_url + '/api/v1/applications?limit=1'
        print(f"\nTesting: {url}")

        # Test without proxy
        print("  Without proxy:")
        success_direct = test_http_endpoint(url, use_proxy=False)

        # Test with proxy if environment variables exist
        if os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy'):
            print("  With proxy:")
            success_proxy = test_http_endpoint(url, use_proxy=True)


def get_network_info():
    """Get basic network information"""
    print_header("NETWORK INFORMATION")

    try:
        # Get hostname
        hostname = socket.gethostname()
        print_status(f"Hostname: {hostname}", "INFO")

        # Get IP addresses
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        print_status(f"IP Addresses: {', '.join(ip_addresses)}", "INFO")

        # Check if we can reach the internet
        try:
            response = requests.get('http://httpbin.org/ip', timeout=5)
            external_ip = response.json().get('origin')
            print_status(f"External IP: {external_ip}", "INFO")
        except:
            print_status("Cannot reach external internet", "WARNING")

    except Exception as e:
        print_status(f"Error getting network info: {e}", "ERROR")


def main():
    """Main function"""
    print_header("EMR CONNECTIVITY TEST TOOL")
    print("This tool helps diagnose network connectivity issues with EMR clusters")

    # Check for config file
    config_file = 'emr_health_config.yaml'
    if not os.path.exists(config_file):
        print_status(f"Configuration file {config_file} not found", "ERROR")
        print_status("Please create the configuration file first", "INFO")
        sys.exit(1)

    # Load configuration
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print_status(f"Error loading configuration: {e}", "ERROR")
        sys.exit(1)

    # Get network info
    get_network_info()

    # Check proxy settings
    check_proxy_environment()

    # Test each cluster
    clusters = config.get('clusters', {})
    if not clusters:
        print_status("No clusters configured", "WARNING")
        sys.exit(1)

    for cluster_id, cluster_config in clusters.items():
        test_cluster_connectivity(cluster_config)

    # Summary and recommendations
    print_header("RECOMMENDATIONS")

    print_status("If you see connection errors:", "INFO")
    print_status("1. Work with IT team to whitelist EMR URLs in Zscaler", "INFO")
    print_status("2. Configure proxy settings if required:", "INFO")
    print_status("   export HTTP_PROXY=http://proxy:port", "INFO")
    print_status("3. Consider deploying on internal network with EMR clusters", "INFO")
    print_status("4. Use VPN or jump server for direct access", "INFO")

    print_status("\nFor immediate help, contact your IT/Network team with:", "INFO")
    print_status("- This test output", "INFO")
    print_status("- Business justification for EMR monitoring access", "INFO")
    print_status("- Specific URLs that need whitelisting", "INFO")


if __name__ == '__main__':
    main()
