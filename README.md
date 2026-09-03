# Railway Ticket Simulation System

A **Python + SQLite railway reservation simulation system** that demonstrates train search, fare calculation, seat allocation, PNR generation, confirmed/waitlisted bookings, ticket cancellation, automatic waitlist promotion, and basic railway administration.

> **Note:** This is an educational simulation project. It does not connect to IRCTC or any real railway reservation system and does not implement official railway booking, quota, RAC, payment, or refund rules.

---

## Features

### Passenger Features

* Search trains between two stations
* Search using source, destination, and journey date
* Check seat availability
* Select travel class
* Book tickets for **1–6 passengers**
* Automatic seat allocation
* Generate a unique PNR
* View complete ticket/PNR details
* Cancel confirmed or waitlisted tickets
* Receive simulated cancellation refunds
* Automatic waitlist promotion after confirmed-ticket cancellation

### Supported Classes

| Code | Class     | Simulated Multiplier |
| ---- | --------- | -------------------: |
| `SL` | Sleeper   |                 1.0x |
| `3A` | AC 3-Tier |                 2.1x |
| `2A` | AC 2-Tier |                 3.1x |
| `1A` | First AC  |                 4.3x |
| `CC` | Chair Car |                 1.5x |

### Administrative Features

The system also includes basic administration capabilities:

* Add stations
* Add trains
* Add route stops
* Add coaches
* Deactivate trains
* View all stations
* View all trains
* Generate system reports

---

# Project Architecture

The project follows a simple layered architecture:

```text
┌───────────────────────────────────────┐
│             CLI / Menu                │
│  Search | Book | Cancel | Admin       │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│           RailwaySystem               │
│                                       │
│ Route Search      Fare Calculation    │
│ Seat Inventory    Booking             │
│ PNR Management    Cancellation        │
│ Waitlist          Administration      │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│              Database                 │
│         SQLite + SQL Operations       │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│            railway.db                 │
│                                       │
│ Stations | Trains | Routes | Coaches  │
│ Fares | Bookings | Passengers         │
│ Waitlist                               │
└───────────────────────────────────────┘
```

---

# Technologies Used

* **Python 3.9+**
* **SQLite**
* Object-Oriented Programming
* SQL
* Python Dataclasses
* Command Line Interface

### Python Libraries

The project uses only Python's standard library:

```text
sqlite3
random
string
dataclasses
datetime
typing
```

No external packages are required.

---

# Database Design

The application uses SQLite for persistent storage.

## Main Tables

```text
stations
   │
   └── routes ──── trains
                     │
                     ├── coaches
                     │
                     ├── fares
                     │
                     └── bookings
                            │
                            ├── passengers
                            │
                            └── waitlist
```

### `stations`

Stores railway stations.

| Field  | Description         |
| ------ | ------------------- |
| `id`   | Primary key         |
| `code` | Unique station code |
| `name` | Station name        |
| `city` | City                |

### `trains`

Stores train information.

| Field        | Description                 |
| ------------ | --------------------------- |
| `id`         | Primary key                 |
| `train_no`   | Unique train number         |
| `name`       | Train name                  |
| `train_type` | Train category              |
| `active`     | Whether the train is active |

### `routes`

Stores the ordered stops of a train.

| Field         | Description                |
| ------------- | -------------------------- |
| `id`          | Primary key                |
| `train_id`    | Associated train           |
| `station_id`  | Station                    |
| `stop_no`     | Position in route          |
| `arrival`     | Arrival time               |
| `departure`   | Departure time             |
| `distance_km` | Distance from route origin |

### `coaches`

Stores coach inventory.

| Field           | Description            |
| --------------- | ---------------------- |
| `id`            | Primary key            |
| `train_id`      | Associated train       |
| `coach_code`    | Coach identifier       |
| `class_code`    | SL / 3A / 2A / 1A / CC |
| `seat_capacity` | Number of seats        |

### `fares`

Stores fare configuration.

| Field         | Description      |
| ------------- | ---------------- |
| `id`          | Primary key      |
| `train_id`    | Associated train |
| `class_code`  | Travel class     |
| `rate_per_km` | Fare rate        |
| `base_fare`   | Base fare        |

### `bookings`

Stores the main reservation record.

