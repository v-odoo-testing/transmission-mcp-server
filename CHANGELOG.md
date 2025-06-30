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

### Fixed
- Claude Desktop configuration now correctly uses virtual environment Python
- Updated README with proper venv/bin/python path examples
- Removed any Windows references (macOS/Linux only)

### Changed
- **BREAKING**: Simplified to single MCP server configuration
- SOCKS5 is now a runtime parameter (`use_socks5: true`) in tool calls
- Removed duplicate server configs - one server handles both direct and proxy
- All tools now accept optional `use_socks5` parameter
- Responses indicate connection method used ("direct" or "via SOCKS5")

### Improved
- Cleaner Claude Desktop configuration with single server entry
- Runtime connection switching without restart
- More intuitive usage: "Use SOCKS5 to add torrent..." 
- Better error messages showing connection method used

### Added
- **search_torrents** tool: Search torrents by name instead of using external Python scripts
- **get_torrent_details** tool: Get detailed information about specific torrents by ID
- **Auto-start option**: add_torrent now has `start_torrent` parameter (default: true)
  - Set `start_torrent: false` to add without starting
  - Default behavior starts torrents immediately after adding

### Improved
- Enhanced add_torrent tool with better control over torrent startup
- Eliminated need for external Python scripts for common operations
- Better status reporting with download speeds, sizes, and ETAs
- More comprehensive torrent information display

### Fixed
- No longer need to execute Python code for searching torrents
- No longer need to execute Python code for getting torrent details
- Cleaner separation between MCP tools and implementation

### Added
- **MCP Resources**: Three comprehensive reference guides now available in Claude Desktop
  - **Magnet Link Format Guide**: Proper hash formats, validation rules, examples
  - **Torrent Management Workflow**: Best practices, directory structure, status codes  
  - **Connection Setup Guide**: Direct and SOCKS5 configuration, troubleshooting
- **Input Validation**: Magnet link and torrent URL validation to catch errors early
- **Enhanced Error Messages**: Clear feedback on invalid magnet links and URLs

### Improved
- **Knowledge Base**: Prevents fundamental errors (like fake hashes) through accessible documentation
- **First-Time Success**: Resources provide the knowledge needed to get things right immediately
- **Better UX**: No more wasted attempts due to invalid input formats

### Developer Experience
- Resources appear in Claude Desktop interface under "PROVIDED RESOURCES"
- Eliminates need for trial-and-error with magnet link formats
- Comprehensive troubleshooting and configuration guidance

### Fixed
- **CRITICAL**: add_torrent now properly starts torrents by default
  - Always explicitly sets `paused` parameter to override daemon defaults
  - `start_torrent: true` (default) → `paused: false` (force start)
  - `start_torrent: false` → `paused: true` (add paused)
  - No longer relies on daemon's `start-added-torrents` setting
  - Fixes issue where torrents were added but not started despite `start_torrent: true`

### Technical Details
- Previous logic only set `paused: true` when `start_torrent: false`
- Left `start_torrent: true` cases to daemon default (which was `false`)
- Now always explicitly controls torrent start behavior
- Ensures consistent behavior regardless of daemon configuration
