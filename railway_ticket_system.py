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

