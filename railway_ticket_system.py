#!/usr/bin/env python3
"""
Railway Ticket Simulation System
--------------------------------
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

# ----------------------------- Utilities ----------------------------- #

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


# ----------------------------- Data classes ----------------------------- #

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
