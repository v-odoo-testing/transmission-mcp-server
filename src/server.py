#!/usr/bin/env python3
"""
Transmission MCP Server

A simple MCP server for controlling Transmission torrent daemon.
Supports direct connection and SOCKS5 proxy.
"""

import json
import os
import sys
import re
from typing import Optional, Dict, Any, List
import httpx
import socks
import socket
from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
from pydantic import BaseModel


# MCP Resources with reference information
MAGNET_LINK_GUIDE = """# Magnet Link Format Reference

## Valid Magnet Link Format
```
magnet:?xt=urn:btih:[HASH]&dn=[DISPLAY_NAME]&tr=[TRACKER_URL]
```

## Hash Requirements
- **Hex Format**: Exactly 40 hexadecimal characters (0-9, A-F)
  - Example: `A1B2C3D4E5F67890ABCDEF1234567890ABCDEF12`
- **Base32 Format**: Exactly 32 base32 characters (A-Z, 2-7)
  - Example: `MFRGG43FMZRW6Y3PNUXXE3DFMFRGG43F`

## ❌ INVALID Examples
- `THUNDERBOLTS2025` (not hex, not 40 chars)
- `movie123` (too short, not hex)
- `abcdef` (too short)

## ✅ Valid Example
```
magnet:?xt=urn:btih:A1B2C3D4E5F67890ABCDEF1234567890ABCDEF12&dn=Movie.2024.1080p&tr=udp://tracker.example.com:1337/announce
```

## Common Tracker URLs
- `udp://tracker.opentrackr.org:1337/announce`
- `udp://tracker.leechers-paradise.org:6969/announce`
- `udp://tracker.coppersurfer.tk:6969/announce`

## Important Notes
- NEVER generate fake hashes - always use real magnet links from torrent sites
- Hash is derived from torrent content - cannot be made up
- Popular sites: YTS, 1337x, The Pirate Bay, RARBG
"""

TORRENT_WORKFLOW_GUIDE = """# Torrent Management Workflow

## Adding Torrents
1. **Find Real Magnet Links**: Use actual torrent sites, never generate fake hashes
2. **Validate Format**: Check hash is 40-char hex before adding
3. **Set Directory**: Specify download location if different from default
4. **Auto-start**: Torrents start automatically unless `start_torrent: false`

## Searching and Managing
- Use `search_torrents` to find existing torrents by name
- Use `get_torrent_details` for comprehensive torrent information
- Use `control_torrent` to start/stop/remove torrents

## Directory Structure
Common download directories:
- Movies: `/media/lacie/Media/Movies`
- TV Shows: `/media/lacie/Media/TV Shows/[ShowName]/Season X`
- Downloads: `/media/lacie/Downloads`

## Status Codes
- **0**: stopped
- **1**: check-wait  
- **2**: checking
- **3**: download-wait
- **4**: downloading
- **5**: seed-wait
- **6**: seeding
- **7**: isolated (no peers)

## Best Practices
- Always verify torrent is legitimate before adding
- Use proper directory structure for organization
- Monitor download progress with `get_torrent_details`
- Remove completed torrents when no longer needed
"""

CONNECTION_GUIDE = """# Transmission Connection Guide

## Connection Modes

### Direct Connection (Local Network)
- Default mode when `use_socks5: false`
- Use when on same network as Transmission server
- Fastest and most reliable

### SOCKS5 Proxy (Remote Access)
- Use when away from home network
- Set `use_socks5: true` in tool calls
- Requires SOCKS5 tunnel setup

## Setting Up SOCKS5 Tunnel
```bash
# SSH tunnel with SOCKS5
ssh -D 1080 -N user@your-home-server.com
```

## Environment Variables
- `TRANSMISSION_HOST`: Server IP (default: 192.168.1.205)
- `TRANSMISSION_PORT`: RPC port (default: 9091)
- `TRANSMISSION_USERNAME`: Authentication username
- `TRANSMISSION_PASSWORD`: Authentication password
- `USE_SOCKS5`: Default proxy mode (true/false)
- `SOCKS5_HOST`: Proxy host (default: 127.0.0.1)
- `SOCKS5_PORT`: Proxy port (default: 1080)

## Troubleshooting
- **Connection refused**: Check if Transmission daemon is running
- **Authentication failed**: Verify username/password
- **Timeout**: Check network connectivity or try SOCKS5 mode
- **409 Error**: Session ID expired (automatically handled)
"""