| Field                    | Description                      |
| ------------------------ | -------------------------------- |
| `id`                     | Primary key                      |
| `pnr`                    | Unique PNR                       |
| `train_id`               | Associated train                 |
| `journey_date`           | Journey date                     |
| `source_station_id`      | Origin                           |
| `destination_station_id` | Destination                      |
| `class_code`             | Travel class                     |
| `status`                 | CONFIRMED / WAITLIST / CANCELLED |
| `total_fare`             | Booking fare                     |
| `created_at`             | Booking timestamp                |

### `passengers`

Stores passengers associated with a booking.

It also stores their seat allocation:

```text
allocation_status
coach_code
seat_no
berth_preference
```

### `waitlist`

Stores waitlisted bookings and their queue position.

```text
booking_id
position
created_at
```

---

# Core Algorithms

## 1. Train Search

A train is considered valid only when:

```text
source.stop_no < destination.stop_no
```

This prevents a user from booking a route backwards.

Example:

```text
NDLS → GZB → AGC → JHS
```

A booking from:

```text
NDLS → AGC
```

is valid.

A booking from:

```text
AGC → NDLS
```

is not valid for that train.

---

## 2. Fare Calculation

The simulator uses:

```text
per_passenger =
    base_fare
    + (distance × rate_per_km × class_multiplier)
    + reservation_charge
    + service_charge
```

Then:

```text
total_fare = per_passenger × passenger_count
```

The current simulated service charge is:

```text
₹18 per passenger
```

Reservation charges differ by class.

> These calculations are intentionally simplified and are not official railway fares.

---

## 3. Automatic Seat Allocation

The system:

1. Retrieves coaches for the selected class.
2. Retrieves already occupied seats.
3. Creates a set of occupied `(coach, seat)` combinations.
4. Searches coaches in order.
5. Searches seats from `1` to the coach capacity.
6. Assigns the first available seat.

Example:

```text
S1-1
S1-2
S1-3
S1-4
...
```

If `S1-1` and `S1-2` are occupied, the next passenger receives:

```text
S1-3
```

---

# Booking System

A booking can contain up to **six passengers**.

Example:

```text
Passenger 1 → Arjun
Passenger 2 → Rahul
Passenger 3 → Aman
```

The system generates a PNR such as:

```text
2609034827
```

The PNR consists of:

```text
YYMMDD + 4 random digits
```

The system also checks the database for a PNR collision before accepting it.

---

# Waitlist System

When there are not enough seats for the complete passenger group, the booking is placed on the waitlist.

Example:

```text
Available seats = 2

Requested passengers = 4

Result = WAITLIST
```

A queue position is assigned:

```text
WL 1
WL 2
WL 3
...
```

The system maintains waitlist positions separately for:

```text
Train
Journey Date
Class
```

---

# Waitlist Promotion

When a confirmed booking is cancelled:

```text
Confirmed Seat
      ↓
Seat becomes available
      ↓
Check waitlist
      ↓
Select earliest eligible booking
      ↓
Check whether enough seats exist
      ↓
Allocate seats
      ↓
Change booking to CONFIRMED
      ↓
Remove waitlist entry
      ↓
Resequence remaining waitlist
```

The system promotes a complete booking group only when enough seats are available for all passengers in that booking.

---

# Cancellation

Cancellation is supported for both confirmed and waitlisted bookings.

### Confirmed Booking

The simulator returns:

```text
80% of original fare
```

### Waitlisted Booking

The simulator returns:

```text
90% of original fare
```

These percentages are project-specific simulation rules rather than official railway refund rules.

---

# Demo Data

The application automatically creates demo data when run for the first time.

## Stations

```text
NDLS - New Delhi
GZB  - Ghaziabad
CNB  - Kanpur Central
LKO  - Lucknow
ALD  - Prayagraj Junction
BSB  - Varanasi Junction
JHS  - Jhansi Junction
BPL  - Bhopal Junction
AGC  - Agra Cantt
```

## Trains

| Train   | Name                            | Route                  |
| ------- | ------------------------------- | ---------------------- |
| `12001` | Shatabdi Simulation Express     | NDLS → GZB → AGC → JHS |
| `12555` | Gomti Simulation Express        | NDLS → GZB → CNB → LKO |
| `12192` | Delhi-Bhopal Simulation Express | NDLS → AGC → JHS → BPL |
| `22416` | Kashi Simulation Express        | NDLS → GZB → ALD → BSB |

