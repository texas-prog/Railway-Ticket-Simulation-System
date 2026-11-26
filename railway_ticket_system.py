#!/usr/bin/env python3
"""
Railway Ticket Simulation System

A detailed educational railway reservation simulator using:
- Python OOP
- SQLite database
- Train and station search
- Seat inventory and coach allocation
- Fare calculation
- Confirmed / RAC-like / waitlist simulation
- PNR generation
- Booking history
- Ticket cancellation + refund
- Admin train / station / route management
- Seed demo data
- Interactive CLI

This is a simulation for learning purposes and does not represent
real railway/IRCTC reservation, quota, refund, or fare rules.
"""

from __future__ import annotations

import sqlite3
import random
import string
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


DB_NAME = "railway.db"

# Utilities #

def money(amount: float) -> str:
    return f"₹{amount:,.2f}"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_date(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def generate_pnr() -> str:
    # 10-character simulation PNR
    prefix = datetime.now().strftime("%y%m%d")
    suffix = "".join(random.choices(string.digits, k=4))
    return prefix + suffix


def ask_int(prompt: str, minimum=None, maximum=None) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a valid integer.")
            continue

        if minimum is not None and value < minimum:
            print(f"Value must be >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Value must be <= {maximum}.")
            continue
        return value


def ask_float(prompt: str, minimum=None) -> float:
    while True:
        raw = input(prompt).strip()
        try:
            value = float(raw)
        except ValueError:
            print("Please enter a valid number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Value must be >= {minimum}.")
            continue
        return value


# Data classes #

@dataclass
class Passenger:
    name: str
    age: int
    gender: str
    berth_preference: str = "No Preference"


@dataclass
class SearchResult:
    train_id: int
    train_no: str
    train_name: str
    departure: str
    arrival: str
    source: str
    destination: str
    duration_hours: float

# Database #

class Database:
    def __init__(self, db_name: str = DB_NAME):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_schema()

    def create_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            city TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_no TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            train_type TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_id INTEGER NOT NULL,
            station_id INTEGER NOT NULL,
            stop_no INTEGER NOT NULL,
            arrival TEXT,
            departure TEXT,
            distance_km REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(train_id) REFERENCES trains(id) ON DELETE CASCADE,
            FOREIGN KEY(station_id) REFERENCES stations(id) ON DELETE CASCADE,
            UNIQUE(train_id, stop_no)
        );

        CREATE TABLE IF NOT EXISTS coaches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_id INTEGER NOT NULL,
            coach_code TEXT NOT NULL,
            class_code TEXT NOT NULL,
            seat_capacity INTEGER NOT NULL,
            FOREIGN KEY(train_id) REFERENCES trains(id) ON DELETE CASCADE,
            UNIQUE(train_id, coach_code)
        );

        CREATE TABLE IF NOT EXISTS fares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_id INTEGER NOT NULL,
            class_code TEXT NOT NULL,
            rate_per_km REAL NOT NULL,
            base_fare REAL NOT NULL DEFAULT 50,
            FOREIGN KEY(train_id) REFERENCES trains(id) ON DELETE CASCADE,
            UNIQUE(train_id, class_code)
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnr TEXT NOT NULL UNIQUE,
            train_id INTEGER NOT NULL,
            journey_date TEXT NOT NULL,
            source_station_id INTEGER NOT NULL,
            destination_station_id INTEGER NOT NULL,
            class_code TEXT NOT NULL,
            status TEXT NOT NULL,
            total_fare REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(train_id) REFERENCES trains(id),
            FOREIGN KEY(source_station_id) REFERENCES stations(id),
            FOREIGN KEY(destination_station_id) REFERENCES stations(id)
        );

        CREATE TABLE IF NOT EXISTS passengers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            passenger_no INTEGER NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            berth_preference TEXT NOT NULL,
            allocation_status TEXT NOT NULL,
            coach_code TEXT,
            seat_no INTEGER,
            fare REAL NOT NULL,
            FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_bookings_pnr ON bookings(pnr);
        CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(journey_date);
        CREATE INDEX IF NOT EXISTS idx_passengers_booking ON passengers(booking_id);
        """)

    def execute(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def executemany(self, sql, seq):
        cur = self.conn.executemany(sql, seq)
        self.conn.commit()
        return cur

    def query_one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def query_all(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def close(self):
        self.conn.close()

# Core system #

class RailwaySystem:
    CLASS_INFO = {
        "SL": {"name": "Sleeper", "multiplier": 1.0},
        "3A": {"name": "AC 3-Tier", "multiplier": 2.1},
        "2A": {"name": "AC 2-Tier", "multiplier": 3.1},
        "1A": {"name": "First AC", "multiplier": 4.3},
        "CC": {"name": "Chair Car", "multiplier": 1.5},
    }

    BERTHS = ["Lower", "Middle", "Upper", "Side Lower", "Side Upper"]

    def __init__(self, db: Database):
        self.db = db

    # Demo data #

    def seed_demo_data(self):
        station_count = self.db.query_one(
            "SELECT COUNT(*) AS c FROM stations"
        )["c"]

        if station_count == 0:
            stations = [
                ("NDLS", "New Delhi", "Delhi"),
                ("GZB", "Ghaziabad", "Ghaziabad"),
                ("CNB", "Kanpur Central", "Kanpur"),
                ("LKO", "Lucknow", "Lucknow"),
                ("ALD", "Prayagraj Junction", "Prayagraj"),
                ("BSB", "Varanasi Junction", "Varanasi"),
                ("JHS", "Jhansi Junction", "Jhansi"),
                ("BPL", "Bhopal Junction", "Bhopal"),
                ("AGC", "Agra Cantt", "Agra"),
            ]
            self.db.executemany(
                "INSERT INTO stations(code, name, city) VALUES (?, ?, ?)",
                stations
            )

        train_count = self.db.query_one(
            "SELECT COUNT(*) AS c FROM trains"
        )["c"]

        if train_count == 0:
            trains = [
                ("12001", "Shatabdi Simulation Express", "Shatabdi"),
                ("12555", "Gomti Simulation Express", "Superfast"),
                ("12192", "Delhi-Bhopal Simulation Express", "Superfast"),
                ("22416", "Kashi Simulation Express", "Superfast"),
            ]
            for item in trains:
                self.db.execute(
                    "INSERT INTO trains(train_no, name, train_type) VALUES (?, ?, ?)",
                    item
                )

        # Add routes if missing
        self._seed_routes_and_coaches()

        print("\nDemo data is ready.")

    def _station_id(self, code: str) -> int:
        row = self.db.query_one(
            "SELECT id FROM stations WHERE code = ?", (code.upper(),)
        )
        if not row:
            raise ValueError(f"Unknown station code: {code}")
        return row["id"]

    def _train_id(self, train_no: str) -> int:
        row = self.db.query_one(
            "SELECT id FROM trains WHERE train_no = ?", (train_no,)
        )
        if not row:
            raise ValueError(f"Unknown train number: {train_no}")
        return row["id"]

    def _seed_routes_and_coaches(self):
        route_count = self.db.query_one(
            "SELECT COUNT(*) AS c FROM routes"
        )["c"]

        if route_count == 0:
            route_data = {
                "12001": [
                    ("NDLS", "06:00", "06:00", 0),
                    ("GZB", "06:28", "06:30", 25),
                    ("AGC", "08:00", "08:05", 195),
                    ("JHS", "10:15", "10:20", 470),
                ],
                "12555": [
                    ("NDLS", "18:30", "18:30", 0),
                    ("GZB", "19:00", "19:02", 25),
                    ("CNB", "23:15", "23:25", 440),
                    ("LKO", "01:30", "01:40", 510),
                ],
                "12192": [
                    ("NDLS", "21:00", "21:00", 0),
                    ("AGC", "23:05", "23:10", 195),
                    ("JHS", "01:20", "01:25", 450),
                    ("BPL", "05:30", "05:35", 700),
                ],
                "22416": [
                    ("NDLS", "11:40", "11:40", 0),
                    ("GZB", "12:10", "12:12", 25),
                    ("ALD", "18:00", "18:05", 600),
                    ("BSB", "20:30", "20:40", 730),
                ],
            }
            for train_no, stops in route_data.items():
                tid = self._train_id(train_no)
                for idx, (code, arr, dep, distance) in enumerate(stops, 1):
                    sid = self._station_id(code)
                    self.db.execute(
                        """
                        INSERT INTO routes
                        (train_id, station_id, stop_no, arrival, departure, distance_km)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (tid, sid, idx, arr, dep, distance)
                    )

        # Coaches and fares
        for train in self.db.query_all("SELECT * FROM trains"):
            train_id = train["id"]
            coach_exists = self.db.query_one(
                "SELECT 1 FROM coaches WHERE train_id = ? LIMIT 1", (train_id,)
            )
            if not coach_exists:
                coach_plan = [
                    ("S1", "SL", 72),
                    ("S2", "SL", 72),
                    ("B1", "3A", 64),
                    ("B2", "3A", 64),
                    ("A1", "2A", 46),
                    ("H1", "1A", 24),
                    ("C1", "CC", 78),
                ]
                self.db.executemany(
                    """
                    INSERT INTO coaches(train_id, coach_code, class_code, seat_capacity)
                    VALUES (?, ?, ?, ?)
                    """,
                    [(train_id, *x) for x in coach_plan]
                )

            fare_exists = self.db.query_one(
                "SELECT 1 FROM fares WHERE train_id = ? LIMIT 1", (train_id,)
            )
            if not fare_exists:
                rate = {
                    "SL": 1.40,
                    "3A": 2.75,
                    "2A": 4.20,
                    "1A": 6.20,
                    "CC": 2.20,
                }
                for code, value in rate.items():
                    self.db.execute(
                        """
                        INSERT INTO fares(train_id, class_code, rate_per_km, base_fare)
                        VALUES (?, ?, ?, ?)
                        """,
                        (train_id, code, value, 75)
                    )

    # Search #

    def search_trains(
        self,
        source_code: str,
        destination_code: str,
        date_str: str
    ) -> list[SearchResult]:
        source = source_code.upper()
        destination = destination_code.upper()

        if not parse_date(date_str):
            raise ValueError("Journey date must be YYYY-MM-DD.")

        rows = self.db.query_all(
            """
            SELECT
                t.id AS train_id,
                t.train_no,
                t.name AS train_name,
                s1.code AS source_code,
                s2.code AS destination_code,
                r1.departure AS departure,
                r2.arrival AS arrival,
                r1.distance_km AS source_distance,
                r2.distance_km AS destination_distance
            FROM trains t
            JOIN routes r1 ON r1.train_id = t.id
            JOIN stations s1 ON s1.id = r1.station_id
            JOIN routes r2 ON r2.train_id = t.id
            JOIN stations s2 ON s2.id = r2.station_id
            WHERE t.active = 1
              AND s1.code = ?
              AND s2.code = ?
              AND r1.stop_no < r2.stop_no
            ORDER BY r1.departure
            """,
            (source, destination)
        )

        results = []
        for row in rows:
            duration = self._duration_hours(
                row["departure"], row["arrival"]
            )
            results.append(
                SearchResult(
                    train_id=row["train_id"],
                    train_no=row["train_no"],
                    train_name=row["train_name"],
                    departure=row["departure"],
                    arrival=row["arrival"],
                    source=row["source_code"],
                    destination=row["destination_code"],
                    duration_hours=duration,
                )
            )
        return results

    @staticmethod
    def _duration_hours(departure: str, arrival: str) -> float:
        fmt = "%H:%M"
        dep = datetime.strptime(departure, fmt)
        arr = datetime.strptime(arrival, fmt)
        if arr < dep:
            arr += timedelta(days=1)
        return round((arr - dep).seconds / 3600, 2)

    def get_route_distance(
        self, train_id: int, source_code: str, destination_code: str
    ) -> float:
        row = self.db.query_one(
            """
            SELECT r2.distance_km - r1.distance_km AS km
            FROM routes r1
            JOIN routes r2 ON r1.train_id = r2.train_id
            JOIN stations s1 ON s1.id = r1.station_id
            JOIN stations s2 ON s2.id = r2.station_id
            WHERE r1.train_id = ?
              AND s1.code = ?
              AND s2.code = ?
              AND r1.stop_no < r2.stop_no
            """,
            (train_id, source_code.upper(), destination_code.upper())
        )
        if not row:
            raise ValueError("Invalid route segment.")
        return float(row["km"])

    def list_stations(self):
        rows = self.db.query_all(
            "SELECT code, name, city FROM stations ORDER BY code"
        )
        print("\nStations")
        print("-" * 70)
        for row in rows:
            print(f"{row['code']:5} | {row['name']}, {row['city']}")

    #  Fare  #

    def calculate_fare(
        self,
        train_id: int,
        source_code: str,
        destination_code: str,
        class_code: str,
        passenger_count: int
    ) -> float:
        class_code = class_code.upper()
        if class_code not in self.CLASS_INFO:
            raise ValueError("Unsupported class.")

        distance = self.get_route_distance(
            train_id, source_code, destination_code
        )
        fare = self.db.query_one(
            """
            SELECT rate_per_km, base_fare
            FROM fares
            WHERE train_id = ? AND class_code = ?
            """,
            (train_id, class_code)
        )
        if not fare:
            raise ValueError("Fare is not configured for this train/class.")

        per_passenger = (
            fare["base_fare"]
            + distance * fare["rate_per_km"] * self.CLASS_INFO[class_code]["multiplier"]
        )

        # Small simulation components
        reservation_charge = {
            "SL": 20,
            "3A": 40,
            "2A": 50,
            "1A": 60,
            "CC": 35,
        }[class_code]

        service_charge = 18
        total = passenger_count * (
            per_passenger + reservation_charge + service_charge
        )
        return round(total, 2)

    #  Inventory  #

    def class_capacity(self, train_id: int, class_code: str) -> int:
        row = self.db.query_one(
            """
            SELECT COALESCE(SUM(seat_capacity), 0) AS cap
            FROM coaches
            WHERE train_id = ? AND class_code = ?
            """,
            (train_id, class_code.upper())
        )
        return int(row["cap"])

    def active_booked_seat_count(
        self, train_id: int, date_str: str, class_code: str
    ) -> int:
        row = self.db.query_one(
            """
            SELECT COUNT(*) AS c
            FROM passengers p
            JOIN bookings b ON b.id = p.booking_id
            WHERE b.train_id = ?
              AND b.journey_date = ?
              AND b.class_code = ?
              AND b.status = 'CONFIRMED'
              AND p.allocation_status = 'CONFIRMED'
            """,
            (train_id, date_str, class_code.upper())
        )
        return int(row["c"])

    def inventory_status(
        self, train_id: int, date_str: str, class_code: str
    ):
        capacity = self.class_capacity(train_id, class_code)
        confirmed = self.active_booked_seat_count(
            train_id, date_str, class_code
        )
        waitlisted = self.db.query_one(
            """
            SELECT COUNT(*) AS c
            FROM bookings
            WHERE train_id = ?
              AND journey_date = ?
              AND class_code = ?
              AND status = 'WAITLIST'
            """,
            (train_id, date_str, class_code.upper())
        )["c"]

        if confirmed < capacity:
            status = "AVAILABLE"
        else:
            status = "WAITLIST"

        return {
            "capacity": capacity,
            "confirmed": confirmed,
            "available": max(0, capacity - confirmed),
            "waitlisted": waitlisted,
            "status": status,
        }

    def _next_seat(self, train_id: int, date_str: str, class_code: str):
        # Find first unused coach/seat.
        coaches = self.db.query_all(
            """
            SELECT coach_code, seat_capacity
            FROM coaches
            WHERE train_id = ? AND class_code = ?
            ORDER BY id
            """,
            (train_id, class_code)
        )

        taken = {
            (row["coach_code"], row["seat_no"])
            for row in self.db.query_all(
                """
                SELECT p.coach_code, p.seat_no
                FROM passengers p
                JOIN bookings b ON b.id = p.booking_id
                WHERE b.train_id = ?
                  AND b.journey_date = ?
                  AND b.class_code = ?
                  AND b.status = 'CONFIRMED'
                  AND p.allocation_status = 'CONFIRMED'
                """,
                (train_id, date_str, class_code)
            )
        }

        for coach in coaches:
            for seat_no in range(1, coach["seat_capacity"] + 1):
                if (coach["coach_code"], seat_no) not in taken:
                    return coach["coach_code"], seat_no

        return None, None

    def coach_chart(
        self, train_id: int, date_str: str, class_code: str
    ):
        rows = self.db.query_all(
            """
            SELECT p.coach_code, p.seat_no, p.name, b.pnr
            FROM passengers p
            JOIN bookings b ON b.id = p.booking_id
            WHERE b.train_id = ?
              AND b.journey_date = ?
              AND b.class_code = ?
              AND b.status = 'CONFIRMED'
              AND p.allocation_status = 'CONFIRMED'
            ORDER BY p.coach_code, p.seat_no
            """,
            (train_id, date_str, class_code.upper())
        )
        return rows

    #  Booking  #

    def book_ticket(
        self,
        train_no: str,
        journey_date: str,
        source_code: str,
        destination_code: str,
        class_code: str,
        passengers: list[Passenger]
    ) -> str:
        if not passengers:
            raise ValueError("At least one passenger is required.")

        if not parse_date(journey_date):
            raise ValueError("Journey date must be YYYY-MM-DD.")

        today = datetime.now().date()
        journey = parse_date(journey_date).date()
        if journey < today:
            raise ValueError("Journey date cannot be in the past.")

        train_id = self._train_id(train_no)
        class_code = class_code.upper()

        search = self.search_trains(
            source_code, destination_code, journey_date
        )
        valid_train = any(x.train_id == train_id for x in search)
        if not valid_train:
            raise ValueError("Train does not operate on this route.")

        if class_code not in self.CLASS_INFO:
            raise ValueError("Invalid class.")

        # Limit booking size for the simulation.
        if len(passengers) > 6:
            raise ValueError("Maximum 6 passengers per booking.")

        fare_total = self.calculate_fare(
            train_id,
            source_code,
            destination_code,
            class_code,
            len(passengers)
        )

        inv = self.inventory_status(train_id, journey_date, class_code)

        if inv["available"] >= len(passengers):
            booking_status = "CONFIRMED"
        else:
            booking_status = "WAITLIST"

        # Make PNR collision extremely unlikely.
        for _ in range(20):
            pnr = generate_pnr()
            if not self.db.query_one(
                "SELECT 1 FROM bookings WHERE pnr = ?", (pnr,)
            ):
                break
        else:
            raise RuntimeError("Unable to generate unique PNR.")

        source_id = self._station_id(source_code)
        dest_id = self._station_id(destination_code)

        cur = self.db.execute(
            """
            INSERT INTO bookings
            (pnr, train_id, journey_date, source_station_id,
             destination_station_id, class_code, status, total_fare, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pnr,
                train_id,
                journey_date,
                source_id,
                dest_id,
                class_code,
                booking_status,
                fare_total,
                now_str(),
            )
        )
        booking_id = cur.lastrowid

        if booking_status == "CONFIRMED":
            for index, passenger in enumerate(passengers, 1):
                coach, seat = self._next_seat(
                    train_id, journey_date, class_code
                )
                if not coach:
                    # Safety fallback: should not happen because capacity was checked.
                    raise RuntimeError("Seat allocation failed.")

                passenger_fare = round(fare_total / len(passengers), 2)
                self.db.execute(
                    """
                    INSERT INTO passengers
                    (booking_id, passenger_no, name, age, gender,
                     berth_preference, allocation_status, coach_code,
                     seat_no, fare)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        booking_id,
                        index,
                        passenger.name,
                        passenger.age,
                        passenger.gender,
                        passenger.berth_preference,
                        "CONFIRMED",
                        coach,
                        seat,
                        passenger_fare,
                    )
                )
        else:
            for index, passenger in enumerate(passengers, 1):
                self.db.execute(
                    """
                    INSERT INTO passengers
                    (booking_id, passenger_no, name, age, gender,
                     berth_preference, allocation_status, coach_code,
                     seat_no, fare)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        booking_id,
                        index,
                        passenger.name,
                        passenger.age,
                        passenger.gender,
                        passenger.berth_preference,
                        "WAITLIST",
                        None,
                        None,
                        round(fare_total / len(passengers), 2),
                    )
                )

            next_pos = self.db.query_one(
                """
                SELECT COALESCE(MAX(position), 0) + 1 AS pos
                FROM waitlist
                WHERE journey_date IS NULL
                """,
            )
            # The query above intentionally ignores booking date; actual position
            # is recalculated below per train/date/class.
            pos_row = self.db.query_one(
                """
                SELECT COALESCE(MAX(w.position), 0) + 1 AS pos
                FROM waitlist w
                JOIN bookings b ON b.id = w.booking_id
                WHERE b.train_id = ?
                  AND b.journey_date = ?
                  AND b.class_code = ?
                  AND b.status = 'WAITLIST'
                """,
                (train_id, journey_date, class_code)
            )

            self.db.execute(
                "INSERT INTO waitlist(booking_id, position, created_at) VALUES (?, ?, ?)",
                (booking_id, pos_row["pos"], now_str())
            )

        return pnr

    def get_booking(self, pnr: str):
        row = self.db.query_one(
            """
            SELECT
                b.*,
                t.train_no,
                t.name AS train_name,
                s1.code AS source_code,
                s1.name AS source_name,
                s2.code AS destination_code,
                s2.name AS destination_name
            FROM bookings b
            JOIN trains t ON t.id = b.train_id
            JOIN stations s1 ON s1.id = b.source_station_id
            JOIN stations s2 ON s2.id = b.destination_station_id
            WHERE b.pnr = ?
            """,
            (pnr.upper().strip(),)
        )
        if not row:
            return None
        passengers = self.db.query_all(
            """
            SELECT *
            FROM passengers
            WHERE booking_id = ?
            ORDER BY passenger_no
            """,
            (row["id"],)
        )
        waitlist = self.db.query_one(
            "SELECT position FROM waitlist WHERE booking_id = ?",
            (row["id"],)
        )
        return row, passengers, waitlist

    def print_ticket(self, pnr: str):
        result = self.get_booking(pnr)
        if not result:
            print("PNR not found.")
            return

        booking, passengers, wait = result

        print("\n" + "=" * 76)
        print("                 RAILWAY TICKET SIMULATION")
        print("=" * 76)
        print(f"PNR              : {booking['pnr']}")
        print(f"Train            : {booking['train_no']} - {booking['train_name']}")
        print(f"Journey Date     : {booking['journey_date']}")
        print(
            f"Route            : {booking['source_code']} ({booking['source_name']})"
            f" -> {booking['destination_code']} ({booking['destination_name']})"
        )
        print(f"Class            : {booking['class_code']} - {self.CLASS_INFO[booking['class_code']]['name']}")
        print(f"Booking Status   : {booking['status']}")
        print(f"Total Fare       : {money(booking['total_fare'])}")
        print(f"Booked At        : {booking['created_at']}")
        print("-" * 76)

        for p in passengers:
            allocation = p["allocation_status"]
            if allocation == "CONFIRMED":
                seat = f"{p['coach_code']}-{p['seat_no']}"
            else:
                seat = "WL"
            print(
                f"{p['passenger_no']:>2}. {p['name']:<22} "
                f"Age {p['age']:<3} {p['gender']:<6} "
                f"{seat:<8} {allocation}"
            )

        if wait:
            print(f"\nWaitlist Position : {wait['position']}")

        print("=" * 76 + "\n")
