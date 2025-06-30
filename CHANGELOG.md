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