---

# Default Coach Configuration

Each demo train initially contains:

```text
S1 → Sleeper → 72 seats
S2 → Sleeper → 72 seats

B1 → 3A → 64 seats
B2 → 3A → 64 seats

A1 → 2A → 46 seats

H1 → 1A → 24 seats

C1 → CC → 78 seats
```

---

# Main Menu

When the application starts, the following menu is available:

```text
================ RAILWAY TICKET SIMULATION ================

1. Search trains
2. Check seat availability
3. Book ticket
4. Print ticket / PNR status
5. Cancel ticket
6. List stations
7. List trains
8. System report
9. Admin: add station
10. Admin: add train
11. Admin: add route stop
12. Admin: add coach
13. Admin: deactivate train
0. Exit
```

---

# Example Workflow

## Step 1 — Search for a Train

Select:

```text
1. Search trains
```

Enter:

```text
Source station code: NDLS
Destination station code: AGC
Journey date: 2026-09-10
```

The system searches the database and displays matching trains.

---

## Step 2 — Book a Ticket

Select:

```text
3. Book ticket
```

Example:

```text
Train number: 12001
Journey date: 2026-09-10
Source station code: NDLS
Destination station code: AGC
Class: SL
Number of passengers: 1
```

Passenger details are entered next.

The system calculates the fare and asks for confirmation.

---

## Step 3 — Receive PNR

After successful booking:

```text
Booking successful.
Your PNR is: 2609101234
```

The ticket is then printed automatically.

---

## Step 4 — Retrieve Ticket

Select:

```text
4. Print ticket / PNR status
```

Enter:

```text
2609101234
```

The system displays:

```text
PNR
Train
Journey Date
Route
Class
Booking Status
Fare
Passenger Details
Coach
Seat
```

---

## Step 5 — Cancel Ticket

Select:

```text
5. Cancel ticket
```

Enter the PNR.

The booking is marked:

```text
CANCELLED
```

and the simulated refund is displayed.

If a waitlisted booking becomes eligible, the system automatically promotes it.

---

# Installation

## Requirements

Install:

```text
Python 3.9 or newer
```

No external package installation is necessary.

Check your Python version:

```bash
python --version
```

or:

```bash
python3 --version
```

---

# Running the Project

Clone the repository:

```bash
git clone https://github.com/your-username/railway-ticket-simulation.git
```

Move into the project:

```bash
cd railway-ticket-simulation
```

Run:

```bash
python railway_ticket_system.py
```

On macOS/Linux, you can also use:

```bash
python3 railway_ticket_system.py
```

---

# Database

The application automatically creates:

```text
railway.db
```

The database is created in the current project directory.

You do **not** need to create the database manually.

The database persists between executions, meaning bookings and administrative changes remain available when the program is restarted.

---

# Project Structure

```text
railway-ticket-simulation/
│
├── railway_ticket_system.py
├── railway.db
├── README.md
├── PROJECT_DESIGN.md
└── Documentation/
    └── Railway_Ticket_Simulation_Documentation.docx
```

> `railway.db` is generated automatically after the first execution and can be excluded from Git if you want a clean repository.

Recommended `.gitignore`:

```gitignore
__pycache__/
*.pyc
railway.db
.venv/
venv/
.env
.DS_Store
```

---

# Concepts Demonstrated

This project is useful as a college-level demonstration of several programming and computer science concepts.

### Python

* Functions
* Classes
* Dataclasses
* Exception handling
* Type hints
* Lists
* Sets
* Dictionaries
* String formatting
* Date/time processing

### Object-Oriented Programming

The system separates responsibilities into classes such as:

```python
Database
RailwaySystem
Passenger
SearchResult
```

### Database Management

The project demonstrates:

* Tables
* Primary keys
* Foreign keys
* Unique constraints
* SQL joins
* Indexes
* CRUD-style operations
* Persistent storage

### Data Structures

Examples include:

```text
List       → passengers / search results
Set        → occupied seats
Dictionary → classes and fare configuration
Queue-like ordering → waitlist
```

### Algorithms

The application demonstrates:

* Route searching
* First-available-seat allocation
* Waitlist ordering
* Waitlist promotion
* Waitlist resequencing
* Fare calculation
* PNR uniqueness checking

