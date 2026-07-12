import streamlit as st

st.set_page_config(
    page_title="AI Travel Concierge",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ AI Travel Concierge")
st.write("Plan your trip using AI, weather, flights and destination information.")

origin = st.text_input("Starting city")
destination = st.text_input("Destination")

departure_date = st.date_input("Departure date")
return_date = st.date_input("Return date")

travellers = st.number_input(
    "Number of travellers",
    min_value=1,
    max_value=20,
    value=1,
)

budget = st.number_input(
    "Budget in ₹",
    min_value=0,
    value=10000,
    step=1000,
)

interests = st.multiselect(
    "Select your interests",
    [
        "Adventure",
        "Beaches",
        "Food",
        "History",
        "Nature",
        "Shopping",
        "Temples",
    ],
)

if st.button("Plan My Trip"):
    if not origin or not destination:
        st.error("Please enter the starting city and destination.")
    elif return_date < departure_date:
        st.error("Return date must be after the departure date.")
    else:
        st.success("Trip details received successfully!")

        st.subheader("Your Trip")

        st.write(f"**From:** {origin}")
        st.write(f"**To:** {destination}")
        st.write(f"**Departure:** {departure_date}")
        st.write(f"**Return:** {return_date}")
        st.write(f"**Travellers:** {travellers}")
        st.write(f"**Budget:** ₹{budget:,.2f}")
        st.write(f"**Interests:** {', '.join(interests) if interests else 'Not selected'}")