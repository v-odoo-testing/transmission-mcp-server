#!/usr/bin/env python3
"""
Transmission MCP Server

A simple MCP server for controlling Transmission torrent daemon.
Supports direct connection and SOCKS5 proxy.
"""

import json
import os
import sys
from typing import Optional, Dict, Any, List
import httpx
import socks
import socket
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel


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
    
    def add_torrent(self, magnet_or_url: str, download_dir: Optional[str] = None) -> Dict[str, Any]:
        """Add torrent via magnet link or URL"""
        args = {"filename": magnet_or_url}
        if download_dir:
            args["download-dir"] = download_dir
        
        result = self._make_request("torrent-add", args)
        return result.get("arguments", {})
    
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
                    "use_socks5": {
                        "type": "boolean",
                        "description": "Use SOCKS5 proxy for this request (default: false)"
                    }
                },
                "required": ["magnet_or_url"]
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
            
            result = client.add_torrent(magnet_or_url, download_dir)
            
            if "torrent-added" in result:
                torrent = result["torrent-added"]
                return [TextContent(
                    type="text",
                    text=f"Torrent added successfully ({proxy_status})!\nID: {torrent.get('id')}\nName: {torrent.get('name')}"
                )]
            elif "torrent-duplicate" in result:
                torrent = result["torrent-duplicate"]
                return [TextContent(
                    type="text",
                    text=f"Torrent already exists ({proxy_status})!\nID: {torrent.get('id')}\nName: {torrent.get('name')}"
                )]
            else:
                return [TextContent(type="text", text=f"Torrent add result unclear ({proxy_status})")]
        
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
