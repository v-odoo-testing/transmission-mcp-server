# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial implementation of Transmission MCP Server
- Support for direct connection to Transmission daemon
- Support for SOCKS5 proxy connection for remote access
- Basic authentication with username/password
- Session ID management for CSRF protection
- Core torrent management tools:
  - `get_session_info`: Get daemon information and statistics
  - `list_torrents`: List all torrents with status and progress  
  - `add_torrent`: Add torrents via magnet link or URL
  - `control_torrent`: Start, stop, or remove torrents
  - `get_free_space`: Check available disk space
- Environment variable configuration
- Claude Desktop integration with dual configs (direct/SOCKS5)

### Technical Details
- Single-file implementation for simplicity
- httpx client with proxy support
- Pydantic configuration management
- MCP protocol integration
- Error handling for common RPC scenarios

## [0.1.0] - 2025-06-30

### Added
- Initial project structure
- Requirements and configuration files
- Implementation plan and documentation
- Claude Desktop configuration templates


## [0.1.0] - 2025-06-30

### Added
- Complete single-file MCP server implementation (`src/server.py`)
- TransmissionClient class with RPC communication
- Support for direct HTTP connection to Transmission daemon  
- Support for SOCKS5 proxy connection for remote access
- Basic authentication with username/password
- Session ID management for CSRF protection (X-Transmission-Session-Id)
- Environment variable configuration system

### MCP Tools Implemented
- `get_session_info`: Retrieve Transmission daemon information and settings
- `list_torrents`: List all torrents with status, progress, and directories
- `add_torrent`: Add torrents via magnet links or URLs with optional download directory
- `control_torrent`: Start, stop, or remove torrents with data deletion option
- `get_free_space`: Check available disk space for downloads

### Infrastructure
- Simple setup: git clone → venv → pip install requirements
- Claude Desktop integration with dual configurations (direct/SOCKS5)
- Test connection utility script
- Complete documentation and setup guide
- GitHub repository created at v-odoo-testing/transmission-mcp-server

### Technical Implementation
- httpx HTTP client with proxy support
- Pydantic configuration management
- Error handling for common RPC scenarios (409 session refresh)
- Status code mapping for torrent states
- Graceful error reporting through MCP tools

### Configuration Options
- TRANSMISSION_HOST/PORT: Daemon connection details
- TRANSMISSION_USERNAME/PASSWORD: Authentication credentials  
- USE_SOCKS5: Enable/disable SOCKS5 proxy mode
- SOCKS5_HOST/PORT: Proxy server configuration
- TRANSMISSION_TIMEOUT: Request timeout settings
