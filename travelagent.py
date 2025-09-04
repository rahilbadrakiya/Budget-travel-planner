import streamlit as st
import json
import os
import time
from serpapi import GoogleSearch 
from agno.agent import Agent
from agno.tools.serpapi import SerpApiTools
from agno.models.google import Gemini
from datetime import datetime, date
from urllib.parse import urlencode
import requests # You will need to install the requests library: pip install requests
from bs4 import BeautifulSoup # You will need to install the BeautifulSoup library: pip install beautifulsoup4
import re

# --- USER AUTHENTICATION & PAGE MANAGEMENT ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'page' not in st.session_state:
    st.session_state['page'] = "login"

USER_FILE = "users.json"

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r") as f:
        # Check if the file is empty before trying to load JSON
        if os.path.getsize(USER_FILE) == 0:
            return {}
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

def check_password(username, password):
    users = load_users()
    return username in users and users[username] == password

def register_user(username, password):
    users = load_users()
    if username in users:
        return False
    users[username] = password
    save_users(users)
    return True

# --- MAIN PAGE RENDERING LOGIC ---
st.set_page_config(page_title="ORBIS PLANNERS", layout="wide")

if st.session_state.page == "register":
    st.title("Register New Account")
    with st.form("register_form"):
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        register_button = st.form_submit_button("Register")
    
    if register_button:
        if new_password != confirm_password:
            st.error("Passwords do not match!")
        elif len(new_username) < 3 or len(new_password) < 6:
            st.error("Username must be at least 3 characters and password at least 6 characters.")
        else:
            if register_user(new_username, new_password):
                st.success("Account created successfully! Please log in.")
                st.session_state.page = "login"
                st.rerun()
            else:
                st.error("Username already exists.")

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