def validate_magnet_link(magnet_url: str) -> tuple[bool, str]:
    """Validate magnet link format and hash"""
    if not magnet_url.startswith('magnet:?xt=urn:btih:'):
        return False, "Invalid magnet link format - must start with 'magnet:?xt=urn:btih:'"
    
    # Extract hash from magnet link (supports both 40-char hex and 32-char base32)
    hex_match = re.search(r'urn:btih:([A-Fa-f0-9]{40})', magnet_url)
    base32_match = re.search(r'urn:btih:([A-Za-z2-7]{32})', magnet_url)
    
    if not hex_match and not base32_match:
        return False, "Invalid hash - must be 40-character hex (A-F0-9) or 32-character base32 (A-Z2-7)"
    
    return True, "Valid magnet link"


def validate_torrent_url(url: str) -> tuple[bool, str]:
    """Validate torrent URL format"""
    if url.startswith('magnet:'):
        return validate_magnet_link(url)
    elif url.startswith(('http://', 'https://')) and url.endswith('.torrent'):
        return True, "Valid torrent URL"
    else:
        return False, "Invalid URL - must be magnet link or HTTP(S) URL ending in .torrent"


class TransmissionConfig(BaseModel):
    """Configuration for Transmission connection"""
    host: str = "192.168.1.205"
    port: int = 9091
    username: str = ""
    password: str = ""
    use_socks5: bool = False
    socks5_host: str = "127.0.0.1"
    socks5_port: int = 1080
    timeout: int = 30


