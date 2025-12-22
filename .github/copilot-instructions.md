# GitHub Copilot Instructions for Python Stadium Management System

## Project Overview
This is a socket-based client-server application for managing stadium venue reservations. It uses a custom JSON-based protocol over TCP.
- **Server**: Python socket server with SQLite database (`backend/server/server.py`).
- **Client**: Python Tkinter/GUI application (inferred from `client/` structure, though GUI code wasn't fully inspected, `client/` contains `home.py`, `log_in.py`).
- **Database**: SQLite (`backend/database/stadium.db` - inferred).

## Architecture & Patterns

### Communication Protocol
- **Transport**: TCP Sockets.
- **Format**: JSON strings.
- **Request Structure**: `{"action": "string", "data": { ... }}`.
- **Response Structure**: `{"status": "success"|"error", "message": "...", "data": ...}`.
- **Encoding**: UTF-8.

### Backend (`backend/`)
- **Entry Point**: `backend/server/server.py`.
- **Database Access**: `backend/server/db_manager.py` handles all SQL operations.
- **Schema**: Defined in `backend/database/schema.sql`.
- **Concurrency**: Threaded request handling (`threading.Thread` per client).

### Database Schema Key Concepts
- **Users**: Roles include `student`, `teacher`, `admin`.
- **Credit System**: Users have a `credit_score`. No-shows reduce score; check-ins maintain it.
- **Venues & Courts**: Hierarchical structure (Venue -> Courts).
- **Time Slots**: Pre-defined slots for booking.
- **Reservations**: Link Users to Time Slots.
- **Class Schedules**: Teachers can block slots for classes.

### Client (`client/`)
- **Structure**: Separate files for different views (`log_in.py`, `home.py`, `admin.py`).
- **Communication**: Likely uses a helper class to send JSON requests to the server.

## Developer Workflow

### Running the System
1.  **Initialize Database**: Run `backend/database/init_db.py` (or similar) to create tables from `schema.sql`.
2.  **Start Server**: Run `python backend/server/server.py`.
3.  **Start Client**: Run `python client/log_in.py` (or the main entry point).

### Common Tasks
- **Adding a new API**:
    1.  Define `action` name.
    2.  Add method in `SportsVenueServer` class in `server.py`.
    3.  Add dispatch logic in `process_request`.
    4.  Implement DB logic in `DBManager`.
    5.  Call from client.

## Specific Conventions
- **JSON Handling**: Use `ensure_ascii=False` in `json.dumps` to support Chinese characters in responses.
- **Error Handling**: Wrap server actions in try-except blocks and return JSON with `"status": "error"`.
- **Paths**: Use `os.path` and `sys.path` manipulation to handle imports between `backend` and `server` modules.

## Critical Files
- `backend/database/schema.sql`: The source of truth for data models.
- `backend/server/server.py`: The API definition and request router.
- `backend/server/db_manager.py`: Database interaction layer.
