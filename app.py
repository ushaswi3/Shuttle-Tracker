import streamlit as st
from supabase_client import supabase
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
from datetime import datetime

# ----------------------------
# Streamlit Page Config
# ----------------------------
st.set_page_config(page_title="Campus Shuttle Tracker", layout="wide")
st.title("🚌 Campus Shuttle Tracker")

# ----------------------------
# Sidebar Navigation
# ----------------------------
menu = st.sidebar.radio(
    "Navigation",
    [
        "Home",
        "Bus Summary",
        "View Schedule",  
        "Book Seat",
        "Intent to Travel",
        "Admin Register",
        "Admin Login",
        "Admin Dashboard"
    ]
)

# ----------------------------
# Session State
# ----------------------------
if "admin" not in st.session_state:
    st.session_state.admin = None


# ----------------------------
# Helper Functions
# ----------------------------
def get_data():
    buses = supabase.table("buses").select("*").execute().data or []
    seats = supabase.table("seats").select("*").execute().data or []
    routes = supabase.table("routes").select("*").execute().data or []
    intents = supabase.table("intent_to_travel").select("*").execute().data or []
    return buses, seats, routes, intents


# ----------------------------
# Home
# ----------------------------
if menu == "Home":
    st.markdown("""
        <style>
        @keyframes float {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-8px); }
            100% { transform: translateY(0px); }
        }

        .home-card {
            background-color: #f5f5f5;  /* light grey */
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2); /* floating effect */
            font-family: 'Segoe UI', sans-serif;
            line-height: 1.6;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            animation: float 3s ease-in-out infinite; /* subtle floating animation */
        }

        .home-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 12px 25px rgba(0, 0, 0, 0.25);
        }

        .home-card h3 {
            color: #007BFF; /* matching blue */
            margin-bottom: 15px;
        }

        .home-card ul {
            margin-top: 10px;
        }
        </style>

        <div class="home-card">
            <h3>🚍 Welcome to the Campus Shuttle Tracker!</h3>
            <h5>Track campus shuttles in real-time, see schedules, check seat availability, and submit your travel intentions—all from one convenient location.</h5>
            <p>Manage your campus shuttle system efficiently:</p>
            <ul>
                <li>View real-time bus summaries and schedules</li>
                <li>Book seats easily</li>
                <li>Record your intent to travel</li>
                <li>Admins can register, log in, and manage buses</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)


# ----------------------------
# BUS SUMMARY
# ----------------------------
elif menu == "Bus Summary":
    st.header("🚌 Bus Summary")

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

        # Add CSS for floating animation
        st.markdown("""
            <style>
            .floating-card {
                background-color: #ffffff;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                animation: float 3s ease-in-out infinite;
            }

            .floating-card:hover {
                transform: scale(1.03);
                box-shadow: 0 20px 40px rgba(0,0,0,0.25);
            }

            @keyframes float {
                0% { transform: translateY(0px); }
                50% { transform: translateY(-8px); }
                100% { transform: translateY(0px); }
            }
            </style>
        """, unsafe_allow_html=True)

        # Two-column layout for cards
        cols = st.columns(2)
        for i, bus in enumerate(buses):
            bus_id = bus["bus_id"]
            available = seat_map.get(bus_id, 0)
            total = int(bus.get("total_seats", 0))
            percent = int((available / total) * 100) if total else 0
            route_str = " → ".join(s[1] for s in route_map.get(bus_id, [])) or "No route info"
            intents_num = intent_count.get(bus_id, 0)

            # Progress color based on occupancy
            if available == total:
                color = "#28a745"  # green
            elif total and available / total < 0.3:
                color = "#dc3545"  # red
            else:
                color = "#ffc107"  # orange

            with cols[i % 2]:
                st.markdown(
                    f"""
                    <div class="floating-card">
                        <h4>🚐 {bus['bus_number']}</h4>
                        <p><b>Route:</b> {route_str}</p>
                        <p><b>Available Seats:</b> {available} / {total}</p>
                        <p><b>Intent Count:</b> {intents_num}</p>
                        <div style='background-color:#e9ecef; border-radius:10px; height:20px; width:100%; margin-top:10px;'>
                            <div style='background-color:{color}; width:{percent}%; height:100%; border-radius:10px;'></div>
                        </div>
                        <p style='color:{color}; font-weight:bold; margin-top:5px;'>Occupancy: {100 - percent}% full</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


# ----------------------------
# View Schedule
# ----------------------------
elif menu == "View Schedule":
    st.header("📅 Full Bus Schedule")

    buses, _, routes, _ = get_data()

    if not buses or not routes:
        st.warning("No buses or schedules found.")
    else:
        import pandas as pd
        from collections import defaultdict

        # Group routes by bus_id
        route_map = defaultdict(list)
        for r in routes:
            bus_id = r.get("bus_id")
            stop_time = r.get("stop_time")
            stop_name = r.get("stop_name", "")
            route_map[bus_id].append((stop_time, stop_name))

        # Sort stops by time
        for bus_id in route_map:
            route_map[bus_id].sort(key=lambda x: x[0])

        # Sort buses by bus_id to preserve order
        buses_sorted = sorted(buses, key=lambda x: x["bus_id"])

        # Prepare dataframe for display
        table_data = []
        for bus in buses:
            bus_id = bus["bus_id"]
            stops = route_map.get(bus_id, [])
            if stops:
                route_str = " → ".join([f"{stop_time} ({stop_name})" for stop_time, stop_name in stops])
            else:
                route_str = "No schedule available"
            table_data.append({
                "Bus Number": bus["bus_number"],
                "Total Seats": bus["total_seats"],
                "Route Schedule": route_str
            })

        df = pd.DataFrame(table_data)

        # Custom styled table
        st.markdown("""
            <style>
            .styled-table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 16px;
                font-family: 'Segoe UI';
                border-radius: 10px 10px 0 0;
                overflow: hidden;
                box-shadow: 0 0 10px rgba(0,0,0,0.15);
            }
            .styled-table thead tr {
                background-color: #17A2B8;
                color: #ffffff;
                text-align: left;
                font-weight: bold;
            }
            .styled-table th, .styled-table td {
                padding: 12px 15px;
            }
            .styled-table tbody tr {
                border-bottom: 1px solid #dddddd;
            }
            .styled-table tbody tr:hover {
                background-color: #f1f1f1;
                transform: scale(1.01);
                transition: all 0.2s ease-in-out;
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown(df.to_html(index=False, classes="styled-table"), unsafe_allow_html=True)

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
# Intent to Travel
# ----------------------------
elif menu == "Intent to Travel":
    st.subheader("🧳 Submit Intent to Travel")

    buses = supabase.table("buses").select("*").execute().data
    bus_list = {b["bus_number"]: b["bus_id"] for b in buses}

    student_id = st.text_input("Enter Your Student ID")
    selected_bus = st.selectbox("Select a Bus", list(bus_list.keys()))

    if st.button("Submit Intent"):
        bus_id = bus_list[selected_bus]
        supabase.table("intent_to_travel").insert({
            "student_id": student_id,
            "bus_id": bus_id,
            "seat_reserved": False
        }).execute()
        st.success("✅ Your intent to travel has been recorded!")


# ----------------------------
# Admin Registration
# ----------------------------
elif menu == "Admin Register":
    st.subheader("📝 Admin Registration")

    username = st.text_input("Choose a Username")
    password = st.text_input("Create a Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if password != confirm_password:
            st.error("Passwords do not match!")
        else:
            existing = supabase.table("admins").select("*").eq("username", username).execute().data
            if existing:
                st.error("Username already taken!")
            else:
                hashed_pw = generate_password_hash(password)
                supabase.table("admins").insert({"username": username, "password": hashed_pw}).execute()
                st.success("✅ Registration successful! You can now log in.")


# ----------------------------
# Admin Login
# ----------------------------
elif menu == "Admin Login":
    st.subheader("🔐 Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        result = supabase.table("admins").select("*").eq("username", username).execute()
        admin = result.data[0] if result.data else None

        if admin and check_password_hash(admin["password"], password):
            st.session_state.admin = admin["username"]
            st.success(f"✅ Welcome, {admin['username']}!")
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

        # Fetch all data
        buses = supabase.table("buses").select("*").execute().data or []
        seats = supabase.table("seats").select("*").execute().data or []
        intents = supabase.table("intent_to_travel").select("*").execute().data or []
        routes = supabase.table("routes").select("*").execute().data or []

        if not buses:
            st.warning("No buses found.")
        else:
            import pandas as pd
            from collections import defaultdict

            route_map = defaultdict(list)
            for r in routes:
                bus_id = r.get("bus_id")
                if bus_id:
                    stop_time = r.get("stop_time", "")
                    stop_name = r.get("stop_name", "")
                    route_map[bus_id].append(f"{stop_name} ({stop_time})")

            # Sort routes by time order
            for bid in route_map:
                route_map[bid].sort()

            # Sort buses by bus_id to preserve order
            buses_sorted = sorted(buses, key=lambda x: x["bus_id"])

            data = []
            for b in buses:
                seat_info = next((s for s in seats if s["bus_id"] == b["bus_id"]), None)
                intent_count = sum(1 for i in intents if i["bus_id"] == b["bus_id"])
                route_display = " → ".join(route_map.get(b["bus_id"], ["No route"]))
                data.append({
                    "Bus Number": b["bus_number"],
                    "Total Seats": b["total_seats"],
                    "Available Seats": seat_info["available_seats"] if seat_info else b["total_seats"],
                    "Intent Count": intent_count,
                    "Route": route_display
                })

            df = pd.DataFrame(data)

            # Custom styled HTML table
            st.markdown("""
                <style>
                .styled-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                    font-size: 16px;
                    font-family: 'Segoe UI';
                    border-radius: 10px 10px 0 0;
                    overflow: hidden;
                    box-shadow: 0 0 10px rgba(0,0,0,0.15);
                }
                .styled-table thead tr {
                    background-color: #007BFF;
                    color: #ffffff;
                    text-align: left;
                    font-weight: bold;
                }
                .styled-table th, .styled-table td {
                    padding: 12px 15px;
                }
                .styled-table tbody tr {
                    border-bottom: 1px solid #dddddd;
                }
                .styled-table tbody tr:hover {
                    background-color: #f1f1f1;
                    transform: scale(1.01);
                    transition: all 0.2s ease-in-out;
                }
                </style>
            """, unsafe_allow_html=True)

            st.markdown(df.to_html(index=False, classes="styled-table"), unsafe_allow_html=True)

            st.divider()
            st.subheader("✏️ Edit Bus Info")

            selected_bus_number = st.selectbox("Select Bus to Edit", [b["bus_number"] for b in buses])
            bus = next(b for b in buses if b["bus_number"] == selected_bus_number)

            # Fetch seat info and routes
            seat_info = next((s for s in seats if s["bus_id"] == bus["bus_id"]), None)
            bus_routes = [r for r in routes if r["bus_id"] == bus["bus_id"]]

            # Bus info inputs
            new_bus_number = st.text_input("Bus Number", bus["bus_number"], key=f"bus_num_{bus['bus_id']}")
            new_total_seats = st.number_input("Total Seats", value=bus["total_seats"], key=f"total_seats_{bus['bus_id']}")
            new_available_seats = st.number_input(
                "Available Seats",
                value=seat_info["available_seats"] if seat_info else 0,
                key=f"avail_seats_{bus['bus_id']}"
            )

            # Current routes
            st.write("### 🛣 Current Routes")
            for i, r in enumerate(bus_routes):
                col1, col2 = st.columns([2, 1])
                key_name = f"{bus['bus_id']}_stop_name_{i}"
                key_time = f"{bus['bus_id']}_stop_time_{i}"
                with col1:
                    stop_name = st.text_input(f"Stop Name {i+1}", r["stop_name"], key=key_name)
                with col2:
                    stop_time = st.text_input(f"Time {i+1}", r["stop_time"], key=key_time)

            # Add new route
            st.write("### ➕ Add New Route")
            new_stop_name = st.text_input("New Stop Name", key=f"new_stop_name_{bus['bus_id']}")
            new_stop_time = st.text_input("New Stop Time (HH:MM)", key=f"new_stop_time_{bus['bus_id']}")

            if st.button("Add Route", key=f"add_route_btn_{bus['bus_id']}"):
                if new_stop_name and new_stop_time:
                    supabase.table("routes").insert({
                        "bus_id": bus["bus_id"],
                        "stop_name": new_stop_name,
                        "stop_time": new_stop_time
                    }).execute()
                    st.success("✅ New route added successfully!")
                    st.experimental_rerun()
                else:
                    st.warning("Please fill both stop name and time.")

            if st.button("Update Bus", key=f"update_bus_btn_{bus['bus_id']}"):
                # Update bus info
                supabase.table("buses").update({
                    "bus_number": new_bus_number,
                    "total_seats": new_total_seats
                }).eq("bus_id", bus["bus_id"]).execute()

                # Update seats
                supabase.table("seats").update({
                    "available_seats": new_available_seats
                }).eq("bus_id", bus["bus_id"]).execute()

                # Update routes
                for i, r in enumerate(bus_routes):
                    key_name = f"{bus['bus_id']}_stop_name_{i}"
                    key_time = f"{bus['bus_id']}_stop_time_{i}"
                    stop_name = st.session_state.get(key_name)
                    stop_time = st.session_state.get(key_time)
                    supabase.table("routes").update({
                        "stop_name": stop_name,
                        "stop_time": stop_time
                    }).eq("route_id", r["route_id"]).execute()

                st.success("✅ Bus details updated successfully!")
        
    if st.button("Logout"):
        st.session_state.admin = None
        st.info("Logged out successfully.")