---

# Error Handling

The application handles common problems such as:

* Invalid dates
* Past journey dates
* Unknown stations
* Unknown trains
* Invalid class codes
* Invalid PNRs
* Duplicate records
* More than six passengers
* Empty passenger bookings
* Repeated cancellation
* Invalid numerical input

The interactive menu catches errors and allows the application to continue running instead of terminating immediately.

---

# Testing Scenarios

Recommended tests include:

| Test                                   | Expected Result           |
| -------------------------------------- | ------------------------- |
| Search valid route                     | Matching train displayed  |
| Search reversed route                  | No valid route            |
| Book available seat                    | CONFIRMED                 |
| Book beyond capacity                   | WAITLIST                  |
| Retrieve valid PNR                     | Ticket displayed          |
| Retrieve invalid PNR                   | PNR not found             |
| Cancel confirmed booking               | CANCELLED + refund        |
| Cancel waitlisted booking              | Removed from waitlist     |
| Cancel confirmed booking with waitlist | Eligible booking promoted |
| Cancel same ticket twice               | Error                     |
| Duplicate station                      | Database constraint error |
| Invalid numeric input                  | Input requested again     |

---

# Current Limitations

This is a simulation rather than a production railway reservation platform.

The project currently does not implement:

* Real railway/IRCTC API integration
* Online payments
* User authentication
* Admin authentication
* Real-time train availability
* Official railway fare rules
* Quotas
* Full RAC functionality
* Automated chart preparation
* Train operating days
* Notifications
* Email/SMS integration
* Graphical user interface
* Web interface
* Mobile application
* Distributed/concurrent booking infrastructure
* Production-grade transactional concurrency
* Advanced berth-preference allocation

The stored berth preference is currently informational; the seat allocation algorithm uses a first-free-seat strategy.

---

# Future Improvements

Possible extensions include:

### GUI

Build a graphical interface with:

```text
Tkinter
PyQt
CustomTkinter
```

### Web Application

Convert the system into a web application using:

```text
Flask
Django
FastAPI
```

### Authentication

Add:

```text
User Registration
Login
Password Hashing
Admin Roles
Passenger Profiles
```

### Payment Simulation

Add:

```text
Payment Gateway Simulation
Transaction ID
Payment Status
Invoice
Refund Records
```

### Advanced Reservation Logic

Implement:

```text
RAC
Quota
Tatkal-style simulation
Dynamic seat inventory
Berth preference matching
Group allocation
Partial waitlist promotion
```

### API

Expose functionality through REST endpoints:

```text
GET  /trains
GET  /availability
POST /bookings
GET  /bookings/{pnr}
POST /bookings/{pnr}/cancel
```

### Testing

Add automated testing using:

```text
pytest
```

with unit and integration test suites.

---

# Security Considerations

The current application is intended for local educational use.

For a production version, security improvements would include:

* Authentication
* Authorization
* Password hashing
* Input sanitization
* Audit logs
* Secure payment processing
* Rate limiting
* Database transaction management
* Concurrent booking protection
* Secure API authentication

---

# Performance Considerations

The project is designed for small educational datasets.

The PNR field has an index, allowing efficient PNR lookup.

Seat allocation uses a set of occupied seats so membership checks are efficient:

```python
if (coach_code, seat_no) not in taken:
```

The current design is appropriate for a local simulation but would require more sophisticated inventory and concurrency management at production scale.

---

# Disclaimer

This project is intended **strictly for educational and demonstration purposes**.

It is not affiliated with:

* Indian Railways
* IRCTC
* Ministry of Railways
* Any railway reservation authority

All train names, fares, reservation rules, refund percentages, PNR generation rules, and seat-allocation behavior are simulated.

---

# License

You can add a license appropriate for your use case.

For an open-source academic project, a common choice is the MIT License.

Example:

```text
MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files, to deal in the Software
without restriction...
```

---

# Author

**Railway Ticket Simulation System**

Built as an academic Python + SQLite project demonstrating:

```text
Python
OOP
SQL
Database Design
Data Structures
Algorithms
Software Engineering
```

---

## ⭐ If You Find This Project Useful

Consider giving the repository a star and using it as a starting point for your own railway reservation, transportation, or database-management projects.
