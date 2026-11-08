"""Mock flight and hotel tools with fixed, repeatable results.

The same inputs always give the same options, prices and confirmation codes,
so a test can check that a change of plans really changed the search.
Searches wait FLIGHT_SEARCH_SECONDS / HOTEL_SEARCH_SECONDS, like a real fare
search; set them to 0 to just click around.

Bookings live in memory in the server process. book_flight and book_hotel
charge money, so the agents pause for a human's approval before running them
(see agents.py). Cancelling is free and runs without approval.

One trip holds at most one flight and one hotel. A trip is the agent's thread,
which stays the same across updates. Booking again on the same trip replaces
the old booking and cancels it in the same step. This is enforced here, not in
the prompt: in testing, a model told "cancel first, then rebook" sometimes
rebooked without cancelling, leaving the traveler with two flights.
"""

import asyncio
import hashlib
import os
from datetime import date

from langchain_core.tools import tool
from langgraph.config import get_config

BOOKINGS: dict[str, dict] = {}  # confirmation code -> booking
ACTIVE: dict[tuple[str, str], str] = {}  # (trip thread, "flight" | "hotel") -> confirmation code


def _trip() -> str:
    return str(get_config()["configurable"]["thread_id"])


def _replace(kind: str, code: str, booking: dict) -> str:
    """Record a booking as the trip's active one; cancel and describe the one it replaces."""
    old = ACTIVE.get((_trip(), kind))
    BOOKINGS[code] = {**booking, "type": kind}
    ACTIVE[(_trip(), kind)] = code
    if old and old != code and BOOKINGS.pop(old, None):
        return f" Replaced and CANCELLED the previous {kind} booking {old}."
    return ""


def _num(*parts: str, mod: int) -> int:
    """A stable number from the inputs, so results repeat exactly."""
    return int(hashlib.sha256("|".join(parts).lower().encode()).hexdigest(), 16) % mod


def _check_dates(start: str, end: str) -> str | None:
    try:
        if date.fromisoformat(end) <= date.fromisoformat(start):
            return "ERROR: the end date must be after the start date."
    except ValueError:
        return "ERROR: dates must be YYYY-MM-DD."
    return None


@tool
async def search_flights(origin: str, destination: str, depart_date: str, return_date: str) -> str:
    """Search round-trip economy flights.

    Args:
        origin: Departure city, e.g. "San Francisco".
        destination: Arrival city, e.g. "Seattle".
        depart_date: Outbound date, YYYY-MM-DD.
        return_date: Return date, YYYY-MM-DD.
    """
    if error := _check_dates(depart_date, return_date):
        return error
    # Fakes a slow real API so you can change the trip mid-search.
    # Remove it in real code; the actual API call is the slow part.
    await asyncio.sleep(float(os.getenv("FLIGHT_SEARCH_SECONDS", 30)))
    lines = [f"Round trip {origin} -> {destination}, out {depart_date}, back {return_date}:"]
    for i, airline in enumerate(["Pacific Air", "Bluebird", "Northstar"], start=1):
        price = 180 + _num(origin, destination, depart_date, return_date, airline, mod=320)
        stops = "nonstop" if i != 3 else "1 stop"
        option = f"FL{_num(origin, destination, depart_date, return_date, airline, mod=9000) + 1000}"
        lines.append(f"- option_id={option} | {airline} | {stops} | ${price}")
    return "\n".join(lines)


@tool
def book_flight(option_id: str, origin: str, destination: str, depart_date: str, return_date: str, price_usd: int) -> str:
    """Book a flight option from search_flights. Charges the traveler, so a human must approve.

    If this trip already has a flight, the new booking replaces it and the old one is cancelled.

    Args:
        option_id: The option_id from search_flights.
        origin: Departure city.
        destination: Arrival city.
        depart_date: Outbound date, YYYY-MM-DD.
        return_date: Return date, YYYY-MM-DD.
        price_usd: The option's price in dollars.
    """
    code = f"FLT-{_num(option_id, depart_date, return_date, mod=900000) + 100000}"
    replaced = _replace("flight", code, {
        "option_id": option_id, "origin": origin, "destination": destination,
        "depart_date": depart_date, "return_date": return_date, "price_usd": price_usd,
    })
    return f"BOOKED flight {code}: {origin} -> {destination}, {depart_date} to {return_date}, ${price_usd}.{replaced}"


@tool
def cancel_flight(confirmation: str) -> str:
    """Cancel the trip's flight booking without rebooking, e.g. the traveler drops the flight.

    Args:
        confirmation: The FLT-... confirmation code from book_flight.
    """
    booking = BOOKINGS.pop(confirmation, None)
    if booking is None or booking["type"] != "flight":
        return f"ERROR: no flight booking {confirmation}."
    ACTIVE.pop((_trip(), "flight"), None)
    return f"CANCELLED flight {confirmation} ({booking['origin']} -> {booking['destination']}, {booking['depart_date']})"


@tool
async def search_hotels(city: str, check_in: str, check_out: str) -> str:
    """Search hotels in a city for the given nights.

    Args:
        city: City to stay in, e.g. "Seattle".
        check_in: Check-in date, YYYY-MM-DD.
        check_out: Check-out date, YYYY-MM-DD.
    """
    if error := _check_dates(check_in, check_out):
        return error
    # Fakes a slow real API so you can change the trip mid-search.
    # Remove it in real code; the actual API call is the slow part.
    await asyncio.sleep(float(os.getenv("HOTEL_SEARCH_SECONDS", 20)))
    nights = (date.fromisoformat(check_out) - date.fromisoformat(check_in)).days
    lines = [f"Hotels in {city}, {check_in} to {check_out} ({nights} nights):"]
    for name in ["Harbor Inn", "Grand Central Hotel", "Parkside Suites"]:
        rate = 120 + _num(city, check_in, name, mod=180)
        option = f"HT{_num(city, check_in, check_out, name, mod=9000) + 1000}"
        lines.append(f"- option_id={option} | {name} | ${rate}/night | total ${rate * nights}")
    return "\n".join(lines)


@tool
def book_hotel(option_id: str, hotel_name: str, city: str, check_in: str, check_out: str, total_usd: int) -> str:
    """Book a hotel option from search_hotels. Charges the traveler, so a human must approve.

    If this trip already has a hotel, the new booking replaces it and the old one is cancelled.

    Args:
        option_id: The option_id from search_hotels.
        hotel_name: The hotel's name.
        city: City of the hotel.
        check_in: Check-in date, YYYY-MM-DD.
        check_out: Check-out date, YYYY-MM-DD.
        total_usd: Total price for the stay in dollars.
    """
    code = f"HTL-{_num(option_id, check_in, check_out, mod=900000) + 100000}"
    replaced = _replace("hotel", code, {
        "option_id": option_id, "hotel_name": hotel_name, "city": city,
        "check_in": check_in, "check_out": check_out, "total_usd": total_usd,
    })
    return f"BOOKED hotel {code}: {hotel_name}, {city}, {check_in} to {check_out}, ${total_usd}.{replaced}"


@tool
def cancel_hotel(confirmation: str) -> str:
    """Cancel the trip's hotel booking without rebooking, e.g. the traveler drops the hotel.

    Args:
        confirmation: The HTL-... confirmation code from book_hotel.
    """
    booking = BOOKINGS.pop(confirmation, None)
    if booking is None or booking["type"] != "hotel":
        return f"ERROR: no hotel booking {confirmation}."
    ACTIVE.pop((_trip(), "hotel"), None)
    return f"CANCELLED hotel {confirmation} ({booking['hotel_name']}, {booking['city']}, {booking['check_in']})"
