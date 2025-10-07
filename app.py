import streamlit as st
from supabase_client import supabase
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
from datetime import datetime

# ----------------------------
# Page Configuration
# ----------------------------
st.set_page_config(page_title="Campus Shuttle Tracker", layout="wide")
st.title("🚌 Campus Shuttle Tracker")

# ----------------------------
# Sidebar Navigation
# ----------------------------
menu = st.sidebar.radio(
    "Navigation",
    ["Home", "Bus Summary", "Book Seat", "Intent to Travel", "Admin Login", "Admin Dashboard"]
)

# ----------------------------
# HOME PAGE
# ----------------------------
if menu == "Home":
    st.header("Welcome to the Campus Shuttle Tracker 🚍")
    st.markdown("""
    This system helps you track campus shuttle routes, check seat availability,
    record your intent to travel, and allow admins to manage buses in real time.
    """)

# ----------------------------
# BUS SUMMARY
# ----------------------------
elif menu == "Bus Summary":
    st.header("🚌 Live Bus Summary")

    buses = supabase.table("buses").select("*").execute().data or []
    seats = supabase.table("seats").select("*").execute().data or []
    routes = supabase.table("routes").select("*").execute().data or []
    intents = supabase.table("intent_to_travel").select("*").execute().data or []

    if not buses:
        st.warning("No buses found.")
    else:
        seat_map = {s["bus_id"]: int(s.get("available_seats", 0)) for s in seats}
        route_map = defaultdict(list)

        # Prepare routes
        for r in routes:
            bus_id = r.get("bus_id")
            if bus_id:
                stop_time = r.get("stop_time")
                try:
                    parsed_time = datetime.strptime(stop_time, "%H:%M:%S").time()
                except:
                    try:
                        parsed_time = datetime.strptime(stop_time, "%H:%M").time()
                    except:
                        parsed_time = stop_time
                route_map[bus_id].append((parsed_time, r.get("stop_name", "")))

        for bid in route_map:
            route_map[bid].sort(key=lambda x: x[0])

        # Count intents
        intent_count = defaultdict(int)
        for i in intents:
            if i.get("bus_id"):
                intent_count[i["bus_id"]] += 1

        # Two columns for layout
        cols = st.columns(2)
        for i, bus in enumerate(buses):
            bus_id = bus["bus_id"]
            available = seat_map.get(bus_id, 0)
            total = int(bus.get("total_seats", 0))
            percent = int((available / total) * 100) if total else 0
            route_str = " → ".join(s[1] for s in route_map.get(bus_id, [])) or "No route info"
            intents_num = intent_count.get(bus_id, 0)

            # Progress color
            if available == total:
                color = "green"
            elif total and available / total < 0.3:
                color = "red"
            else:
                color = "orange"

            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"### 🚐 {bus['bus_number']}")
                    st.write(f"**Route:** {route_str}")
                    st.write(f"**Available Seats:** {available} / {total}")
                    st.write(f"**Intent Count:** {intents_num}")
                    st.progress(percent / 100)
                    st.markdown(
                        f"<p style='color:{color}; font-weight:bold;'>Occupancy: {100 - percent}% full</p>",
                        unsafe_allow_html=True
                    )

# ----------------------------
# BOOK SEAT
# ----------------------------
elif menu == "Book Seat":
    st.header("🎟️ Book a Seat")

    buses = supabase.table("buses").select("*").execute().data
    if not buses:
        st.warning("No buses available.")
    else:
        selected_bus = st.selectbox("Select Bus", [b["bus_number"] for b in buses])
        user_name = st.text_input("Enter your name")

        if st.button("Book Seat"):
            bus = next(b for b in buses if b["bus_number"] == selected_bus)
            seat_info = supabase.table("seats").select("*").eq("bus_id", bus["bus_id"]).execute().data

            if not seat_info or seat_info[0]["available_seats"] <= 0:
                st.error("No seats available for this bus!")
            else:
                supabase.table("occupancy").insert({
                    "bus_id": bus["bus_id"],
                    "user_name": user_name
                }).execute()

                supabase.table("seats").update({
                    "available_seats": seat_info[0]["available_seats"] - 1
                }).eq("bus_id", bus["bus_id"]).execute()

                st.success(f"Booking confirmed for {user_name} on bus {selected_bus}!")

# ----------------------------
# INTENT TO TRAVEL
# ----------------------------
elif menu == "Intent to Travel":
    st.header("🧭 Intent to Travel")

    buses = supabase.table("buses").select("*").execute().data
    if not buses:
        st.warning("No buses found.")
    else:
        student_id = st.text_input("Enter your Student ID")
        selected_bus = st.selectbox("Select Bus", [b["bus_number"] for b in buses])

        if st.button("Submit Intent"):
            bus = next(b for b in buses if b["bus_number"] == selected_bus)
            supabase.table("intent_to_travel").insert({
                "student_id": student_id,
                "bus_id": bus["bus_id"],
                "seat_reserved": False
            }).execute()
            st.success("Your travel intent has been recorded!")

# ----------------------------
# ADMIN LOGIN
# ----------------------------
# ----------------------------
# ADMIN LOGIN
# ----------------------------
elif menu == "Admin Login":
    st.header("🔐 Admin Login")

    if "admin" not in st.session_state:
        st.session_state.admin = None

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Hardcoded check
        if username == "admin" and password == "admin@123":
            st.session_state.admin = username
            st.success("Login successful! Open the Admin Dashboard from sidebar.")
        else:
            st.error("Invalid username or password.")


# ----------------------------
# ADMIN DASHBOARD
# ----------------------------
elif menu == "Admin Dashboard":
    if "admin" not in st.session_state or not st.session_state.admin:
        st.warning("You must log in first (see Admin Login section).")
    else:
        st.header(f"🧑‍💼 Admin Dashboard — {st.session_state.admin}")

        buses = supabase.table("buses").select("*").execute().data or []
        seats = supabase.table("seats").select("*").execute().data or []
        intents = supabase.table("intent_to_travel").select("*").execute().data or []

        if not buses:
            st.warning("No buses found.")
        else:
            import pandas as pd
            data = []
            for b in buses:
                seat_info = next((s for s in seats if s["bus_id"] == b["bus_id"]), None)
                intent_count = sum(1 for i in intents if i["bus_id"] == b["bus_id"])
                data.append({
                    "Bus Number": b["bus_number"],
                    "Total Seats": b["total_seats"],
                    "Available Seats": seat_info["available_seats"] if seat_info else b["total_seats"],
                    "Intent Count": intent_count
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

            st.divider()
            st.subheader("✏️ Edit Bus Info")
            selected_bus = st.selectbox("Select Bus to Edit", [b["bus_number"] for b in buses])
            bus = next(b for b in buses if b["bus_number"] == selected_bus)

            new_bus_number = st.text_input("Bus Number", bus["bus_number"])
            new_total_seats = st.number_input("Total Seats", value=bus["total_seats"])
            seat_info = next((s for s in seats if s["bus_id"] == bus["bus_id"]), None)
            new_available_seats = st.number_input("Available Seats", value=seat_info["available_seats"] if seat_info else 0)

            if st.button("Update Bus"):
                supabase.table("buses").update({
                    "bus_number": new_bus_number,
                    "total_seats": new_total_seats
                }).eq("bus_id", bus["bus_id"]).execute()

                supabase.table("seats").update({
                    "available_seats": new_available_seats
                }).eq("bus_id", bus["bus_id"]).execute()

                st.success("Bus details updated successfully!")