class TransmissionClient:
    """Simple Transmission RPC client"""
    
    def __init__(self, config: TransmissionConfig, use_socks5: Optional[bool] = None):
        self.config = config
        self.session_id: Optional[str] = None
        self.base_url = f"http://{config.host}:{config.port}/transmission/rpc"
        
        # Use parameter override or config default
        socks5_enabled = use_socks5 if use_socks5 is not None else config.use_socks5
        
        # Setup HTTP client
        if socks5_enabled:
            # Configure SOCKS5 proxy
            self.client = httpx.Client(
                proxies=f"socks5://{config.socks5_host}:{config.socks5_port}",
                timeout=config.timeout
            )
        else:
            self.client = httpx.Client(timeout=config.timeout)
    
    def _get_auth_header(self) -> Dict[str, str]:
        """Get authentication header"""
        headers = {"Content-Type": "application/json"}
        if self.config.username and self.config.password:
            import base64
            credentials = base64.b64encode(
                f"{self.config.username}:{self.config.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        if self.session_id:
            headers["X-Transmission-Session-Id"] = self.session_id
        
        return headers
    
    def _make_request(self, method: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make RPC request to Transmission"""
        payload = {
            "method": method,
            "arguments": arguments or {}
        }
        
        headers = self._get_auth_header()
        
        try:
            response = self.client.post(
                self.base_url,
                json=payload,
                headers=headers
            )
            
            # Handle 409 - update session ID
            if response.status_code == 409:
                self.session_id = response.headers.get("X-Transmission-Session-Id")
                headers = self._get_auth_header()
                response = self.client.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            raise Exception(f"Transmission RPC error: {e}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information"""
        result = self._make_request("session-get")
        return result.get("arguments", {})
    
    def list_torrents(self) -> List[Dict[str, Any]]:
        """List all torrents"""
        fields = [
            "id", "hashString", "name", "status", "downloadDir",
            "percentDone", "totalSize", "downloadedEver", "rateDownload",
            "rateUpload", "eta", "files", "peers"
        ]
        result = self._make_request("torrent-get", {"fields": fields})
        return result.get("arguments", {}).get("torrents", [])
    
    def add_torrent(self, magnet_or_url: str, download_dir: Optional[str] = None, start_torrent: bool = True, validate: bool = True) -> Dict[str, Any]:
        """Add torrent via magnet link or URL"""
        # Validate input if requested
        if validate:
            is_valid, message = validate_torrent_url(magnet_or_url)
            if not is_valid:
                return {"error": f"Validation failed: {message}"}
        
        args = {"filename": magnet_or_url}
        if download_dir:
            args["download-dir"] = download_dir
        if not start_torrent:
            args["paused"] = True
        
        result = self._make_request("torrent-add", args)
        return result.get("arguments", {})
    
    def get_torrent_details(self, torrent_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific torrent"""
        fields = [
            "id", "hashString", "name", "status", "downloadDir",
            "percentDone", "totalSize", "downloadedEver", "rateDownload",
            "rateUpload", "eta", "files", "peers", "addedDate", "startDate"
        ]
        result = self._make_request("torrent-get", {"ids": [torrent_id], "fields": fields})
        torrents = result.get("arguments", {}).get("torrents", [])
        return torrents[0] if torrents else {}
    
    def search_torrents(self, search_term: str) -> List[Dict[str, Any]]:
        """Search torrents by name"""
        all_torrents = self.list_torrents()
        search_term_lower = search_term.lower()
        return [t for t in all_torrents if search_term_lower in t.get("name", "").lower()]
    
    def start_torrent(self, torrent_ids: List[int]) -> None:
        """Start torrents"""
        self._make_request("torrent-start", {"ids": torrent_ids})
    
    def stop_torrent(self, torrent_ids: List[int]) -> None:
        """Stop torrents"""
        self._make_request("torrent-stop", {"ids": torrent_ids})
    
    def remove_torrent(self, torrent_ids: List[int], delete_data: bool = False) -> None:
        """Remove torrents"""
        args = {"ids": torrent_ids, "delete-local-data": delete_data}
        self._make_request("torrent-remove", args)
    
    def get_free_space(self, path: str = None) -> Dict[str, Any]:
        """Get free space for path"""
        session_info = self.get_session_info()
        check_path = path or session_info.get("download-dir", "/")
        result = self._make_request("free-space", {"path": check_path})
        return result.get("arguments", {})


# Initialize MCP server
server = Server("transmission-mcp-server")

# Load configuration from environment
config = TransmissionConfig(
    host=os.getenv("TRANSMISSION_HOST", "192.168.1.205"),
    port=int(os.getenv("TRANSMISSION_PORT", "9091")),
    username=os.getenv("TRANSMISSION_USERNAME", ""),
    password=os.getenv("TRANSMISSION_PASSWORD", ""),
    use_socks5=os.getenv("USE_SOCKS5", "false").lower() == "true",
    socks5_host=os.getenv("SOCKS5_HOST", "127.0.0.1"),
    socks5_port=int(os.getenv("SOCKS5_PORT", "1080")),
    timeout=int(os.getenv("TRANSMISSION_TIMEOUT", "30"))
)

# Initialize client factory function
def get_client(use_socks5: bool = False) -> TransmissionClient:
    """Get client with optional SOCKS5 override"""
    return TransmissionClient(config, use_socks5=use_socks5)


@server.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="transmission://magnet-guide",
            name="Magnet Link Format Guide",
            description="Complete guide for valid magnet link formats and hash requirements",
            mimeType="text/plain"
        ),
        Resource(
            uri="transmission://workflow-guide", 
            name="Torrent Management Workflow",
            description="Best practices for adding, managing, and organizing torrents",
            mimeType="text/plain"
        ),
        Resource(
            uri="transmission://connection-guide",
            name="Connection Setup Guide", 
            description="Guide for direct and SOCKS5 proxy connections to Transmission",
            mimeType="text/plain"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content"""
    if uri == "transmission://magnet-guide":
        return MAGNET_LINK_GUIDE
    elif uri == "transmission://workflow-guide":
        return TORRENT_WORKFLOW_GUIDE
    elif uri == "transmission://connection-guide":
        return CONNECTION_GUIDE
    else:
        raise ValueError(f"Unknown resource: {uri}")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_session_info",
            description="Get Transmission daemon session information",
            inputSchema={
                "type": "object",
                "properties": {
                    "use_socks5": {
                        "type": "boolean",
                        "description": "Use SOCKS5 proxy for this request (default: false)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="list_torrents",
            description="List all torrents with their status",
            inputSchema={
                "type": "object",
                "properties": {
                    "use_socks5": {
                        "type": "boolean",
                        "description": "Use SOCKS5 proxy for this request (default: false)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="add_torrent",
            description="Add a torrent via magnet link or URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "magnet_or_url": {
                        "type": "string",
                        "description": "Magnet link or torrent URL"
                    },
                    "download_dir": {
                        "type": "string", 
                        "description": "Optional download directory path"
                    },
                    "start_torrent": {
                        "type": "boolean",
                        "description": "Start torrent immediately after adding (default: true)"
                    },
                    "use_socks5": {
                        "type": "boolean",
                        "description": "Use SOCKS5 proxy for this request (default: false)"
                    }
                },
                "required": ["magnet_or_url"]
            }
        ),
        Tool(
            name="search_torrents",
            description="Search torrents by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Search term to find torrents"
                    },
                    "use_socks5": {
                        "type": "boolean",
                        "description": "Use SOCKS5 proxy for this request (default: false)"
                    }
                },
                "required": ["search_term"]
            }
        ),
        Tool(
            name="get_torrent_details",
            description="Get detailed information about a specific torrent",
            inputSchema={
                "type": "object",
                "properties": {
                    "torrent_id": {
                        "type": "integer",
                        "description": "Torrent ID to get details for"
                    },
                    "use_socks5": {
                        "type": "boolean",
                        "description": "Use SOCKS5 proxy for this request (default: false)"
                    }
                },
                "required": ["torrent_id"]
            }
        ),
        Tool(
            name="control_torrent",
            description="Start, stop, or remove torrents",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["start", "stop", "remove"],
                        "description": "Action to perform"
                    },
                    "torrent_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of torrent IDs"
                    },
                    "delete_data": {
                        "type": "boolean",
                        "description": "Delete local data when removing (default: false)"
                    },
                    "use_socks5": {
                        "type": "boolean",
                        "description": "Use SOCKS5 proxy for this request (default: false)"
                    }
                },
                "required": ["action", "torrent_ids"]
            }
        ),
        Tool(
            name="get_free_space",
            description="Get free space available for downloads",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to check (optional)"
                    },
                    "use_socks5": {
                        "type": "boolean",
                        "description": "Use SOCKS5 proxy for this request (default: false)"
                    }
                },
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    try:
        # Extract use_socks5 parameter
        use_socks5 = arguments.pop("use_socks5", False)
        client = get_client(use_socks5)
        
        proxy_status = "via SOCKS5" if use_socks5 else "direct"
        
        if name == "get_session_info":
            result = client.get_session_info()
            return [TextContent(
                type="text",
                text=f"Session Info ({proxy_status}):\n{json.dumps(result, indent=2)}"
            )]
        
        elif name == "list_torrents":
            torrents = client.list_torrents()
            if not torrents:
                return [TextContent(type="text", text=f"No torrents found ({proxy_status})")]
            
            output = f"Torrents ({proxy_status}):\n"
            for torrent in torrents:
                status_map = {0: "stopped", 1: "check-wait", 2: "check", 3: "download-wait", 
                            4: "download", 5: "seed-wait", 6: "seed", 7: "isolated"}
                status = status_map.get(torrent.get("status", 0), "unknown")
                progress = torrent.get("percentDone", 0) * 100
                
                output += f"ID: {torrent.get('id')}\n"
                output += f"Name: {torrent.get('name')}\n"
                output += f"Status: {status}\n"
                output += f"Progress: {progress:.1f}%\n"
                output += f"Download Dir: {torrent.get('downloadDir')}\n"
                output += "---\n"
            
            return [TextContent(type="text", text=output)]
        
        elif name == "add_torrent":
            magnet_or_url = arguments["magnet_or_url"]
            download_dir = arguments.get("download_dir")
            start_torrent = arguments.get("start_torrent", True)
            
            result = client.add_torrent(magnet_or_url, download_dir, start_torrent)
            
            if "torrent-added" in result:
                torrent = result["torrent-added"]
                status_text = "and started downloading" if start_torrent else "but not started (paused)"
                return [TextContent(
                    type="text",
                    text=f"Torrent added successfully {status_text} ({proxy_status})!\nID: {torrent.get('id')}\nName: {torrent.get('name')}"
                )]
            elif "torrent-duplicate" in result:
                torrent = result["torrent-duplicate"]
                return [TextContent(
                    type="text",
                    text=f"Torrent already exists ({proxy_status})!\nID: {torrent.get('id')}\nName: {torrent.get('name')}"
                )]
            else:
                return [TextContent(type="text", text=f"Torrent add result unclear ({proxy_status})")]
        
        elif name == "search_torrents":
            search_term = arguments["search_term"]
            torrents = client.search_torrents(search_term)
            
            if not torrents:
                return [TextContent(type="text", text=f"No torrents found matching '{search_term}' ({proxy_status})")]
            
            output = f"Found {len(torrents)} torrent(s) matching '{search_term}' ({proxy_status}):\n"
            for torrent in torrents:
                status_map = {0: "stopped", 1: "check-wait", 2: "check", 3: "download-wait", 
                            4: "download", 5: "seed-wait", 6: "seed", 7: "isolated"}
                status = status_map.get(torrent.get("status", 0), "unknown")
                progress = torrent.get("percentDone", 0) * 100
                
                output += f"ID: {torrent.get('id')}\n"
                output += f"Name: {torrent.get('name')}\n"
                output += f"Status: {status}\n"
                output += f"Progress: {progress:.1f}%\n"
                output += "---\n"
            
            return [TextContent(type="text", text=output)]
        
        elif name == "get_torrent_details":
            torrent_id = arguments["torrent_id"]
            torrent = client.get_torrent_details(torrent_id)
            
            if not torrent:
                return [TextContent(type="text", text=f"Torrent ID {torrent_id} not found ({proxy_status})")]
            
            status_map = {0: "stopped", 1: "check-wait", 2: "check", 3: "download-wait", 
                        4: "download", 5: "seed-wait", 6: "seed", 7: "isolated"}
            status = status_map.get(torrent.get("status", 0), "unknown")
            progress = torrent.get("percentDone", 0) * 100
            download_speed = torrent.get("rateDownload", 0) / (1024 * 1024)  # MB/s
            upload_speed = torrent.get("rateUpload", 0) / (1024 * 1024)  # MB/s
            total_size = torrent.get("totalSize", 0) / (1024 * 1024 * 1024)  # GB
            eta = torrent.get("eta", -1)
            
            output = f"Torrent Details ({proxy_status}):\n"
            output += f"ID: {torrent.get('id')}\n"
            output += f"Name: {torrent.get('name')}\n"
            output += f"Status: {status}\n"
            output += f"Progress: {progress:.1f}%\n"
            output += f"Size: {total_size:.2f} GB\n"
            output += f"Download Speed: {download_speed:.2f} MB/s\n"
            output += f"Upload Speed: {upload_speed:.2f} MB/s\n"
            output += f"Download Dir: {torrent.get('downloadDir')}\n"
            
            if eta > 0:
                eta_hours = eta // 3600
                eta_mins = (eta % 3600) // 60
                output += f"ETA: {eta_hours}h {eta_mins}m\n"
            elif eta == -1:
                output += "ETA: Not available\n"
            elif eta == -2:
                output += "ETA: Unknown\n"
            
            return [TextContent(type="text", text=output)]
        
        elif name == "control_torrent":
            action = arguments["action"]
            torrent_ids = arguments["torrent_ids"]
            delete_data = arguments.get("delete_data", False)
            
            if action == "start":
                client.start_torrent(torrent_ids)
                return [TextContent(type="text", text=f"Started torrents ({proxy_status}): {torrent_ids}")]
            elif action == "stop":
                client.stop_torrent(torrent_ids)
                return [TextContent(type="text", text=f"Stopped torrents ({proxy_status}): {torrent_ids}")]
            elif action == "remove":
                client.remove_torrent(torrent_ids, delete_data)
                action_text = "removed with data" if delete_data else "removed (data kept)"
                return [TextContent(type="text", text=f"Torrents {action_text} ({proxy_status}): {torrent_ids}")]
        
        elif name == "get_free_space":
            path = arguments.get("path")
            result = client.get_free_space(path)
            
            size_bytes = result.get("size-bytes", 0)
            size_gb = size_bytes / (1024**3)
            check_path = result.get("path", "default")
            
            return [TextContent(
                type="text", 
                text=f"Free space at '{check_path}' ({proxy_status}): {size_gb:.2f} GB ({size_bytes:,} bytes)"
            )]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        proxy_status = "via SOCKS5" if arguments.get("use_socks5", False) else "direct"
        return [TextContent(type="text", text=f"Error ({proxy_status}): {str(e)}")]


def main():
    """Main entry point"""
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def run_server():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