elif st.session_state.page == "login":
    st.markdown('<h1 class="title">ORBIS PLANNERS</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Plan your dream trip with AI!</p>', unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if check_password(username, password):
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.session_state['page'] = "app"
            st.success("Logged in successfully! 🚀")
            st.rerun()
        else:
            st.error("Invalid username or password.")
            
    if st.button("Register New Account"):
        st.session_state.page = "register"
        st.rerun()

elif st.session_state.page == "app":
    st.markdown('<h1 class="title">ORBIS PLANNERS</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Plan your dream trip with AI! Get personalized recommendations for flights, hotels, and activities.</p>', unsafe_allow_html=True)
    
    st.sidebar.title("🌎 Travel Assistant")
    st.sidebar.text(f"Welcome, {st.session_state.username}!")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.session_state['page'] = "login"
        st.rerun()

    st.markdown("---")
    
    # --- City to IATA Mapping ---
    CITY_TO_IATA = {
        "mumbai": "BOM",
        "new delhi": "DEL",
        "delhi": "DEL",
        "bangalore": "BLR",
        "chennai": "MAA",
        "kolkata": "CCU",
        "hyderabad": "HYD",
        "goa": "GOI",
        "pune": "PNQ",
        "ahmedabad": "AMD",
        "jaipur": "JAI",
        "kochi": "COK",
        "cochin": "COK",
        "lucknow": "LKO",
        "patna": "PAT",
        "rajkot": "RAJ",
        # Add more cities as needed
    }

    # Helper function to get IATA code from city name, or return the code if it's already one
    def get_iata_code(city_or_code):
        city = city_or_code.strip().lower()
        if len(city) == 3 and city.isalpha():
            return city.upper()
        return CITY_TO_IATA.get(city)

    # User Inputs Section
    st.markdown("### 🌍 Where are you headed?")
    source_input = st.text_input("🛫 Departure City (Name or IATA Code):", "")
    # --- CHANGE: Destination input is now just a city name ---
    destination_input = st.text_input("🛬 Destination City (Name):", "")

    st.markdown("### 📅 Plan Your Adventure")
    # New travel mode selection
    travel_mode = st.radio("Choose your mode of travel:", ("Flights", "Trains", "Both"))
    num_days = st.slider("🕒 Trip Duration (days):", 1, 14, 5)
    travel_theme = st.selectbox(
        "🎭 Select Your Travel Theme:",
        ["💑 Couple Getaway", "👨‍👩‍👧‍👦 Family Vacation", "🏔️ Adventure Trip", "🧳 Solo Exploration"]
    )

    st.markdown("---")
    
    st.markdown(
        f"""
        <div style="
            text-align: center; 
            padding: 15px; 
            background-color: #ffecd1; 
            border-radius: 10px; 
            margin-top: 20px;
        ">
            <h3>🌟 Your {travel_theme} to {destination_input} is about to begin! 🌟</h3>
            <p>Let's find the best options for your unforgettable journey.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    def format_datetime(iso_string):
        try:
            dt = datetime.strptime(iso_string, "%Y-%m-%d %H:%M")
            return dt.strftime("%b-%d, %Y | %I:%M %p")
        except:
            return "N/A"

    activity_preferences = st.text_area(
        "🌍 What activities do you enjoy? (e.g., relaxing on the beach, exploring historical sites, nightlife, adventure)",
        ""
    )
    
    today = date.today()
    departure_date = st.date_input("Departure Date", min_value=today)
    return_date = st.date_input("Return Date", min_value=departure_date)

    # Sidebar Setup
    st.sidebar.subheader("Personalize Your Trip")
    budget = st.sidebar.radio("💰 Budget Preference:", ["Economy", "Standard", "Luxury"])
    flight_class = st.sidebar.radio("✈️ Flight Class:", ["Economy", "Business", "First Class"])
    hotel_rating = st.sidebar.selectbox("🏨 Preferred Hotel Rating:", ["Any", "3⭐", "4⭐", "5⭐"])

    st.sidebar.subheader("🎒 Packing Checklist")
    packing_list = {
        "👕 Clothes": True,
        "🩴 Comfortable Footwear": True,
        "🕶️ Sunglasses & Sunscreen": False,
        "📖 Travel Guidebook": False,
        "💊 Medications & First-Aid": True
    }
    for item, checked in packing_list.items():
        st.sidebar.checkbox(item, value=checked)

    st.sidebar.subheader("🛂 Travel Essentials")
    visa_required = st.sidebar.checkbox("🛃 Check Visa Requirements")
    travel_insurance = st.sidebar.checkbox("🛡️ Get Travel Insurance")
    currency_converter = st.sidebar.checkbox("💱 Currency Exchange Rates")
    
    SERPAPI_KEY = "9fc1212d9c0c9a72ef69ee5eead07c1b732e89c4f4c0ee9941833f54faf82370"
    GOOGLE_API_KEY = "AIzaSyDiwv2ImPaGezH45WBgylFBJNx3olXiLsE"
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

    # --- NEW FUNCTION: Find the nearest airport using a search query ---
    def find_nearest_airport_iata(city_name):
        with st.spinner(f"Searching for the nearest airport to {city_name}..."):
            # This is a conceptual implementation. A real one would use a more robust
            # API call or a pre-populated database.
            search_query = f"nearest airport to {city_name} IATA code"
            params = {
                "engine": "google_search",
                "q": search_query,
                "api_key": SERPAPI_KEY
            }
            try:
                search = GoogleSearch(params)
                results = search.get_dict()
                
                # Simple logic to find an IATA code (3 capital letters)
                # This may not be perfect, but it's a good starting point
                # for a demonstration.
                if 'organic_results' in results:
                    for result in results['organic_results']:
                        match = re.search(r'\b[A-Z]{3}\b', result.get('snippet', ''))
                        if match:
                            return match.group(0)
                        match = re.search(r'\b[A-Z]{3}\b', result.get('title', ''))
                        if match:
                            return match.group(0)
                return None
            except Exception as e:
                st.error(f"Error fetching nearest airport: {e}")
                return None
                
    def fetch_flights(source_iata, destination_iata, departure_date, return_date):
        params = {
            "engine": "google_flights",
            "departure_id": source_iata,
            "arrival_id": destination_iata,
            "outbound_date": str(departure_date),
            "return_date": str(return_date),
            "currency": "INR",
            "hl": "en",
            "api_key": SERPAPI_KEY
        }
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            return results
        except Exception as e:
            st.error(f"Error fetching flight data: {e}")
            return {}

    # Placeholder function for fetching train data
    def fetch_trains(source_city, destination_city):
        st.info(f"Simulating train search for {source_city} to {destination_city}...")
        # In a real application, you would use a train API here.
        # This is a placeholder for demonstration purposes.
        return {
            "trains": [
                {
                    "name": "Superfast Express",
                    "from": source_city,
                    "to": destination_city,
                    "departure": "10:00 AM",
                    "arrival": "06:00 PM",
                    "travel_time": "8 hours",
                    "price": "₹ 1500"
                },
                {
                    "name": "Mail Express",
                    "from": source_city,
                    "to": destination_city,
                    "departure": "08:00 PM",
                    "arrival": "04:00 AM",
                    "travel_time": "8 hours",
                    "price": "₹ 1200"
                }
            ]
        }
        
    def extract_cheapest_flights(flight_data):
        best_flights = flight_data.get("best_flights", [])
        sorted_flights = sorted(best_flights, key=lambda x: x.get("price", float("inf")))[:3]
        return sorted_flights

    def create_google_flights_link(source_iata, destination_iata, departure_date, return_date):
        base_url = "https://www.google.com/travel/flights/0?"
        q_params = f"q=Flights+from+{source_iata}+to+{destination_iata}+on+{departure_date}+returning+on+{return_date}"
        return f"{base_url}{q_params}"

    researcher = Agent(
        name="Researcher",
        instructions=[
            "Identify the travel destination specified by the user.",
            "Gather detailed information on the destination, including climate, culture, and safety tips.",
            "Find popular attractions, landmarks, and must-visit places.",
            "Search for activities that match the user’s interests and travel style.",
            "Prioritize information from reliable sources and official travel guides.",
            "Provide well-structured summaries with key insights and recommendations."
        ],
        model=Gemini(id="gemini-1.5-flash-latest"),
        tools=[SerpApiTools(api_key=SERPAPI_KEY)],
        add_datetime_to_instructions=True,
    )

    planner = Agent(
        name="Planner",
        instructions=[
            "Gather details about the user's travel preferences and budget.",
            "Create a detailed itinerary with scheduled activities and estimated costs.",
            "Ensure the itinerary includes transportation options and travel time estimates.",
            "Optimize the schedule for convenience and enjoyment.",
            "Present the itinerary in a structured format.",
            "Provide a separate, estimated budget breakdown for the entire trip, including flight, accommodation, food, and activities. The budget should be based on the user's selected budget preference (Economy, Standard, or Luxury). Give a numerical estimate. Do not use the word 'Varies'. Give a numerical estimate."
        ],
        model=Gemini(id="gemini-1.5-flash-latest"),
        add_datetime_to_instructions=True,
    )

    hotel_restaurant_finder = Agent(
        name="Hotel & Restaurant Finder",
        instructions=[
            "Identify key locations in the user's travel itinerary.",
            "Search for highly rated hotels near those locations.",
            "Search for top-rated restaurants based on cuisine preferences and proximity.",
            "Prioritize results based on user preferences, ratings, and availability.",
            "Provide direct booking links or reservation options where possible."
        ],
        model=Gemini(id="gemini-1.5-flash-latest"),
        tools=[SerpApiTools(api_key=SERPAPI_KEY)],
        add_datetime_to_instructions=True,
    )

    if st.button("🚀 Generate Travel Plan"):
        source_iata = get_iata_code(source_input)
        
        # --- NEW LOGIC: Find nearest airport for the destination ---
        destination_iata = get_iata_code(destination_input)
        if not destination_iata and travel_mode in ["Flights", "Both"]:
            st.warning(f"No direct airport found for '{destination_input}'. Searching for the nearest one...")
            destination_iata = find_nearest_airport_iata(destination_input)
            if destination_iata:
                st.success(f"Found nearest airport with IATA code: {destination_iata}. All flight searches will use this airport.")
            else:
                st.error(f"Could not find a nearby airport for '{destination_input}'. Please try a different city or check for a valid IATA code.")
        
        # Check for valid inputs based on travel mode
        if not source_input or not destination_input:
            st.warning("Please enter a departure and a destination city.")
        elif travel_mode in ["Flights", "Both"] and (not source_iata or not destination_iata):
            st.warning("Please provide a valid city name or IATA code for flight search.")
        else:
            cheapest_flights = []
            train_results = None
            booking_link = ""

            # Fetch Flights if selected
            if travel_mode in ["Flights", "Both"]:
                with st.spinner("✈️ Fetching best flight options..."):
                    flight_data = fetch_flights(source_iata, destination_iata, departure_date, return_date)
                    cheapest_flights = extract_cheapest_flights(flight_data)
                    booking_link = create_google_flights_link(source_iata, destination_iata, departure_date, return_date)
            
            # Fetch Trains if selected
            if travel_mode in ["Trains", "Both"]:
                with st.spinner("🚂 Fetching train options..."):
                    train_results = fetch_trains(source_input, destination_input)

            # --- Display Results ---
            if travel_mode in ["Flights", "Both"]:
                st.subheader("✈️ Cheapest Flight Options")
                if cheapest_flights:
                    cols = st.columns(len(cheapest_flights))
                    for idx, flight in enumerate(cheapest_flights):
                        with cols[idx]:
                            airline_logo = flight.get("airline_logo", "")
                            airline_name = flight.get("airline", "Unknown Airline")
                            price = flight.get("price", "Not Available")
                            total_duration_minutes = flight.get("total_duration", "N/A")

                            if total_duration_minutes != "N/A":
                                hours = total_duration_minutes // 60
                                minutes = total_duration_minutes % 60
                                total_duration = f"{hours}h {minutes}m"
                            else:
                                total_duration = "N/A"

                            flights_info = flight.get("flights", [{}])
                            departure = flights_info[0].get("departure_airport", {})
                            arrival = flights_info[-1].get("arrival_airport", {})
                            
                            airline_name = flights_info[0].get("airline", "Unknown Airline")
                            
                            departure_time = format_datetime(departure.get("time", "N/A"))
                            arrival_time = format_datetime(arrival.get("time", "N/A"))

                            st.markdown(
                                f"""
                                <div style="
                                    border: 2px solid #ddd; 
                                    border-radius: 10px; 
                                    padding: 15px; 
                                    text-align: center;
                                    box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
                                    background-color: #f9f9f9;
                                    margin-bottom: 20px;
                                ">
                                    <img src="{airline_logo}" width="100" alt="Flight Logo" />
                                    <h3 style="margin: 10px 0;">{airline_name}</h3>
                                    <p><strong>Departure:</strong> {departure_time}</p>
                                    <p><strong>Arrival:</strong> {arrival_time}</p>
                                    <p><strong>Duration:</strong> {total_duration}</p>
                                    <h2 style="color: #008000;">💰 {price}</h2>
                                    <a href="{booking_link}" target="_blank" style="
                                        display: inline-block;
                                        padding: 10px 20px;
                                        font-size: 16px;
                                        font-weight: bold;
                                        color: #fff;
                                        background-color: #007bff;
                                        text-decoration: none;
                                        border-radius: 5px;
                                        margin-top: 10px;
                                    ">🔗 Book Now</a>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                else:
                    st.warning("⚠️ No flight data available for this route. Please check the dates and city names.")

            if travel_mode in ["Trains", "Both"]:
                st.subheader("🚂 Train Options")
                if train_results and train_results.get("trains"):
                    for train in train_results["trains"]:
                        st.markdown(f"**{train['name']}**")
                        st.markdown(f"- **Route:** {train['from']} to {train['to']}")
                        st.markdown(f"- **Departure:** {train['departure']}")
                        st.markdown(f"- **Arrival:** {train['arrival']}")
                        st.markdown(f"- **Duration:** {train['travel_time']}")
                        st.markdown(f"- **Price:** {train['price']}")
                        st.markdown("---")
                else:
                    st.warning("⚠️ No train data available for this route.")

            # --- AI Agents for Itinerary, Hotels, etc. ---
            # These can run regardless of travel mode
            with st.spinner("🔍 Researching best attractions & activities..."):
                research_prompt = (
                    f"Research the best attractions and activities in {destination_input} for a {num_days}-day {travel_theme.lower()} trip. "
                    f"The traveler enjoys: {activity_preferences}. Budget: {budget}. "
                    f"Hotel Rating: {hotel_rating}. Visa Requirement: {visa_required}. Travel Insurance: {travel_insurance}."
                )
                research_results = researcher.run(research_prompt, stream=False)

            # --- FIX: Adding a delay to avoid rate limiting ---
            time.sleep(2)

            with st.spinner("🏨 Searching for hotels & restaurants..."):
                hotel_restaurant_prompt = (
                    f"Find the best hotels and restaurants near popular attractions in {destination_input} for a {travel_theme.lower()} trip. "
                    f"Budget: {budget}. Hotel Rating: {hotel_rating}. Preferred activities: {activity_preferences}."
                )
                hotel_restaurant_results = hotel_restaurant_finder.run(hotel_restaurant_prompt, stream=False)
            
            # --- FIX: Adding a delay to avoid rate limiting ---
            time.sleep(2)

            with st.spinner("🗺️ Creating your personalized itinerary..."):
                # --- NEW PROMPT: Instruct the AI to generate a budget table ---
                itinerary_prompt = (
                    f"Based on the following data, create a {num_days}-day itinerary for a {travel_theme.lower()} trip to {destination_input}. "
                    f"The traveler enjoys: {activity_preferences}. Budget: {budget}. Flight Class: {flight_class}. Hotel Rating: {hotel_rating}. "
                    f"Visa Requirement: {visa_required}. Travel Insurance: {travel_insurance}. Research: {research_results.content}. "
                    f"Hotels & Restaurants: {hotel_restaurant_results.content}. "
                   # ... (inside the itinerary_prompt string)
f"**TASK:** In your final response, also provide a detailed estimated budget breakdown in a Markdown table for the trip's expenses at the destination. The budget breakdown should include categories like accommodation, food, and activities. **Do not include the cost of flights in this budget table.** Present this in a structured, numerical table with two columns: 'Category' and 'Estimated Cost'. "
                )
                if cheapest_flights and travel_mode in ["Flights", "Both"]:
                     itinerary_prompt += f" Flights: {json.dumps(cheapest_flights)}."
                itinerary = planner.run(itinerary_prompt, stream=False)

            st.subheader("🏨 Hotels & Restaurants")
            st.write(hotel_restaurant_results.content)

            st.subheader("🗺️ Your Personalized Itinerary & Budget")
            st.write(itinerary.content) # The AI's response now includes the budget table

            st.success("✅ Travel plan generated successfully!")