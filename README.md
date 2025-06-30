# Transmission MCP Server

A simple MCP server for controlling your Transmission torrent daemon. Supports both direct connection and SOCKS5 proxy for remote access.

## Quick Setup

1. **Clone and setup:**
   ```bash
   git clone <this-repo>
   cd transmission-mcp-server
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Claude Desktop:**
   
   Copy the configuration from `claude-desktop-config.json` to your Claude Desktop config file:
   
   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   
   **Important**: Update the paths to match your system and use the venv Python:
   `/path/to/transmission-mcp-server/venv/bin/python`
   ```json
   {
     "mcpServers": {
       "transmission": {
         "command": "/path/to/transmission-mcp-server/venv/bin/python",
         "args": ["/path/to/transmission-mcp-server/src/server.py"],
         "env": {
           "TRANSMISSION_HOST": "192.168.1.205",
           "TRANSMISSION_PORT": "9091",
           "TRANSMISSION_USERNAME": "your_username",
           "TRANSMISSION_PASSWORD": "your_password",
           "USE_SOCKS5": "false"
         }
       }
     }
   }
   ```

3. **For SOCKS5 proxy usage** (when away from home):
   Use the `use_socks5: true` parameter in your commands to Claude

## Environment Variables

- `TRANSMISSION_HOST`: IP address of Transmission daemon (default: 192.168.1.205)
- `TRANSMISSION_PORT`: Port number (default: 9091)
- `TRANSMISSION_USERNAME`: Username for authentication
- `TRANSMISSION_PASSWORD`: Password for authentication
- `USE_SOCKS5`: Enable SOCKS5 proxy (true/false, default: false)
- `SOCKS5_HOST`: SOCKS5 proxy host (default: 127.0.0.1)
- `SOCKS5_PORT`: SOCKS5 proxy port (default: 1080)
- `TRANSMISSION_TIMEOUT`: Request timeout in seconds (default: 30)

## Available Tools

### `add_torrent`
Add a new torrent via magnet link or URL.
- `magnet_or_url`: Magnet link or torrent file URL
- `download_dir`: Optional custom download directory
- `use_socks5`: Use SOCKS5 proxy for this request (default: false)

### `control_torrent`
Start, stop, or remove torrents.
- `action`: "start", "stop", or "remove"
- `torrent_ids`: Array of torrent IDs
- `delete_data`: Whether to delete local data when removing (default: false)
- `use_socks5`: Use SOCKS5 proxy for this request (default: false)

### `get_free_space`
Check available disk space for downloads.
- `path`: Optional directory path to check
- `use_socks5`: Use SOCKS5 proxy for this request (default: false)

### `list_torrents`  
List all torrents with their status, progress, and download directories.
- `use_socks5`: Use SOCKS5 proxy for this request (default: false)

### `get_session_info`
Get information about the Transmission daemon session, including version, settings, and statistics.
- `use_socks5`: Use SOCKS5 proxy for this request (default: false)

## Usage Examples

After setting up Claude Desktop, you can use these commands:

**Direct connection (local network):**
- "Show me all my torrents"
- "Add this magnet link: magnet:?xt=urn:btih:..."
- "Stop torrent ID 5"
- "How much free space do I have?"

**Via SOCKS5 proxy (remote access):**
- "Use SOCKS5 to show me all my torrents"
- "Use SOCKS5 proxy to add this magnet link: magnet:?xt=urn:btih:..."
- "Use SOCKS5 to stop torrent ID 5"
- "Use SOCKS5 to get free space"

## Network Setup

### Direct Connection (Local Network)
Use when your laptop is on the same network as the Transmission server.

### SOCKS5 Proxy (Remote Access)
Set up a SOCKS5 tunnel when away from home, then use `use_socks5: true` in your commands:

```bash
# SSH tunnel with SOCKS5
ssh -D 1080 -N user@your-home-server.com
```

Then tell Claude: *"Use SOCKS5 to add this magnet link..."*

## Troubleshooting

### Connection Issues
- Verify Transmission daemon is running and accessible
- Check firewall settings on the Transmission server
- Ensure RPC is enabled in Transmission settings
- Verify username/password if authentication is required

### SOCKS5 Issues  
- Confirm SOCKS5 proxy is running on specified host:port
- Test SOCKS5 connectivity with another tool first
- Check if authentication is required for your SOCKS5 proxy

### Authentication Issues
- Verify username/password in environment variables
- Check if Transmission requires authentication
- Ensure RPC whitelist includes your client IP

## Development

The server is contained in a single file (`src/server.py`) for simplicity. It uses:
- `httpx` for HTTP requests
- `pydantic` for configuration management  
- `mcp` for the Model Context Protocol integration

## License

MIT License - see LICENSE file for details.
