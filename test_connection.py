#!/usr/bin/env python3
"""
Test script for Transmission MCP Server
"""

import os
import sys
import json
from src.server import TransmissionClient, TransmissionConfig

def test_connection():
    """Test connection to Transmission daemon"""
    config = TransmissionConfig(
        host=os.getenv("TRANSMISSION_HOST", "192.168.1.205"),
        port=int(os.getenv("TRANSMISSION_PORT", "9091")),
        username=os.getenv("TRANSMISSION_USERNAME", ""),
        password=os.getenv("TRANSMISSION_PASSWORD", ""),
        use_socks5=os.getenv("USE_SOCKS5", "false").lower() == "true",
        socks5_host=os.getenv("SOCKS5_HOST", "127.0.0.1"),
        socks5_port=int(os.getenv("SOCKS5_PORT", "1080"))
    )
    
    print(f"Testing connection to {config.host}:{config.port}")
    print(f"Using SOCKS5: {config.use_socks5}")
    if config.use_socks5:
        print(f"SOCKS5 proxy: {config.socks5_host}:{config.socks5_port}")
    
    try:
        client = TransmissionClient(config)
        
        # Test session info
        print("\n=== Session Info ===")
        session_info = client.get_session_info()
        print(f"Version: {session_info.get('version')}")
        print(f"RPC Version: {session_info.get('rpc-version')}")
        print(f"Download Dir: {session_info.get('download-dir')}")
        
        # Test torrent list
        print("\n=== Torrents ===")
        torrents = client.list_torrents()
        print(f"Found {len(torrents)} torrents")
        
        for i, torrent in enumerate(torrents[:3]):  # Show first 3
            print(f"{i+1}. {torrent.get('name')} - {torrent.get('status')}")
        
        # Test free space
        print("\n=== Free Space ===")
        space_info = client.get_free_space()
        size_gb = space_info.get("size-bytes", 0) / (1024**3)
        print(f"Free space: {size_gb:.2f} GB")
        
        print("\n✅ Connection test successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
